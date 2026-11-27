"""Knowledge article (document) schemas."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from backend.app.models.enums import IssueCategory


class KnowledgeArticleCreateRequest(BaseModel):
    """Request schema for creating a knowledge article."""

    title: str = Field(..., max_length=500)
    content: str
    source_url: Optional[str] = Field(None, max_length=1000)
    category: Optional[IssueCategory] = None
    access_level: str = Field(default="internal", pattern="^(internal|public)$")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("access_level")
    @classmethod
    def validate_access_level(cls, v):
        if v not in ("internal", "public"):
            raise ValueError("access_level must be 'internal' or 'public'")
        return v


class KnowledgeArticleUpdateRequest(BaseModel):
    """Request schema for updating a knowledge article."""

    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    source_url: Optional[str] = Field(None, max_length=1000)
    category: Optional[IssueCategory] = None
    access_level: Optional[str] = Field(None, pattern="^(internal|public)$")
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class KnowledgeArticleResponse(BaseModel):
    """Response schema for a knowledge article."""

    id: UUID
    tenant_id: UUID
    title: str
    content: str
    source_url: Optional[str] = None
    category: Optional[IssueCategory] = None
    access_level: str
    is_active: bool
    chunk_count: int = Field(default=0)
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeArticleSummaryResponse(BaseModel):
    """Summary response for knowledge article list."""

    id: UUID
    tenant_id: UUID
    title: str
    source_url: Optional[str] = None
    category: Optional[IssueCategory] = None
    chunk_count: int = Field(default=0)
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeArticleListResponse(BaseModel):
    """Response schema for paginated knowledge article list."""

    articles: List[KnowledgeArticleSummaryResponse]
    total: int
    limit: int
    offset: int


class ChunkedDocument(BaseModel):
    """Schema for a chunked document in vector search."""

    doc_id: UUID
    title: str
    chunk_content: str
    source_url: Optional[str] = None
    category: Optional[IssueCategory] = None
    chunk_index: int
    score: Optional[float] = None
    rrf_score: Optional[float] = None

    class Config:
        from_attributes = True


class DocumentChunk(BaseModel):
    """Schema for a document chunk with metadata."""

    content: str
    start_char: int
    end_char: int
    chunk_index: int


class ChunkingResult(BaseModel):
    """Result of document chunking operation."""

    doc_id: Optional[UUID] = None
    chunks: List[DocumentChunk]
    total_chunks: int
    total_chars: int


class KnowledgeSearchRequest(BaseModel):
    """Request schema for hybrid knowledge search."""

    query: str = Field(..., min_length=1)
    tenant_id: UUID
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    limit: int = Field(default=10, ge=1, le=100)
    include_citations: bool = True
    category: Optional[IssueCategory] = None


class KnowledgeSearchResult(BaseModel):
    """Single search result item."""

    doc_id: UUID
    title: str
    content: str
    score: float
    rrf_score: Optional[float] = None
    source_url: Optional[str] = None
    category: Optional[IssueCategory] = None
    chunk_index: int
    updated_at: datetime


class KnowledgeSearchResponse(BaseModel):
    """Response schema for hybrid knowledge search."""

    results: List[KnowledgeSearchResult]
    query_id: UUID = Field(default_factory=UUID)
    latency_ms: int