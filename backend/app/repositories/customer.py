"""Customer repository."""

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple
from uuid import UUID

from backend.app.models.customer import Customer
from backend.app.repositories.base import BaseRepository
from backend.app.models.enums import CustomerTier
from backend.app.core.database import db_manager


class CustomerRepository(BaseRepository[Customer]):
    """Repository for Customer model."""

    def __init__(self):
        super().__init__(Customer)

    async def get_by_email(self, tenant_id: UUID, email: str) -> Optional[Customer]:
        """Get customer by email for a specific tenant."""
        async with db_manager.session() as session:
            stmt = select(Customer).where(
                Customer.email == email,
                Customer.tenant_id == tenant_id
            )
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

    async def list_customers(self, filters: dict, limit: int = 50, offset: int = 0, *, tenant_id: UUID | None = None) -> Tuple[List[Customer], int]:
        """List customers with filters and pagination.

        Args:
            filters: Filter criteria (email, tier, organization)
            limit: Maximum number of results
            offset: Pagination offset
            tenant_id: Optional tenant filter for multi-tenancy
        """
        async with db_manager.session() as session:
            stmt = select(Customer)
            count_stmt = select(func.count()).select_from(Customer)

            if tenant_id is not None:
                stmt = stmt.where(Customer.tenant_id == tenant_id)
                count_stmt = count_stmt.where(Customer.tenant_id == tenant_id)
            if "email" in filters:
                stmt = stmt.where(Customer.email.ilike(f"%{filters['email']}%"))
                count_stmt = count_stmt.where(Customer.email.ilike(f"%{filters['email']}%"))
            if "tier" in filters:
                stmt = stmt.where(Customer.tier == filters["tier"])
                count_stmt = count_stmt.where(Customer.tier == filters["tier"])
            if "organization" in filters:
                stmt = stmt.where(Customer.organization.ilike(f"%{filters['organization']}%"))
                count_stmt = count_stmt.where(Customer.organization.ilike(f"%{filters['organization']}%"))

            stmt = stmt.order_by(Customer.created_at.desc()).limit(limit).offset(offset)
            result = await session.execute(stmt)
            customers = result.scalars().all()

            count_result = await session.execute(count_stmt)
            total = count_result.scalar_one()

            return list(customers), total