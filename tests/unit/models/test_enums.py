"""Tests for enums."""

import pytest

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


def test_channel_type_enum():
    assert ChannelType.EMAIL == "EMAIL"
    assert ChannelType.CHAT == "CHAT"
    assert ChannelType.TICKET_ZENDESK == "TICKET_ZENDESK"
    assert ChannelType.TICKET_INTERCOM == "TICKET_INTERCOM"
    assert ChannelType.IN_APP == "IN_APP"
    assert ChannelType.SLACK == "SLACK"


def test_severity_level_enum():
    assert SeverityLevel.LOW_P3 == "LOW_P3"
    assert SeverityLevel.MEDIUM_P2 == "MEDIUM_P2"
    assert SeverityLevel.HIGH_P1 == "HIGH_P1"
    assert SeverityLevel.CRITICAL_P0 == "CRITICAL_P0"


def test_ticket_status_enum():
    assert TicketStatus.NEW == "NEW"
    assert TicketStatus.PROCESSING == "PROCESSING"
    assert TicketStatus.AWAITING_CUSTOMER == "AWAITING_CUSTOMER"
    assert TicketStatus.AWAITING_APPROVAL == "AWAITING_APPROVAL"
    assert TicketStatus.RESOLVED == "RESOLVED"
    assert TicketStatus.ESCALATED == "ESCALATED"
    assert TicketStatus.CLOSED == "CLOSED"


def test_action_risk_level_enum():
    assert ActionRiskLevel.LOW == "LOW"
    assert ActionRiskLevel.MEDIUM == "MEDIUM"
    assert ActionRiskLevel.HIGH == "HIGH"
    assert ActionRiskLevel.CRITICAL == "CRITICAL"


def test_action_status_enum():
    assert ActionStatus.PENDING_APPROVAL == "PENDING_APPROVAL"
    assert ActionStatus.APPROVED == "APPROVED"
    assert ActionStatus.REJECTED == "REJECTED"
    assert ActionStatus.EXECUTING == "EXECUTING"
    assert ActionStatus.SUCCESS == "SUCCESS"
    assert ActionStatus.FAILED == "FAILED"
    assert ActionStatus.ROLLED_BACK == "ROLLED_BACK"


def test_role_type_enum():
    assert RoleType.SUPER_ADMIN == "SUPER_ADMIN"
    assert RoleType.TENANT_ADMIN == "TENANT_ADMIN"
    assert RoleType.SUPPORT_MANAGER == "SUPPORT_MANAGER"
    assert RoleType.TIER1_AGENT == "TIER1_AGENT"
    assert RoleType.TIER2_ENGINEER == "TIER2_ENGINEER"
    assert RoleType.READ_ONLY == "READ_ONLY"


def test_customer_tier_enum():
    assert CustomerTier.STANDARD == "STANDARD"
    assert CustomerTier.PREMIUM == "PREMIUM"
    assert CustomerTier.ENTERPRISE == "ENTERPRISE"


def test_sender_type_enum():
    assert SenderType.CUSTOMER == "CUSTOMER"
    assert SenderType.AI_AGENT == "AI_AGENT"
    assert SenderType.HUMAN_AGENT == "HUMAN_AGENT"
    assert SenderType.SYSTEM == "SYSTEM"


def test_issue_category_enum():
    assert IssueCategory.ACCOUNT_ACCESS == "ACCOUNT_ACCESS"
    assert IssueCategory.BILLING_SUBSCRIPTION == "BILLING_SUBSCRIPTION"
    assert IssueCategory.FEATURE_HOW_TO == "FEATURE_HOW_TO"
    assert IssueCategory.BASIC_TROUBLESHOOTING == "BASIC_TROUBLESHOOTING"
    assert IssueCategory.ORDER_STATUS == "ORDER_STATUS"
    assert IssueCategory.TECHNICAL_BUG == "TECHNICAL_BUG"
    assert IssueCategory.API_ISSUE == "API_ISSUE"
    assert IssueCategory.INTEGRATION_PROBLEM == "INTEGRATION_PROBLEM"
    assert IssueCategory.COMPLEX_BILLING_DISPUTE == "COMPLEX_BILLING_DISPUTE"
    assert IssueCategory.FEATURE_REQUEST == "FEATURE_REQUEST"