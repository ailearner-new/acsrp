"""Ticket API routes."""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.core.middleware import require_role
from backend.app.repositories.ticket import TicketRepository
from backend.app.repositories.customer import CustomerRepository
from backend.app.schemas.ticket import (
    TicketIngestRequest,
    TicketIngestResponse,
    TicketResponse,
    TicketListResponse,
    TicketMessageResponse,
    AgentActionRequest,
    AgentActionResponse,
)

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post(
    "/ingest",
    response_model=TicketIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a support request from any channel",
)
async def ingest_ticket(
    request: TicketIngestRequest,
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER", "TIER1_AGENT", "TIER2_ENGINEER", "READ_ONLY")),
) -> TicketIngestResponse:
    """
    Ingest a support request from any channel (email, chat, Zendesk, Intercom, in-app, Slack).

    Creates a new ticket with an initial customer message.
    The ticket will be queued for AI processing.
    """
    # Verify tenant matches user's tenant (unless super admin)
    user_tenant_id = current_user.get("tenant_id")
    if user_tenant_id and current_user.get("role") != "SUPER_ADMIN":
        if str(request.tenant_id) != user_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create tickets for other tenants",
            )

    ticket_repo = TicketRepository()
    customer_repo = CustomerRepository()

    # Find or create customer
    customer = await customer_repo.get_by_email(request.tenant_id, request.customer_email)
    if not customer:
        from backend.app.models.customer import Customer
        from backend.app.models.enums import CustomerTier
        customer = Customer(
            tenant_id=request.tenant_id,
            email=request.customer_email,
            full_name=request.customer_name,
            tier=CustomerTier.STANDARD,
        )
        await customer_repo.create(customer)

    # Create ticket
    from backend.app.models.ticket import Ticket, TicketMessage
    from backend.app.models.enums import TicketStatus, SenderType
    import uuid

    ticket = Ticket(
        tenant_id=request.tenant_id,
        customer_id=customer.id,
        channel=request.channel,
        external_ref_id=request.external_ref_id,
        subject=request.subject,
        status=TicketStatus.NEW,
    )
    await ticket_repo.create(ticket)

    # Create initial message
    message = TicketMessage(
        ticket_id=ticket.id,
        tenant_id=request.tenant_id,
        sender_type=SenderType.CUSTOMER,
        sender_id=request.customer_email,
        content=request.body,
        attachments=request.attachments[0].model_dump() if request.attachments else {},
        metadata=request.metadata,
    )
    await ticket_repo.add_message(message)

    return TicketIngestResponse(
        ticket_id=ticket.id,
        status="queued",
        message="Request accepted for processing",
        queued_at=ticket.created_at,
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get ticket details",
)
async def get_ticket(
    ticket_id: UUID,
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER", "TIER1_AGENT", "TIER2_ENGINEER", "READ_ONLY")),
) -> TicketResponse:
    """
    Get detailed information about a specific ticket.

    Returns ticket metadata, customer info, and current status.
    """
    ticket_repo = TicketRepository()
    ticket = await ticket_repo.get_by_id(ticket_id)

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return TicketResponse(
        ticket_id=ticket.id,
        tenant_id=ticket.tenant_id,
        customer_id=ticket.customer_id,
        assigned_agent_id=ticket.assigned_agent_id,
        channel=ticket.channel,
        external_ref_id=ticket.external_ref_id,
        subject=ticket.subject,
        status=ticket.status,
        severity=ticket.severity,
        category=ticket.category,
        subcategory=ticket.subcategory,
        sentiment_score=float(ticket.sentiment_score) if ticket.sentiment_score else None,
        confidence_score=float(ticket.confidence_score) if ticket.confidence_score else None,
        is_autonomous_resolved=ticket.is_autonomous_resolved,
        resolution_summary=ticket.resolution_summary,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.get(
    "/{ticket_id}/messages",
    response_model=List[TicketMessageResponse],
    summary="Get conversation history for a ticket",
)
async def get_ticket_messages(
    ticket_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER", "TIER1_AGENT", "TIER2_ENGINEER", "READ_ONLY")),
) -> List[TicketMessageResponse]:
    """
    Get the conversation history (messages) for a specific ticket.

    Returns messages in chronological order with pagination support.
    """
    ticket_repo = TicketRepository()
    messages = await ticket_repo.get_messages(ticket_id, limit=limit, offset=offset)

    return [
        TicketMessageResponse(
            message_id=msg.id,
            sender_type=msg.sender_type,
            sender_id=msg.sender_id,
            content=msg.content,
            cleaned_content=msg.cleaned_content,
            attachments=msg.attachments,
            metadata=msg.metadata,
            created_at=msg.created_at,
        )
        for msg in messages
    ]


@router.post(
    "/{ticket_id}/agent-action",
    response_model=AgentActionResponse,
    summary="Agent accepts/edits/rejects AI suggestion",
)
async def agent_action(
    ticket_id: UUID,
    request: AgentActionRequest,
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER", "TIER1_AGENT", "TIER2_ENGINEER")),
) -> AgentActionResponse:
    """
    Agent accepts, edits, or rejects an AI suggestion for a ticket.

    This endpoint is used by human agents to interact with AI-generated suggestions.
    """
    # Implementation would integrate with workflow graph
    # For now, return a placeholder response
    return AgentActionResponse(
        status="applied",
        message_id=None,
    )


@router.get(
    "/",
    response_model=TicketListResponse,
    summary="List tickets with filtering and pagination",
)
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter by ticket status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by category"),
    assigned_agent_id: Optional[UUID] = Query(None, description="Filter by assigned agent"),
    customer_id: Optional[UUID] = Query(None, description="Filter by customer"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER", "TIER1_AGENT", "TIER2_ENGINEER", "READ_ONLY")),
) -> TicketListResponse:
    """
    List tickets with optional filtering and pagination.

    Supports filtering by status, severity, category, assigned agent, and customer.
    """
    ticket_repo = TicketRepository()

    # Build filters
    filters = {}
    if status:
        filters["status"] = status
    if severity:
        filters["severity"] = severity
    if category:
        filters["category"] = category
    if assigned_agent_id:
        filters["assigned_agent_id"] = assigned_agent_id
    if customer_id:
        filters["customer_id"] = customer_id

    tickets, total = await ticket_repo.list_tickets(filters, limit=limit, offset=offset)

    return TicketListResponse(
        tickets=[
            TicketResponse(
                ticket_id=t.id,
                tenant_id=t.tenant_id,
                customer_id=t.customer_id,
                assigned_agent_id=t.assigned_agent_id,
                channel=t.channel,
                external_ref_id=t.external_ref_id,
                subject=t.subject,
                status=t.status,
                severity=t.severity,
                category=t.category,
                subcategory=t.subcategory,
                sentiment_score=float(t.sentiment_score) if t.sentiment_score else None,
                confidence_score=float(t.confidence_score) if t.confidence_score else None,
                is_autonomous_resolved=t.is_autonomous_resolved,
                resolution_summary=t.resolution_summary,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in tickets
        ],
        total=total,
        limit=limit,
        offset=offset,
    )