"""Base repository with common CRUD operations and tenant context handling."""

from typing import Any, Optional, TypeVar, Generic, List
from uuid import UUID
from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.database import db_manager

T = TypeVar("T", bound=object)


class BaseRepository(Generic[T]):
    """Base repository with common operations and tenant context support."""

    def __init__(self, model_class: type[T], session_factory=None):
        self.model_class = model_class
        self.session_factory = session_factory or db_manager.session_factory

    async def get_by_id(self, id: UUID, *, tenant_id: UUID | None = None) -> Optional[T]:
        """Get entity by ID with optional tenant filtering."""
        async with db_manager.session() as session:
            stmt = select(self.model_class).where(self.model_class.id == id)
            if tenant_id is not None:
                stmt = stmt.where(self.model_class.tenant_id == tenant_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        tenant_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[T]:
        """Get all entities with optional tenant filtering and pagination."""
        async with db_manager.session() as session:
            stmt = select(self.model_class).offset(offset).limit(limit)
            if tenant_id is not None:
                stmt = stmt.where(self.model_class.tenant_id == tenant_id)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def create(self, **kwargs: Any) -> T:
        """Create a new entity."""
        async with db_manager.session() as session:
            entity = self.model_class(**kwargs)
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            return entity

    async def update(self, id: UUID, **kwargs: Any) -> Optional[T]:
        """Update an entity by ID."""
        async with db_manager.session() as session:
            entity = await session.get(self.model_class, id)
            if entity is None:
                return None
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            await session.commit()
            await session.refresh(entity)
            return entity

    async def delete(self, id: UUID, *, tenant_id: UUID | None = None) -> bool:
        """Delete an entity by ID. Returns True if deleted."""
        async with db_manager.session() as session:
            stmt = delete(self.model_class).where(self.model_class.id == id)
            if tenant_id is not None:
                stmt = stmt.where(self.model_class.tenant_id == tenant_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def count(self, *, tenant_id: UUID | None = None) -> int:
        """Count entities with optional tenant filtering."""
        async with db_manager.session() as session:
            stmt = select(func.count()).select_from(self.model_class)
            if tenant_id is not None:
                stmt = stmt.where(self.model_class.tenant_id == tenant_id)
            result = await session.execute(stmt)
            return result.scalar_one()