"""Ticket repository."""

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.app.models.ticket import Ticket, TicketMessage
from backend.app.repositories.base import BaseRepository
from backend.app.models.enums import ChannelType, TicketStatus, SeverityLevel, IssueCategory


class TicketRepository(BaseRepository[Ticket]):
    """Repository for Ticket model."""

    def __init__(self):
        super().__init__(Ticket)

    async def get_by_customer(self, customer_id: UUID, *, tenant_id: str | None = None, status: TicketStatus | None = None) -> list[Ticket]:
        """Get tickets by customer."""
        async with db_manager.session() as session:
            stmt = select(Ticket).where(Ticket.customer_id == customer_id)
            if tenant_id is not None:
                stmt = stmt.where(Ticket.tenant_id == tenant_id)
            if status is not None:
                stmt = stmt.where(Ticket.status == status)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_open_tickets(self, *, tenant_id: UUID) -> list[Ticket]:
        """Get open (non-resolved) tickets."""
        async with db_manager.session() as session:
            stmt = select(Ticket).where(
                Ticket.tenant_id == tenant_id,
                Ticket.status.in_([TicketStatus.NEW, TicketStatus.PROCESSING, TicketStatus.AWAITING_CUSTOMER, TicketStatus.AWAITING_APPROVAL])
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def count_unassigned(self, *, tenant_id: UUID) -> int:
        """Count unassigned tickets."""
        async with db_manager.session() as session:
            stmt = select(func.count()).select_from(Ticket).where(
                Ticket.tenant_id == tenant_id,
                Ticket.assigned_agent_id == None
            )
            result = await session.execute(stmt)
            return result.scalar_one()

    async def get_with_messages(self, ticket_id: UUID, *, tenant_id: UUID) -> Optional[Ticket]:
        """Get ticket with loaded messages."""
        async with db_manager.session() as session:
            stmt = select(Ticket).options(
                selectinload(Ticket.messages)
            ).where(Ticket.id == ticket_id, Ticket.tenant_id == tenant_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()