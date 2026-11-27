"""Mock ticketing system integration (Zendesk/Intercom) for testing."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class TicketStatus(str, Enum):
    NEW = "NEW"
    OPEN = "OPEN"
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


@dataclass
class Ticket:
    """Mock ticket record."""
    ticket_id: str
    subject: str
    description: str
    status: TicketStatus
    priority: str
    requester: str
    assignee: Optional[str]
    created_at: str
    updated_at: str
    tags: List[str] = field(default_factory=list)


class MockTicketingClient:
    """Mock ticketing API client for Zendesk/Intercom-style systems."""

    def __init__(self, api_token: Optional[str] = None):
        """Initialize mock ticketing client."""
        self.api_token = api_token or "mock_token"
        self.tickets: Dict[str, Ticket] = {}
        self.queues: Dict[str, List[str]] = {}

    async def create_ticket(
        self,
        subject: str,
        description: str,
        requester: str,
        priority: str = "normal",
        tags: Optional[List[str]] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new ticket.

        Args:
            subject: Ticket subject
            description: Ticket description
            requester: Requester email/ID
            priority: Ticket priority
            tags: Optional tags
            custom_fields: Optional custom fields

        Returns:
            Created ticket
        """
        ticket_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        ticket = Ticket(
            ticket_id=ticket_id,
            subject=subject,
            description=description,
            status=TicketStatus.NEW,
            priority=priority,
            requester=requester,
            assignee=None,
            created_at=now,
            updated_at=now,
            tags=tags or [],
        )
        self.tickets[ticket_id] = ticket

        # Add to queue
        if "NEW" not in self.queues:
            self.queues["NEW"] = []
        self.queues["NEW"].append(ticket_id)

        return {
            "ticket_id": ticket_id,
            "status": "created",
            "subject": subject,
            "created_at": now,
        }

    async def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Get ticket details."""
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        return {
            "ticket_id": ticket.ticket_id,
            "subject": ticket.subject,
            "description": ticket.description,
            "status": ticket.status.value,
            "priority": ticket.priority,
            "requester": ticket.requester,
            "assignee": ticket.assignee,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
            "tags": ticket.tags,
        }

    async def update_ticket(
        self,
        ticket_id: str,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        comment: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update a ticket.

        Args:
            ticket_id: Ticket ID
            status: New status
            assignee: New assignee
            comment: Comment to add
            tags: New tags

        Returns:
            Updated ticket
        """
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        if status:
            old_status = ticket.status
            ticket.status = TicketStatus(status.upper())

            # Update queues
            if old_status.value in self.queues and ticket_id in self.queues[old_status.value]:
                self.queues[old_status.value].remove(ticket_id)
            if ticket.status.value not in self.queues:
                self.queues[ticket.status.value] = []
            self.queues[ticket.status.value].append(ticket_id)

        if assignee:
            ticket.assignee = assignee

        if tags:
            ticket.tags = tags

        ticket.updated_at = datetime.utcnow().isoformat() + "Z"

        return {
            "ticket_id": ticket_id,
            "status": ticket.status.value,
            "updated_at": ticket.updated_at,
        }

    async def add_comment(
        self,
        ticket_id: str,
        body: str,
        author: str,
        public: bool = True,
    ) -> Dict[str, Any]:
        """Add a comment to a ticket.

        Args:
            ticket_id: Ticket ID
            body: Comment body
            author: Comment author
            public: Whether comment is public

        Returns:
            Comment result
        """
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        ticket.updated_at = datetime.utcnow().isoformat() + "Z"

        return {
            "ticket_id": ticket_id,
            "comment_id": str(uuid.uuid4()),
            "body": body,
            "author": author,
            "public": public,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

    async def search_tickets(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        requester: Optional[str] = None,
        assignee: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search for tickets.

        Args:
            query: Search query
            status: Filter by status
            requester: Filter by requester
            assignee: Filter by assignee
            tags: Filter by tags
            limit: Maximum results

        Returns:
            List of matching tickets
        """
        results = []

        for ticket in self.tickets.values():
            if status and ticket.status.value != status.upper():
                continue
            if requester and ticket.requester != requester:
                continue
            if assignee and ticket.assignee != assignee:
                continue
            if tags:
                if not all(tag in ticket.tags for tag in tags):
                    continue
            if query:
                if query.lower() not in ticket.subject.lower() and query.lower() not in ticket.description.lower():
                    continue

            results.append({
                "ticket_id": ticket.ticket_id,
                "subject": ticket.subject,
                "status": ticket.status.value,
                "priority": ticket.priority,
                "requester": ticket.requester,
                "assignee": ticket.assignee,
                "tags": ticket.tags,
                "created_at": ticket.created_at,
            })

        return results[:limit]

    def list_tickets_in_queue(self, status: str = "NEW") -> List[str]:
        """List ticket IDs in a specific queue."""
        return self.queues.get(status, [])

    async def get_queue_size(self) -> Dict[str, int]:
        """Get size of each ticket queue."""
        return {status: len(tickets) for status, tickets in self.queues.items()}


class MockZendeskClient(MockTicketingClient):
    """Mock Zendesk-specific client."""

    pass


class MockIntercomClient(MockTicketingClient):
    """Mock Intercom-specific client."""

    pass