"""WebSocket API routes for real-time agent assistance."""

import json
import uuid
from typing import Dict, Set, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.middleware import get_current_user, decode_token, REQUEST_ID_VAR
from backend.app.core.config import settings

router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    """Manages WebSocket connections for ticket subscriptions."""

    def __init__(self):
        # ticket_id -> set of (websocket, user_info)
        self.active_connections: Dict[UUID, Set[tuple]] = {}
        self.user_connections: Dict[str, Set[UUID]] = {}  # user_id -> set of ticket_ids

    async def connect(self, websocket: WebSocket, ticket_id: UUID, user_info: dict):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if ticket_id not in self.active_connections:
            self.active_connections[ticket_id] = set()
        self.active_connections[ticket_id].add((websocket, user_info))

        user_id = user_info.get("sub")
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(ticket_id)

    def disconnect(self, websocket: WebSocket, ticket_id: UUID, user_info: dict):
        """Remove a WebSocket connection."""
        if ticket_id in self.active_connections:
            self.active_connections[ticket_id].discard((websocket, user_info))
            if not self.active_connections[ticket_id]:
                del self.active_connections[ticket_id]

        user_id = user_info.get("sub")
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(ticket_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_to_ticket(self, ticket_id: UUID, message: dict):
        """Send a message to all subscribers of a ticket."""
        if ticket_id in self.active_connections:
            disconnected = set()
            for websocket, user_info in self.active_connections[ticket_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.add((websocket, user_info))

            # Clean up disconnected connections
            for ws, ui in disconnected:
                self.disconnect(ws, ticket_id, ui)

    async def broadcast_state_update(self, ticket_id: UUID, state: dict):
        """Broadcast a STATE_UPDATE message to all ticket subscribers."""
        message = {
            "type": "STATE_UPDATE",
            "payload": state,
        }
        await self.send_to_ticket(ticket_id, message)

    async def broadcast_new_message(self, ticket_id: UUID, message_data: dict):
        """Broadcast a NEW_MESSAGE to all ticket subscribers."""
        message = {
            "type": "NEW_MESSAGE",
            "payload": message_data,
        }
        await self.send_to_ticket(ticket_id, message)


# Global connection manager
manager = ConnectionManager()


async def get_ws_token(websocket: WebSocket, token: str = Query(...)) -> Optional[dict]:
    """Extract and validate token from WebSocket query parameter."""
    try:
        payload = decode_token(token)
        return payload
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None


@router.websocket("/tickets/{ticket_id}")
async def websocket_ticket_stream(
    websocket: WebSocket,
    ticket_id: UUID,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time agent state updates.

    Client sends: {"type": "subscribe", "ticket_id": "uuid"}
    Server sends: NEW_MESSAGE and STATE_UPDATE events

    Query Parameters:
    - token: JWT access token (required for authentication)
    """
    # Authenticate user
    user_info = await get_ws_token(websocket, token)
    if not user_info:
        return

    # Set request ID context
    request_id = f"ws-{uuid.uuid4().hex[:8]}"
    REQUEST_ID_VAR.set(request_id)

    # Connect
    await manager.connect(websocket, ticket_id, user_info)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "CONNECTED",
            "payload": {
                "ticket_id": str(ticket_id),
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        })

        # Listen for client messages (subscribe, ping, etc.)
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "subscribe":
                # Client confirms subscription (already subscribed on connect)
                await websocket.send_json({
                    "type": "SUBSCRIBED",
                    "payload": {
                        "ticket_id": str(ticket_id),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                })
            elif data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "payload": {"timestamp": datetime.utcnow().isoformat()},
                })
            elif data.get("type") == "agent_action":
                # Forward agent action to workflow (placeholder for future integration)
                await websocket.send_json({
                    "type": "ACTION_ACK",
                    "payload": {
                        "action_id": data.get("action_id"),
                        "status": "received",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, ticket_id, user_info)
    except Exception as e:
        manager.disconnect(websocket, ticket_id, user_info)
        # Log error but don't crash
        from backend.app.core.logging import get_logger
        logger = get_logger("websocket")
        logger.error("websocket_error", ticket_id=str(ticket_id), error=str(e))


# Utility functions for other parts of the system to broadcast updates

async def broadcast_new_message(ticket_id: UUID, message_data: dict):
    """Broadcast a new message to all subscribers of a ticket."""
    await manager.broadcast_new_message(ticket_id, message_data)


async def broadcast_state_update(ticket_id: UUID, state: dict):
    """Broadcast a state update to all subscribers of a ticket."""
    await manager.broadcast_state_update(ticket_id, state)