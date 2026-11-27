"""User/Agent model."""

from typing import TYPE_CHECKING, List

from sqlalchemy import ARRAY, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, IDMixin, TimestampMixin, TenantMixin
from backend.app.models.enums import RoleType

if TYPE_CHECKING:
    from backend.app.models.tenant import Tenant
    from backend.app.models.ticket import Ticket
    from backend.app.models.action import ActionAudit


class User(Base, IDMixin, TimestampMixin, TenantMixin):
    """User/Agent model."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleType] = mapped_column(
        Enum(RoleType, native_enum=False),
        nullable=False,
        default=RoleType.TIER1_AGENT,
    )
    skills: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    assigned_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="assigned_agent", foreign_keys="Ticket.assigned_agent_id", lazy="dynamic"
    )
    approved_actions: Mapped[list["ActionAudit"]] = relationship(
        "ActionAudit", back_populates="approved_by_user", foreign_keys="ActionAudit.approved_by", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role}, tenant_id={self.tenant_id})>"