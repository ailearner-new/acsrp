"""Tenant model."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.customer import Customer
    from backend.app.models.ticket import Ticket
    from backend.app.models.article import KnowledgeArticle


class Tenant(Base, IDMixin, TimestampMixin):
    """Tenant/organization model."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="tenant", lazy="dynamic")
    customers: Mapped[list["Customer"]] = relationship("Customer", back_populates="tenant", lazy="dynamic")
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="tenant", lazy="dynamic")
    knowledge_articles: Mapped[list["KnowledgeArticle"]] = relationship(
        "KnowledgeArticle", back_populates="tenant", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, domain={self.domain})>"