"""Action audit model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, JSON, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, IDMixin, TimestampMixin, TenantMixin
from backend.app.models.enums import ActionRiskLevel, ActionStatus

if TYPE_CHECKING:
    from backend.app.models.ticket import Ticket
    from backend.app.models.user import User


class ActionAudit(Base, IDMixin, TimestampMixin, TenantMixin):
    """Action execution audit log."""

    __tablename__ = "action_audits"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_name: Mapped[str] = mapped_column(String(150), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(150), nullable=False)
    risk_level: Mapped[ActionRiskLevel] = mapped_column(
        Enum(ActionRiskLevel, native_enum=False),
        nullable=False,
    )
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus, native_enum=False),
        nullable=False,
        default=ActionStatus.PENDING_APPROVAL,
        index=True,
    )
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approval_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="actions")
    approved_by_user: Mapped["User | None"] = relationship(
        "User", back_populates="approved_actions", foreign_keys=[approved_by]
    )

    def __repr__(self) -> str:
        return f"<ActionAudit(id={self.id}, action={self.action_name}, status={self.status})>"