"""Customer model."""

from typing import TYPE_CHECKING

from sqlalchemy import Enum, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, IDMixin, TimestampMixin, TenantMixin
from backend.app.models.enums import CustomerTier

if TYPE_CHECKING:
    from backend.app.models.tenant import Tenant
    from backend.app.models.ticket import Ticket


class Customer(Base, IDMixin, TimestampMixin, TenantMixin):
    """Customer model."""

    __tablename__ = "customers"

    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tier: Mapped[CustomerTier] = mapped_column(
        Enum(CustomerTier, native_enum=False),
        nullable=False,
        default=CustomerTier.STANDARD,
    )
    metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="customers")
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="customer", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, email={self.email}, tier={self.tier}, tenant_id={self.tenant_id})>"