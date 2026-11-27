"""Models package initialization."""

from backend.app.models.base import Base, IDMixin, TimestampMixin, TenantMixin
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
from backend.app.models.tenant import Tenant
from backend.app.models.user import User
from backend.app.models.customer import Customer
from backend.app.models.ticket import Ticket, TicketMessage
from backend.app.models.action import ActionAudit
from backend.app.models.case import ResolvedCase
from backend.app.models.article import KnowledgeArticle

__all__ = [
    # Base
    "Base",
    "IDMixin",
    "TimestampMixin",
    "TenantMixin",
    # Enums
    "ChannelType",
    "SeverityLevel",
    "TicketStatus",
    "ActionRiskLevel",
    "ActionStatus",
    "RoleType",
    "CustomerTier",
    "SenderType",
    "IssueCategory",
    # Models
    "Tenant",
    "User",
    "Customer",
    "Ticket",
    "TicketMessage",
    "ActionAudit",
    "ResolvedCase",
    "KnowledgeArticle",
]