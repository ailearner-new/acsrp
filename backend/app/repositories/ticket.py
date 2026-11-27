"""Ticket repository."""

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple
from uuid import UUID

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

    async def add_message(self, message: TicketMessage) -> TicketMessage:
        """Add a message to a ticket."""
        async with db_manager.session() as session:
            session.add(message)
            await session.commit()
            await session.refresh(message)
            return message

    async def get_messages(self, ticket_id: UUID, limit: int = 100, offset: int = 0) -> List[TicketMessage]:
        """Get messages for a ticket with pagination."""
        async with db_manager.session() as session:
            stmt = select(TicketMessage).where(
                TicketMessage.ticket_id == ticket_id
            ).order_by(TicketMessage.created_at).limit(limit).offset(offset)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_tickets(self, filters: dict, limit: int = 50, offset: int = 0) -> Tuple[List[Ticket], int]:
        """List tickets with filters and pagination."""
        async with db_manager.session() as session:
            stmt = select(Ticket)
            count_stmt = select(func.count()).select_from(Ticket)

            if "status" in filters:
                stmt = stmt.where(Ticket.status == filters["status"])
                count_stmt = count_stmt.where(Ticket.status == filters["status"])
            if "severity" in filters:
                stmt = stmt.where(Ticket.severity == filters["severity"])
                count_stmt = count_stmt.where(Ticket.severity == filters["severity"])
            if "category" in filters:
                stmt = stmt.where(Ticket.category == filters["category"])
                count_stmt = count_stmt.where(Ticket.category == filters["category"])
            if "assigned_agent_id" in filters:
                stmt = stmt.where(Ticket.assigned_agent_id == filters["assigned_agent_id"])
                count_stmt = count_stmt.where(Ticket.assigned_agent_id == filters["assigned_agent_id"])
            if "customer_id" in filters:
                stmt = stmt.where(Ticket.customer_id == filters["customer_id"])
                count_stmt = count_stmt.where(Ticket.customer_id == filters["customer_id"])

            stmt = stmt.order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
            result = await session.execute(stmt)
            tickets = result.scalars().all()

            count_result = await session.execute(count_stmt)
            total = count_result.scalar_one()

            return list(tickets), total