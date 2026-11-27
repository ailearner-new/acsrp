"""Approval-gated write tools for customer actions."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from backend.app.tools.policy import RiskLevel, ToolDefinition, Policy


class BillingTool:
    """Billing-related write tools (HIGH risk, always requires approval)."""

    @staticmethod
    async def refund(
        ticket_id: str,
        customer_id: str,
        amount: float,
        reason: str,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Issue a partial or full financial refund to a customer.

        This is a HIGH risk tool that always requires approval.
        Refunds over $50 require additional verification.

        Args:
            ticket_id: The ticket ID this refund is for
            customer_id: Customer ID receiving the refund
            amount: Refund amount (0 < amount <= 500)
            reason: Reason for the refund (min 10 chars)
            approved_by: User ID who approved the refund

        Returns:
            Refund execution result
        """
        if not approved_by:
            return {
                "status": "REQUIRES_APPROVAL",
                "message": f"Refund of ${amount} exceeds approval threshold. Approval ticket created.",
                "action_required": True,
                "approval_amount": amount,
            }

        if amount > 50.00 and not approved_by:
            return {
                "status": "REQUIRES_APPROVAL",
                "message": f"Refund of ${amount} exceeds $50 threshold. Approval ticket created.",
                "action_required": True,
            }

        # Simulate refund processing
        # In production, this would call Stripe/Billing API
        try:
            # Mock API call
            transaction_id = f"tx_refund_{uuid.uuid4().hex[:8]}"

            return {
                "status": "SUCCESS",
                "transaction_id": transaction_id,
                "amount": amount,
                "customer_id": customer_id,
                "ticket_id": ticket_id,
                "processed_by": approved_by,
                "processed_at": datetime.utcnow().isoformat() + "Z",
                "message": f"Refund of ${amount} issued to customer {customer_id}",
            }
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "amount": amount,
            }


