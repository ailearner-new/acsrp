"""Knowledge article repository."""

from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple
from uuid import UUID

from backend.app.models.article import KnowledgeArticle
from backend.app.repositories.base import BaseRepository
from backend.app.core.database import db_manager
from backend.app.models.enums import IssueCategory


class KnowledgeArticleRepository(BaseRepository[KnowledgeArticle]):
    """Repository for KnowledgeArticle model."""

    def __init__(self):
        super().__init__(KnowledgeArticle)

    async def get_by_title(self, tenant_id: UUID, title: str) -> Optional[KnowledgeArticle]:
        """Get article by exact title for a specific tenant."""
        async with db_manager.session() as session:
            stmt = select(KnowledgeArticle).where(
                KnowledgeArticle.title == title,
                KnowledgeArticle.tenant_id == tenant_id,
                KnowledgeArticle.is_active == True
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def search_by_keywords(
        self,
        tenant_id: Optional[UUID],
        keywords: List[str],
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[KnowledgeArticle], int]:
        """Search articles by keywords using full-text search."""
        async with db_manager.session() as session:
            where_clauses = ["is_active = TRUE"]
            params = {}

            if tenant_id:
                where_clauses.append("tenant_id = :tenant_id")
                params["tenant_id"] = tenant_id

            if keywords:
                where_clauses.append("@@ ts_rank(article_search_vector, plainto_tsquery(:query))")
                params["query"] = " & ".join(keywords)

            stmt = select(KnowledgeArticle).where(text(" AND ".join(where_clauses)))
            count_stmt = select(func.count()).select_from(KnowledgeArticle).where(text(" AND ".join(where_clauses)))

            stmt = stmt.order_by(KnowledgeArticle.created_at.desc()).limit(limit).offset(offset)

            result = await session.execute(stmt, params)
            articles = result.scalars().all()

            count_result = await session.execute(count_stmt, params)
            total = count_result.scalar_one()

            return list(articles), total

    async def list_active(
        self,
        tenant_id: Optional[UUID] = None,
        category: Optional[IssueCategory] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[KnowledgeArticle], int]:
        """List active articles with optional filtering."""
        async with db_manager.session() as session:
            stmt = select(KnowledgeArticle).where(KnowledgeArticle.is_active == True)
            count_stmt = select(func.count()).select_from(KnowledgeArticle).where(KnowledgeArticle.is_active == True)

            if tenant_id is not None:
                stmt = stmt.where(KnowledgeArticle.tenant_id == tenant_id)
                count_stmt = count_stmt.where(KnowledgeArticle.tenant_id == tenant_id)

            if category is not None:
                stmt = stmt.where(KnowledgeArticle.category == category)
                count_stmt = count_stmt.where(KnowledgeArticle.category == category)

            stmt = stmt.order_by(KnowledgeArticle.created_at.desc()).limit(limit).offset(offset)
            result = await session.execute(stmt)
            articles = result.scalars().all()

            count_result = await session.execute(count_stmt)
            total = count_result.scalar_one()

            return list(articles), total

    async def count_chunks_by_category(self, *, tenant_id: UUID | None = None) -> dict:
        """Count total chunks by category for knowledge base analytics."""
        async with db_manager.session() as session:
            stmt = select(
                KnowledgeArticle.category.label("category"),
                func.count(text("jsonb_array_length(content_chunks)")).label("chunk_count")
            ).group_by(KnowledgeArticle.category)

            if tenant_id is not None:
                stmt = stmt.where(KnowledgeArticle.tenant_id == tenant_id)

            result = await session.execute(stmt)
            return {str(row.category): row.chunk_count for row in result}

    async def get_articles_with_chunks(
        self,
        article_ids: List[UUID],
        tenant_id: Optional[UUID] = None,
    ) -> List[KnowledgeArticle]:
        """Get articles with their chunks populated."""
        async with db_manager.session() as session:
            stmt = select(KnowledgeArticle).options(selectinload(KnowledgeArticle.content_chunks)).where(
                KnowledgeArticle.id.in_(article_ids)
            )
            if tenant_id is not None:
                stmt = stmt.where(KnowledgeArticle.tenant_id == tenant_id)

            result = await session.execute(stmt)
            return result.scalars().all()