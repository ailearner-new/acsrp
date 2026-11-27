"""Tests for model imports and basic instantiation."""

import pytest
import uuid

from backend.app.models import (
    Base,
    IDMixin,
    TimestampMixin,
    TenantMixin,
    ChannelType,
    SeverityLevel,
    TicketStatus,
    ActionRiskLevel,
    ActionStatus,
    RoleType,
    CustomerTier,
    SenderType,
    IssueCategory,
    Tenant,
    User,
    Customer,
    Ticket,
    TicketMessage,
    ActionAudit,
    ResolvedCase,
)


def test_imports():
    """Test that all models can be imported."""
    assert Base is not None
    assert IDMixin is not None
    assert TimestampMixin is not None
    assert TenantMixin is not None


def test_tenant_model():
    """Test Tenant model creation."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test Tenant",
        domain="test.example.com",
    )
    assert tenant.name == "Test Tenant"
    assert tenant.domain == "test.example.com"
    assert tenant.config == {}


def test_user_model():
    """Test User model creation."""
    tenant_id = uuid.uuid4()
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="agent@example.com",
        password_hash="hashed_password",
        full_name="Test Agent",
        role="TIER1_AGENT",
    )
    assert user.email == "agent@example.com"
    assert user.role == "TIER1_AGENT"
    assert user.skills == []
    assert user.is_active is True


def test_customer_model():
    """Test Customer model creation."""
    tenant_id = uuid.uuid4()
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="customer@example.com",
        full_name="John Doe",
        organization="Acme Corp",
        tier="PREMIUM",
    )
    assert customer.email == "customer@example.com"
    assert customer.tier == "PREMIUM"
    assert customer.metadata == {}


def test_ticket_model():
    """Test Ticket model creation."""
    tenant_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    ticket = Ticket(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        customer_id=customer_id,
        channel="CHAT",
        subject="Test ticket",
        severity="MEDIUM_P2",
        category="BILLING_SUBSCRIPTION",
    )
    assert ticket.channel == "CHAT"
    assert ticket.severity == "MEDIUM_P2"
    assert ticket.category == "BILLING_SUBSCRIPTION"
    assert ticket.status == "NEW"
    assert ticket.is_autonomous_resolved is False


def test_action_audit_model():
    """Test ActionAudit model creation."""
    tenant_id = uuid.uuid4()
    ticket_id = uuid.uuid4()
    action = ActionAudit(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        ticket_id=ticket_id,
        action_name="issue_refund",
        tool_name="billing.refund",
        risk_level="HIGH",
        parameters={"amount": 50, "currency": "USD"},
        requested_by="resolution_agent",
    )
    assert action.action_name == "issue_refund"
    assert action.risk_level == "HIGH"
    assert action.status == "PENDING_APPROVAL"


def test_resolved_case_model():
    """Test ResolvedCase model creation."""
    tenant_id = uuid.uuid4()
    case = ResolvedCase(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        issue_summary="Customer couldn't reset password",
        root_cause="Expired reset token",
        resolution_steps="Sent new reset link with 24h expiry",
        category="ACCOUNT_ACCESS",
    )
    assert case.issue_summary == "Customer couldn't reset password"
    assert case.root_cause == "Expired reset token"
    assert case.category == "ACCOUNT_ACCESS"