"""Knowledge article/document model for RAG pipeline."""

from typing import TYPE_CHECKING

from sqlalchemy import Enum, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, IDMixin, TimestampMixin, TenantMixin
from backend.app.models.enums import IssueCategory

if TYPE_CHECKING:
    from backend.app.models.tenant import Tenant


class KnowledgeArticle(Base, IDMixin, TimestampMixin, TenantMixin):
    """Knowledge article/document model for the knowledge base.

    Used for RAG retrieval - articles are chunked for vector search
    and can be from internal docs, help articles, or historical resolutions.
    """

    __tablename__ = "knowledge_articles"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_chunks: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    category: Mapped[IssueCategory | None] = mapped_column(
        Enum(IssueCategory, native_enum=False),
        nullable=True,
    )
    access_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="internal",
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="knowledge_articles")

    def __repr__(self) -> str:
        return f"<KnowledgeArticle(id={self.id}, title={self.title!r}, tenant_id={self.tenant_id})>"