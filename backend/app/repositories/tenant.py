"""Tenant repository."""

from sqlalchemy import select

from backend.app.models.tenant import Tenant
from backend.app.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    """Repository for Tenant model."""

    def __init__(self):
        super().__init__(Tenant)

    async def get_by_domain(self, domain: str, *, tenant_id: str | None = None) -> Optional[Tenant]:
        """Get tenant by domain."""
        async with db_manager.session() as session:
            stmt = select(Tenant).where(Tenant.domain == domain)
            if tenant_id is not None:
                stmt = stmt.where(Tenant.id == tenant_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def count_users(self, *, tenant_id: UUID) -> int:
        """Count users in tenant."""
        async with db_manager.session() as session:
            stmt = select(func.count()).select_from(Tenant).where(Tenant.id == tenant_id)
            # Will need func import
            return 0  # Placeholder - would need func import from sqlalchemy

    # Note: func import needed