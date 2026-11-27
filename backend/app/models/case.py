"""Resolved case model for episodic memory."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, JSON, String, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import REAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, IDMixin, TimestampMixin, TenantMixin
from backend.app.models.enums import IssueCategory

if TYPE_CHECKING:
    from backend.app.models.ticket import Ticket


class ResolvedCase(Base, IDMixin, TimestampMixin, TenantMixin):
    """Resolved case model for episodic memory and similarity search."""

    __tablename__ = "resolved_cases"
    __table_args__ = (
        Index("ix_resolved_cases_embedding", "embedding", postgresql_using="hnsw"),
    )

    ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tickets.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
        index=True,
    )
    issue_summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_steps: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[IssueCategory | None] = mapped_column(
        Enum(IssueCategory, native_enum=False),
        nullable=True,
    )
    # pgvector embedding - stored as array of floats; actual type is vector(1536)
    embedding: Mapped[list[float] | None] = mapped_column(
        PG_ARRAY(REAL),
        nullable=True,
    )
    csat_score: Mapped[int | None] = mapped_column(nullable=True)

    # Relationships
    ticket: Mapped["Ticket | None"] = relationship("Ticket", back_populates="resolved_case")

    def __repr__(self) -> str:
        return f"<ResolvedCase(id={self.id}, category={self.category}, csat={self.csat_score})>"