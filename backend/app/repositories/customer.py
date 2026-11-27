"""Customer repository."""

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.app.models.customer import Customer
from backend.app.repositories.base import BaseRepository
from backend.app.models.enums import CustomerTier


class CustomerRepository(BaseRepository[Customer]):
    """Repository for Customer model."""

    def __init__(self):
        super().__init__(Customer)

    async def get_by_email(self, email: str, *, tenant_id: str | None = None) -> Optional[Customer]:
        """Get customer by email."""
        async with db_manager.session() as session:
            stmt = select(Customer).where(Customer.email == email)
            if tenant_id is not None:
                stmt = stmt.where(Customer.tenant_id == tenant_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_tier(self, tier: CustomerTier, *, tenant_id: str | None = None) -> list[Customer]:
        """Get customers by tier."""
        async with db_manager.session() as session:
            stmt = select(Customer).where(Customer.tier == tier)
            if tenant_id is not None:
                stmt = stmt.where(Customer.tenant_id == tenant_id)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def count_by_tier(self, *, tenant_id: UUID, tier: CustomerTier) -> int:
        """Count customers by tier in tenant."""
        async with db_manager.session() as session:
            stmt = select(func.count()).select_from(Customer).where(Customer.tier == tier, Customer.tenant_id == tenant_id)
            result = await session.execute(stmt)
            return result.scalar_one()