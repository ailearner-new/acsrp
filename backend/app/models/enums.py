"""Enums for the application."""

import enum


class ChannelType(str, enum.Enum):
    """Supported communication channels."""

    EMAIL = "EMAIL"
    CHAT = "CHAT"
    TICKET_ZENDESK = "TICKET_ZENDESK"
    TICKET_INTERCOM = "TICKET_INTERCOM"
    IN_APP = "IN_APP"
    SLACK = "SLACK"


class SeverityLevel(str, enum.Enum):
    """Ticket severity levels."""

    LOW_P3 = "LOW_P3"
    MEDIUM_P2 = "MEDIUM_P2"
    HIGH_P1 = "HIGH_P1"
    CRITICAL_P0 = "CRITICAL_P0"


class TicketStatus(str, enum.Enum):
    """Ticket lifecycle statuses."""

    NEW = "NEW"
    PROCESSING = "PROCESSING"
    AWAITING_CUSTOMER = "AWAITING_CUSTOMER"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class ActionRiskLevel(str, enum.Enum):
    """Risk levels for autonomous actions."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionStatus(str, enum.Enum):
    """Action execution statuses."""

    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class RoleType(str, enum.Enum):
    """User roles."""

    SUPER_ADMIN = "SUPER_ADMIN"
    TENANT_ADMIN = "TENANT_ADMIN"
    SUPPORT_MANAGER = "SUPPORT_MANAGER"
    TIER1_AGENT = "TIER1_AGENT"
    TIER2_ENGINEER = "TIER2_ENGINEER"
    READ_ONLY = "READ_ONLY"


class CustomerTier(str, enum.Enum):
    """Customer subscription tiers."""

    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"


class SenderType(str, enum.Enum):
    """Message sender types."""

    CUSTOMER = "CUSTOMER"
    AI_AGENT = "AI_AGENT"
    HUMAN_AGENT = "HUMAN_AGENT"
    SYSTEM = "SYSTEM"


class IssueCategory(str, enum.Enum):
    """Issue categories."""

    ACCOUNT_ACCESS = "ACCOUNT_ACCESS"
    BILLING_SUBSCRIPTION = "BILLING_SUBSCRIPTION"
    FEATURE_HOW_TO = "FEATURE_HOW_TO"
    BASIC_TROUBLESHOOTING = "BASIC_TROUBLESHOOTING"
    ORDER_STATUS = "ORDER_STATUS"
    TECHNICAL_BUG = "TECHNICAL_BUG"
    API_ISSUE = "API_ISSUE"
    INTEGRATION_PROBLEM = "INTEGRATION_PROBLEM"
    COMPLEX_BILLING_DISPUTE = "COMPLEX_BILLING_DISPUTE"
    FEATURE_REQUEST = "FEATURE_REQUEST"