"""Ticket API schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr
from typing import Literal

from backend.app.models.enums import (
    ChannelType,
    SeverityLevel,
    TicketStatus,
    SenderType,
    IssueCategory,
)


class AttachmentBase(BaseModel):
    """Attachment schema."""

    name: str
    url: str
    content_type: str


class TicketIngestRequest(BaseModel):
    """Request schema for ticket ingestion."""

    tenant_id: UUID
    channel: ChannelType
    external_ref_id: Optional[str] = None
    customer_email: EmailStr
    customer_name: Optional[str] = None
    subject: Optional[str] = Field(None, max_length=500)
    body: str
    attachments: List[AttachmentBase] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TicketIngestResponse(BaseModel):
    """Response schema for ticket ingestion."""

    ticket_id: UUID
    status: Literal["queued"]
    message: str
    queued_at: datetime


class TicketMessageResponse(BaseModel):
    """Response schema for ticket message."""

    message_id: UUID
    sender_type: SenderType
    sender_id: str
    content: str
    cleaned_content: Optional[str] = None
    attachments: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class TicketResponse(BaseModel):
    """Response schema for ticket details."""

    ticket_id: UUID
    tenant_id: UUID
    customer_id: UUID
    assigned_agent_id: Optional[UUID] = None
    channel: ChannelType
    external_ref_id: Optional[str] = None
    subject: Optional[str] = None
    status: TicketStatus
    severity: SeverityLevel
    category: Optional[IssueCategory] = None
    subcategory: Optional[str] = None
    sentiment_score: Optional[float] = None
    confidence_score: Optional[float] = None
    is_autonomous_resolved: bool = False
    resolution_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    """Response schema for paginated ticket list."""

    tickets: List[TicketResponse]
    total: int
    limit: int
    offset: int


class AgentActionRequest(BaseModel):
    """Request schema for agent action on AI suggestion."""

    action: Literal["accept", "edit", "reject"]
    suggestion_id: str
    edited_content: Optional[str] = None
    edited_actions: Optional[List[Dict[str, Any]]] = None


class AgentActionResponse(BaseModel):
    """Response schema for agent action."""

    status: Literal["applied", "rejected"]
    message_id: Optional[UUID] = None


class TicketUpdateRequest(BaseModel):
    """Request schema for updating a ticket."""

    subject: Optional[str] = Field(None, max_length=500)
    status: Optional[TicketStatus] = None
    severity: Optional[SeverityLevel] = None
    category: Optional[IssueCategory] = None
    subcategory: Optional[str] = None
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_autonomous_resolved: Optional[bool] = None
    resolution_summary: Optional[str] = None


class TicketAssignRequest(BaseModel):
    """Request schema for assigning a ticket to an agent."""

    agent_id: UUID


class TicketMessageCreateRequest(BaseModel):
    """Request schema for adding a message to a ticket."""

    sender_type: SenderType
    sender_id: str
    content: str
    cleaned_content: Optional[str] = None
    attachments: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TicketMessageCreateResponse(BaseModel):
    """Response schema for adding a message."""

    message_id: UUID
    ticket_id: UUID
    created_at: datetime


# WebSocket message schemas
class WSConnectMessage(BaseModel):
    """WebSocket connection message."""

    type: Literal["subscribe"]
    ticket_id: str


class WSMessage(BaseModel):
    """Base WebSocket message."""

    type: str
    payload: Dict[str, Any]


class WSNewMessagePayload(BaseModel):
    """Payload for NEW_MESSAGE event."""

    message_id: UUID
    sender_type: SenderType
    content: str
    created_at: datetime


class WSStateUpdatePayload(BaseModel):
    """Payload for STATE_UPDATE event."""

    intent: Optional[str] = None
    severity: Optional[SeverityLevel] = None
    confidence_score: Optional[float] = None
    retrieved_docs: Optional[List[Dict[str, Any]]] = None
    proposed_actions: Optional[List[Dict[str, Any]]] = None
    draft_response: Optional[str] = None
    next_node: Optional[str] = None


class WSAgentActionPayload(BaseModel):
    """Payload for agent_action client message."""

    action_id: str
    action: Literal["accept", "edit", "reject"]
    suggestion_id: str
    edited_content: Optional[str] = None
    edited_actions: Optional[List[Dict[str, Any]]] = None