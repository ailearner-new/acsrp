"""Seed script for ACS-RP demo data."""

import uuid
from datetime import datetime

from backend.app.core.config import get_settings
from backend.app.core.database import db_manager
from backend.app.models import Base, Tenant, User, Customer, Ticket, TicketMessage, ActionAudit, ResolvedCase
from backend.app.models.enums import (
    ChannelType,
    SeverityLevel,
    TicketStatus,
    ActionRiskLevel,
    ActionStatus,
    RoleType,
    CustomerTier,
    SenderType,
    IssueCategory,
)


def seed_tenants():
    """Seed default tenant."""
    settings = get_settings()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    tenant = Tenant(
        id=tenant_id,
        name="Acme Corp",
        domain="acme.example.com",
        config={},
    )
    # Use session to add
    print(f"Seeded tenant: {tenant.name} (id={tenant.id})")


def seed_users(tenant_id):
    """Seed sample users/agents."""
    users = [
        {
            "email": "admin@acme.example.com",
            "full_name": "Admin User",
            "role": RoleType.SUPER_ADMIN,
            "skills": [],
        },
        {
            "email": "tier1@acme.example.com",
            "full_name": "Tier 1 Agent",
            "role": RoleType.TIER1_AGENT,
            "skills": [],
        },
        {
            "email": "tier2@acme.example.com",
            "full_name": "Tier 2 Engineer",
            "role": RoleType.TIER2_ENGINEER,
            "skills": [],
        },
    ]

    for user_data in users:
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            **user_data,
        )
        print(f"Seeded user: {user.email} (role={user.role})")


def seed_customers(tenant_id):
    """Seed sample customers."""
    customers = [
        {
            "email": "john.doe@acme.com",
            "full_name": "John Doe",
            "organization": "Acme Inc",
            "tier": CustomerTier.PREMIUM,
        },
        {
            "email": "jane.smith@acme.com",
            "full_name": "Jane Smith",
            "organization": "Acme Inc",
            "tier": CustomerTier.STANDARD,
        },
    ]

    for cust_data in customers:
        customer = Customer(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            **cust_data,
        )
        print(f"Seeded customer: {customer.email} (tier={customer.tier})")


def seed_tickets(tenant_id, customer_map):
    """Seed sample tickets."""
    tickets = [
        {
            "channel": ChannelType.CHAT,
            "subject": "Billing issue - double charged",
            "severity": SeverityLevel.MEDIUM_P2,
            "category": IssueCategory.BILLING_SUBSCRIPTION,
            "sentiment_score": 0.3,
            "confidence_score": 0.85,
        },
        {
            "channel": ChannelType.EMAIL,
            "subject": "Password reset request",
            "severity": SeverityLevel.LOW_P3,
            "category": IssueCategory.ACCOUNT_ACCESS,
            "sentiment_score": -0.2,
            "confidence_score": 0.95,
        },
    ]

    for i, ticket_data in enumerate(tickets):
        customer_email = list(customer_map.keys())[i] if i < len(customer_map) else None
        customer_id = customer_map.get(customer_email) if customer_email else None

        ticket = Ticket(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            customer_id=customer_id,
            channel=ticket_data["channel"],
            subject=ticket_data["subject"],
            severity=ticket_data["severity"],
            category=ticket_data["category"],
            status=TicketStatus.NEW,
            is_autonomous_resolved=False,
            sentiment_score=ticket_data["sentiment_score"],
            confidence_score=ticket_data["confidence_score"],
            resolution_summary=None,
        )
        print(f"Seeded ticket: {ticket.subject} (id={ticket.id})")


def seed_sample_data():
    """Run the full demo data seeding."""
    import asyncio

    async def _seed():
        # Ensure tables exist
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        # Seed tenants
        seed_tenants()

        # Seed users
        seed_users(tenant_id)

        # Seed customers
        seed_customers(tenant_id)

        # Build customer map for tickets
        from backend.app.models import Customer
        async with db_manager.session() as session:
            result = await session.execute(
                Customer.__table__.select().where(Customer.tenant_id == tenant_id)
            )
            customers = result.scalars().all()
            customer_map = {c.email: c.id for c in customers}

        # Seed tickets
        seed_tickets(tenant_id, customer_map)

        print("\n✅ Demo data seeding complete!")

    asyncio.run(_seed())


if __name__ == "__main__":
    seed_sample_data()