"""User repository."""

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.app.models.user import User
from backend.app.repositories.base import BaseRepository
from backend.app.models.enums import RoleType


class UserRepository(BaseRepository[User]):
    """Repository for User model."""

    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, email: str, *, tenant_id: str | None = None) -> Optional[User]:
        """Get user by email."""
        async with db_manager.session() as session:
            stmt = select(User).where(User.email == email)
            if tenant_id is not None:
                stmt = stmt.where(User.tenant_id == tenant_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_role(self, role: RoleType, *, tenant_id: str | None = None) -> list[User]:
        """Get users by role."""
        async with db_manager.session() as session:
            stmt = select(User).where(User.role == role)
            if tenant_id is not None:
                stmt = stmt.where(User.tenant_id == tenant_id)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def count_by_role(self, role: RoleType, *, tenant_id: UUID) -> int:
        """Count users by role in tenant."""
        async with db_manager.session() as session:
            stmt = select(func.count()).select_from(User).where(User.role == role, User.tenant_id == tenant_id)
            result = await session.execute(stmt)
            return result.scalar_one()