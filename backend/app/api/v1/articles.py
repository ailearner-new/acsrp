"""Knowledge article (document) API routes."""

from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.core.middleware import require_role
from backend.app.repositories.article import KnowledgeArticleRepository
from backend.app.schemas.article import (
    KnowledgeArticleCreateRequest,
    KnowledgeArticleUpdateRequest,
    KnowledgeArticleResponse,
    KnowledgeArticleListResponse,
    KnowledgeArticleSummaryResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)
from backend.app.models.enums import IssueCategory

router = APIRouter(prefix="/articles", tags=["Knowledge Articles"])


def get_tenant_id_from_user(current_user: dict) -> UUID:
    """Extract and convert tenant_id from JWT token to UUID."""
    tenant_id = current_user.get("tenant_id")
    if tenant_id is None:
        return UUID("00000000-0000-0000-0000-000000000000")
    if isinstance(tenant_id, str):
        return UUID(tenant_id)
    return tenant_id


@router.post(
    "/",
    response_model=KnowledgeArticleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new knowledge article",
)
async def create_article(
    request: KnowledgeArticleCreateRequest,
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER")),
) -> KnowledgeArticleResponse:
    """
    Create a new knowledge article in the system.

    Requires appropriate role permissions.
    """
    article_repo = KnowledgeArticleRepository()
    tenant_id = get_tenant_id_from_user(current_user)
    user_role = current_user.get("role")

    from backend.app.models.article import KnowledgeArticle

    article = KnowledgeArticle(
        tenant_id=tenant_id,
        title=request.title,
        content=request.content,
        source_url=request.source_url,
        category=request.category,
        access_level=request.access_level,
        metadata=request.metadata,
    )

    await article_repo.create(article)

    return KnowledgeArticleResponse(
        id=article.id,
        tenant_id=article.tenant_id,
        title=article.title,
        content=article.content,
        source_url=article.source_url,
        category=article.category,
        access_level=article.access_level,
        is_active=article.is_active,
        chunk_count=0,
        metadata=article.metadata,
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


@router.get(
    "/{article_id}",
    response_model=KnowledgeArticleResponse,
    summary="Get knowledge article by ID",
)
async def get_article(
    article_id: UUID,
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER", "TIER1_AGENT", "TIER2_ENGINEER", "READ_ONLY")),
) -> KnowledgeArticleResponse:
    """
    Get detailed information about a specific knowledge article.
    """
    article_repo = KnowledgeArticleRepository()
    tenant_id = get_tenant_id_from_user(current_user)
    user_role = current_user.get("role")

    if user_role == "SUPER_ADMIN":
        article = await article_repo.get_by_id(article_id)
    else:
        article = await article_repo.get_by_id(article_id, tenant_id=tenant_id)

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge article not found",
        )

    return KnowledgeArticleResponse(
        id=article.id,
        tenant_id=article.tenant_id,
        title=article.title,
        content=article.content,
        source_url=article.source_url,
        category=article.category,
        access_level=article.access_level,
        is_active=article.is_active,
        chunk_count=len(article.content_chunks) if article.content_chunks else 0,
        metadata=article.metadata,
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


@router.patch(
    "/{article_id}",
    response_model=KnowledgeArticleResponse,
    summary="Update knowledge article details",
)
async def update_article(
    article_id: UUID,
    request: KnowledgeArticleUpdateRequest,
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER")),
) -> KnowledgeArticleResponse:
    """
    Update knowledge article information.

    Only provided fields will be updated.
    """
    article_repo = KnowledgeArticleRepository()
    tenant_id = get_tenant_id_from_user(current_user)
    user_role = current_user.get("role")

    if user_role == "SUPER_ADMIN":
        article = await article_repo.get_by_id(article_id)
    else:
        article = await article_repo.get_by_id(article_id, tenant_id=tenant_id)

    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge article not found",
        )

    # Update fields if provided
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(article, key):
            setattr(article, key, value)

    await article_repo.update(article_id, **update_data)

    # Refresh article
    if user_role == "SUPER_ADMIN":
        article = await article_repo.get_by_id(article_id)
    else:
        article = await article_repo.get_by_id(article_id, tenant_id=tenant_id)

    return KnowledgeArticleResponse(
        id=article.id,
        tenant_id=article.tenant_id,
        title=article.title,
        content=article.content,
        source_url=article.source_url,
        category=article.category,
        access_level=article.access_level,
        is_active=article.is_active,
        chunk_count=len(article.content_chunks) if article.content_chunks else 0,
        metadata=article.metadata,
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


@router.delete(
    "/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a knowledge article",
)
async def delete_article(
    article_id: UUID,
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER")),
) -> None:
    """
    Delete a knowledge article.

    Only provided fields will be updated.
    """
    article_repo = KnowledgeArticleRepository()
    tenant_id = get_tenant_id_from_user(current_user)
    user_role = current_user.get("role")

    if user_role == "SUPER_ADMIN":
        deleted = await article_repo.delete(article_id)
    else:
        deleted = await article_repo.delete(article_id, tenant_id=tenant_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge article not found",
        )


@router.get(
    "/",
    response_model=KnowledgeArticleListResponse,
    summary="List knowledge articles with filtering and pagination",
)
async def list_articles(
    category: Optional[IssueCategory] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(True, description="Show only active articles"),
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER", "TIER1_AGENT", "TIER2_ENGINEER", "READ_ONLY")),
) -> KnowledgeArticleListResponse:
    """
    List knowledge articles with optional filtering and pagination.

    Supports filtering by category and active status.
    """
    article_repo = KnowledgeArticleRepository()
    tenant_id = get_tenant_id_from_user(current_user)
    user_role = current_user.get("role")

    if user_role != "SUPER_ADMIN":
        articles, total = await article_repo.list_active(
            tenant_id=tenant_id,
            category=category,
            limit=limit,
            offset=offset,
        )
    else:
        articles, total = await article_repo.list_active(
            tenant_id=None,
            category=category,
            limit=limit,
            offset=offset,
        )

    return KnowledgeArticleListResponse(
        articles=[
            KnowledgeArticleSummaryResponse(
                id=a.id,
                tenant_id=a.tenant_id,
                title=a.title,
                source_url=a.source_url,
                category=a.category,
                chunk_count=len(a.content_chunks) if a.content_chunks else 0,
                updated_at=a.updated_at,
            )
            for a in articles
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    summary="Search knowledge articles with hybrid retrieval",
)
async def search_articles(
    request: KnowledgeSearchRequest,
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER", "TIER1_AGENT", "TIER2_ENGINEER", "READ_ONLY")),
) -> KnowledgeSearchResponse:
    """
    Search knowledge articles using hybrid retrieval (vector + BM25 + graph).

    Combines dense vector search with sparse keyword search for optimal results.
    """
    import time

    start_time = time.time()

    # This is a placeholder - the actual RAG pipeline implementation
    # would go here in the knowledge-service
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Hybrid search pipeline not yet implemented - use knowledge-service directly",
    )