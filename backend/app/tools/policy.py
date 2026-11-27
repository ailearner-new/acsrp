"""Tool policy definitions for approval gating and risk management."""

from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime


class RiskLevel(str, Enum):
    """Risk levels for tool actions."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Auto-execute thresholds by risk level
APPROVAL_THRESHOLDS = {
    RiskLevel.LOW: "always",           # Always auto-execute
    RiskLevel.MEDIUM: "tier_based",    # Tier change requires approval
    RiskLevel.HIGH: "approval",        # Always requires approval
    RiskLevel.CRITICAL: "approval",    # Always requires approval
}


@dataclass
class ToolDefinition:
    """Definition of a tool/action."""
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    risk_level: RiskLevel
    auto_execute_threshold: Optional[float] = None
    approval_required: bool = True
    category: str = "general"
    tenant_scoped: bool = False

    @property
    def requires_approval(self) -> bool:
        """Check if this tool requires approval based on risk level."""
        if APPROVAL_THRESHOLDS.get(self.risk_level) == "always":
            return False
        return self.approval_required


@dataclass
class Policy:
    """Policy for tool execution and approval.

    Policies define:
    - Which tools require approval
    - Approval thresholds based on risk level
    - Tenant isolation rules
    - Execution constraints
    """
    name: str
    risk_level: RiskLevel
    amount_threshold: Optional[float] = None  # For financial tools
    time_bound: bool = False  # Actions with time constraints
    rollback_available: bool = True  # Can this action be rolled back?
    notification_required: bool = False  # Notify stakeholders on execution

    # Approval requirements
    min_approver_role: Optional[str] = None
    requires_multiple_approvers: int = 1

    @property
    def auto_approve(self) -> bool:
        """Check if this policy allows auto-approval."""
        if self.risk_level == RiskLevel.LOW:
            return True
        if APPROVAL_THRESHOLDS.get(self.risk_level) == "always":
            return True
        if self.amount_threshold and self.amount_threshold <= 0:
            return True
        return False

    def check_approval_needed(self, context: Dict[str, Any]) -> bool:
        """Check if approval is needed based on context.

        Args:
            context: Dictionary with parameters like 'amount', 'tier', 'user_role', etc.

        Returns:
            True if approval is required, False otherwise
        """
        if self.auto_approve:
            return False

        # Check amount threshold for financial risks
        if self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            amount = context.get('amount', 0)
            if self.amount_threshold and amount > self.amount_threshold:
                return True

        # Check tenant tier for enterprise escalation
        tier = context.get('tier', 'STANDARD')
        if tier == "ENTERPRISE" and self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return True

        return True  # Default to requiring approval


@dataclass
class ApprovalPolicy:
    """Approval policy configuration for the action executor."""

    # Auto-execute thresholds by risk level
    auto_execute_amount_thresholds: Dict[RiskLevel, float] = field(default_factory=lambda: {
        RiskLevel.LOW: 0.0,      # Always auto-execute
        RiskLevel.MEDIUM: float('inf'),  # Requires approval for amounts > 0 (any amount)
        RiskLevel.HIGH: 0.0,     # Always requires approval
        RiskLevel.CRITICAL: 0.0, # Always requires approval
    })

    # Special thresholds for specific tools
    tool_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "billing.refund": 50.00,  # $50 threshold for refunds
        "subscription.change": float('inf'),  # Always requires approval
        "feature_flag.toggle": 0.0,  # Always requires approval
        "config.update": 0.0,  # Always requires approval
    })

    def get_threshold(self, tool_name: str, risk_level: RiskLevel, amount: Optional[float] = None) -> Optional[float]:
        """Get the approval threshold for a tool.

        Args:
            tool_name: Name of the tool
            risk_level: Default risk level
            amount: Optional monetary amount

        Returns:
            Threshold value or None if always requires approval
        """
        # Check tool-specific threshold first
        if tool_name in self.tool_thresholds:
            return self.tool_thresholds[tool_name]

        # Fall back to risk level threshold
        return self.auto_execute_amount_thresholds.get(risk_level)


@dataclass
class ToolExecutionContext:
    """Context for tool execution."""
    ticket_id: str
    tenant_id: str
    user_id: str
    user_role: str
    parameters: Dict[str, Any]
    requested_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_enterprise_customer(self) -> bool:
        """Check if this is an enterprise customer case."""
        return self.parameters.get('tier') == 'ENTERPRISE'


# Default tool definitions
DEFAULT_TOOLS = [
    ToolDefinition(
        name="customer.lookup",
        description="Look up customer information by email or ID",
        parameters_schema={"type": "object", "properties": {"email": {"type": "string"}}},
        risk_level=RiskLevel.LOW,
        approval_required=False,
        category="customer",
    ),
    ToolDefinition(
        name="subscription.get",
        description="Get subscription details for a customer",
        parameters_schema={"type": "object", "properties": {"customer_id": {"type": "string"}}},
        risk_level=RiskLevel.LOW,
        approval_required=False,
        category="billing",
    ),
    ToolDefinition(
        name="subscription.change",
        description="Change customer subscription tier or plan",
        parameters_schema={"type": "object", "properties": {
            "customer_id": {"type": "string"},
            "new_plan": {"type": "string"},
            "effective_date": {"type": "string", "format": "date"}
        }},
        risk_level=RiskLevel.MEDIUM,
        approval_required=True,
        category="billing",
    ),
    ToolDefinition(
        name="billing.refund",
        description="Issue a partial or full financial refund to a customer",
        parameters_schema={"type": "object", "properties": {
            "ticket_id": {"type": "string"},
            "customer_id": {"type": "string"},
            "amount": {"type": "number", "minimum": 0, "maximum": 500},
            "reason": {"type": "string", "minLength": 10}
        }},
        risk_level=RiskLevel.HIGH,
        approval_required=True,
        category="billing",
    ),
    ToolDefinition(
        name="account.password_reset",
        description="Reset customer password",
        parameters_schema={"type": "object", "properties": {
            "customer_id": {"type": "string"},
            "email": {"type": "string"}
        }},
        risk_level=RiskLevel.MEDIUM,
        approval_required=True,
        category="account",
    ),
    ToolDefinition(
        name="feature_flag.toggle",
        description="Toggle a feature flag for a tenant or customer",
        parameters_schema={"type": "object", "properties": {
            "flag_name": {"type": "string"},
            "enabled": {"type": "boolean"},
            "target": {"type": "string"}
        }},
        risk_level=RiskLevel.HIGH,
        approval_required=True,
        category="configuration",
    ),
    ToolDefinition(
        name="config.update",
        description="Update tenant or customer configuration",
        parameters_schema={"type": "object", "properties": {
            "config_path": {"type": "string"},
            "value": {},
            "scope": {"type": "string", "enum": ["tenant", "customer"]}
        }},
        risk_level=RiskLevel.HIGH,
        approval_required=True,
        category="configuration",
    ),
]


def get_default_policy() -> Policy:
    """Get the default approval policy."""
    return Policy(
        name="default_approval",
        risk_level=RiskLevel.HIGH,
        amount_threshold=50.00,  # $50 threshold
        requires_multiple_approvers=1,
    )