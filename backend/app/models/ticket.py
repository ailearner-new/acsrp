"""Ticket and message models."""

from typing import TYPE_CHECKING, List

from sqlalchemy import Enum, JSON, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, IDMixin, TimestampMixin, TenantMixin
from backend.app.models.enums import (
    ChannelType,
    SeverityLevel,
    TicketStatus,
    SenderType,
    IssueCategory,
)

if TYPE_CHECKING:
    from backend.app.models.tenant import Tenant
    from backend.app.models.customer import Customer
    from backend.app.models.user import User
    from backend.app.models.action import ActionAudit
    from backend.app.models.case import ResolvedCase


class Ticket(Base, IDMixin, TimestampMixin, TenantMixin):
    """Ticket/Conversation model."""

    __tablename__ = "tickets"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    channel: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, native_enum=False),
        nullable=False,
    )
    external_ref_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=True)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, native_enum=False),
        nullable=False,
        default=TicketStatus.NEW,
        index=True,
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, native_enum=False),
        nullable=False,
        default=SeverityLevel.MEDIUM_P2,
    )
    category: Mapped[IssueCategory | None] = mapped_column(
        Enum(IssueCategory, native_enum=False),
        nullable=True,
    )
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    is_autonomous_resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="tickets")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="tickets")
    assigned_agent: Mapped["User | None"] = relationship(
        "User", back_populates="assigned_tickets", foreign_keys=[assigned_agent_id]
    )
    messages: Mapped[list["TicketMessage"]] = relationship(
        "TicketMessage", back_populates="ticket", cascade="all, delete-orphan", lazy="dynamic"
    )
    actions: Mapped[list["ActionAudit"]] = relationship(
        "ActionAudit", back_populates="ticket", cascade="all, delete-orphan", lazy="dynamic"
    )
    resolved_case: Mapped["ResolvedCase | None"] = relationship(
        "ResolvedCase", back_populates="ticket", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, subject={self.subject}, status={self.status}, severity={self.severity})>"


class TicketMessage(Base, IDMixin, TimestampMixin, TenantMixin):
    """Ticket message model."""

    __tablename__ = "ticket_messages"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_type: Mapped[SenderType] = mapped_column(
        Enum(SenderType, native_enum=False),
        nullable=False,
    )
    sender_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachments: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="messages")

    def __repr__(self) -> str:
        return f"<TicketMessage(id={self.id}, ticket_id={self.ticket_id}, sender={self.sender_type})>"