class SubscriptionTool:
    """Subscription management tools (MEDIUM risk)."""

    @staticmethod
    async def change(
        customer_id: str,
        new_plan: str,
        effective_date: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Change a customer's subscription tier or plan.

        This is a MEDIUM risk tool that requires approval.

        Args:
            customer_id: Customer ID to update
            new_plan: New plan name
            effective_date: When the change takes effect
            approved_by: User ID who approved

        Returns:
            Subscription change result
        """
        if not approved_by:
            return {
                "status": "REQUIRES_APPROVAL",
                "message": "Subscription change requires approval",
                "action_required": True,
            }

        return {
            "status": "SUCCESS",
            "message": f"Subscription changed to {new_plan}",
            "customer_id": customer_id,
            "new_plan": new_plan,
            "effective_date": effective_date,
            "processed_by": approved_by,
            "processed_at": datetime.utcnow().isoformat() + "Z",
        }


class AccountTool:
    """Account management tools (MEDIUM risk)."""

    @staticmethod
    async def password_reset(
        customer_id: str,
        email: str,
        verified: bool = False,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reset a customer's password.

        This is a MEDIUM risk tool that requires verification.

        Args:
            customer_id: Customer ID to reset password for
            email: Customer email address
            verified: Whether identity was verified
            approved_by: User ID who approved

        Returns:
            Password reset result
        """
        if not verified and not approved_by:
            return {
                "status": "REQUIRES_APPROVAL",
                "message": "Password reset requires verification or approval",
                "action_required": True,
            }

        # Generate reset token
        reset_token = f"reset_{uuid.uuid4().hex[:16]}"
        reset_url = f"https://app.example.com/reset-password?token={reset_token}"

        return {
            "status": "SUCCESS",
            "message": "Password reset initiated",
            "customer_id": customer_id,
            "reset_url": reset_url,
            "expires_at": datetime.utcnow().isoformat() + "Z",
        }


class FeatureFlagTool:
    """Feature flag management tools (HIGH risk)."""

    @staticmethod
    async def toggle(
        flag_name: str,
        enabled: bool,
        scope: str = "tenant",
        target: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Toggle a feature flag.

        This is a HIGH risk tool that always requires approval.

        Args:
            flag_name: Name of the feature flag
            enabled: Whether to enable or disable
            scope: Toggle scope - "tenant" or "global"
            target: Target tenant/customer ID if scoped
            approved_by: User ID who approved

        Returns:
            Toggle result
        """
        if not approved_by:
            return {
                "status": "REQUIRES_APPROVAL",
                "message": f"Feature flag toggle requires approval",
                "action_required": True,
                "flag_name": flag_name,
                "new_value": enabled,
            }

        # Simulate toggle
        return {
            "status": "SUCCESS",
            "message": f"Feature flag {flag_name} toggled to {enabled}",
            "flag_name": flag_name,
            "enabled": enabled,
            "scope": scope,
            "target": target,
            "processed_by": approved_by,
            "processed_at": datetime.utcnow().isoformat() + "Z",
        }


class ConfigTool:
    """Configuration management tools (HIGH risk)."""

    @staticmethod
    async def update(
        config_path: str,
        value: Any,
        scope: str = "tenant",
        tenant_id: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update tenant or customer configuration.

        This is a HIGH risk tool that always requires approval.

        Args:
            config_path: Path to the configuration item
            value: New value to set
            scope: Update scope - "tenant" or "customer"
            tenant_id: Tenant ID for multi-tenancy
            approved_by: User ID who approved

        Returns:
            Update result
        """
        if not approved_by:
            return {
                "status": "REQUIRES_APPROVAL",
                "message": "Configuration update requires approval",
                "action_required": True,
                "config_path": config_path,
            }

        return {
            "status": "SUCCESS",
            "message": f"Configuration {config_path} updated",
            "config_path": config_path,
            "value": str(value)[:100],  # Truncate for safety
            "scope": scope,
            "tenant_id": tenant_id,
            "processed_by": approved_by,
            "processed_at": datetime.utcnow().isoformat() + "Z",
        }


def get_tool_definitions() -> list[ToolDefinition]:
    """Get tool definitions for write tools."""
    return [
        ToolDefinition(
            name="billing.refund",
            description="Issue a partial or full financial refund to a customer account. ALWAYS requires approval.",
            parameters_schema={"type": "object", "properties": {
                "ticket_id": {"type": "string"},
                "customer_id": {"type": "string"},
                "amount": {"type": "number", "minimum": 0, "maximum": 500},
                "reason": {"type": "string", "minLength": 10}
            }, "required": ["ticket_id", "customer_id", "amount", "reason"]},
            risk_level=RiskLevel.HIGH,
            approval_required=True,
            category="billing",
        ),
        ToolDefinition(
            name="subscription.change",
            description="Change customer subscription tier or plan.",
            parameters_schema={"type": "object", "properties": {
                "customer_id": {"type": "string"},
                "new_plan": {"type": "string"},
                "effective_date": {"type": "string", "format": "date"}
            }, "required": ["customer_id", "new_plan"]},
            risk_level=RiskLevel.MEDIUM,
            approval_required=True,
            category="billing",
        ),
        ToolDefinition(
            name="account.password_reset",
            description="Reset customer password.",
            parameters_schema={"type": "object", "properties": {
                "customer_id": {"type": "string"},
                "email": {"type": "string"},
                "verified": {"type": "boolean"}
            }, "required": ["customer_id", "email"]},
            risk_level=RiskLevel.MEDIUM,
            approval_required=True,
            category="account",
        ),
        ToolDefinition(
            name="feature_flag.toggle",
            description="Toggle a feature flag for a tenant or customer. ALWAYS requires approval.",
            parameters_schema={"type": "object", "properties": {
                "flag_name": {"type": "string"},
                "enabled": {"type": "boolean"},
                "scope": {"type": "string", "enum": ["tenant", "global"]},
                "target": {"type": "string"}
            }, "required": ["flag_name", "enabled"]},
            risk_level=RiskLevel.HIGH,
            approval_required=True,
            category="configuration",
        ),
        ToolDefinition(
            name="config.update",
            description="Update tenant or customer configuration. ALWAYS requires approval.",
            parameters_schema={"type": "object", "properties": {
                "config_path": {"type": "string"},
                "value": {},
                "scope": {"type": "string", "enum": ["tenant", "customer"]},
                "tenant_id": {"type": "string"}
            }, "required": ["config_path", "value"]},
            risk_level=RiskLevel.HIGH,
            approval_required=True,
            category="configuration",
        ),
    ]


# Tool method mapping
TOOL_METHODS = {
    "billing.refund": BillingTool.refund,
    "subscription.change": SubscriptionTool.change,
    "account.password_reset": AccountTool.password_reset,
    "feature_flag.toggle": FeatureFlagTool.toggle,
    "config.update": ConfigTool.update,
}


def register_tools(registry):
    """Register write tools with the registry."""
    definitions = get_tool_definitions()
    for defn in definitions:
        executor = _create_executor(defn)
        registry.register_tool(defn, executor)


def _create_executor(tool_def):
    """Create an executor function for a tool definition."""
    async def executor(**kwargs):
        method = TOOL_METHODS.get(tool_def.name)
        if method:
            return await method(**kwargs)
        return {"status": "error", "error": f"Unknown tool: {tool_def.name}"}

    return executor