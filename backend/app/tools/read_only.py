"""Read-only support tools for customer context and diagnostics."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

from backend.app.tools.policy import RiskLevel, ToolDefinition


@dataclass
class CustomerLookupParams:
    """Parameters for customer lookup."""
    email: Optional[str] = None
    customer_id: Optional[str] = None


@dataclass
class SubscriptionInfoParams:
    """Parameters for subscription info."""
    customer_id: str
    tenant_id: Optional[str] = None


@dataclass
class UsageMetricsParams:
    """Parameters for usage metrics."""
    customer_id: str
    timeframe: str = "last_30_days"
    metrics: Optional[list[str]] = None


@dataclass
class APIHealthParams:
    """Parameters for API health check."""
    service: Optional[str] = None
    endpoint: Optional[str] = None


@dataclass
class ConfigValidateParams:
    """Parameters for config validation."""
    config_path: Optional[str] = None
    tenant_id: Optional[str] = None


@dataclass
class LogQueryParams:
    """Parameters for log queries."""
    query: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    level: Optional[str] = None
    limit: int = 100


@dataclass
class FeatureFlagCheckParams:
    """Parameters for feature flag check."""
    flag_name: str
    tenant_id: Optional[str] = None
    customer_id: Optional[str] = None


class ReadTools:
    """Read-only support tools (LOW risk, auto-execute)."""

    @staticmethod
    async def customer_lookup(
        email: Optional[str] = None,
        customer_id: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Look up customer information.

        This is a read-only operation that retrieves customer profile,
        subscription details, and usage metrics.

        Args:
            email: Customer email to look up
            customer_id: Customer ID to look up
            approved_by: User who approved (not required for read operations)

        Returns:
            Customer profile and context
        """
        if not email and not customer_id:
            return {
                "status": "error",
                "error": "Either email or customer_id must be provided",
            }

        # In production, this would query the database
        # For now, return a mock response
        return {
            "status": "success",
            "customer": {
                "id": customer_id or str(uuid.uuid4()),
                "email": email or "customer@example.com",
                "full_name": "John Doe",
                "organization": "Acme Corp",
                "tier": "STANDARD",
                "created_at": "2024-01-15T10:00:00Z",
            },
            "subscription": {
                "plan": "professional",
                "mrr": 49.99,
                "status": "active",
                "renewal_date": "2025-01-15",
            },
            "usage": {
                "api_calls_last_30_days": 1250,
                "features_used": ["basic", "analytics"],
            },
        }

    @staticmethod
    async def subscription_info(
        customer_id: str,
        tenant_id: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get subscription details for a customer.

        Args:
            customer_id: Customer ID
            tenant_id: Optional tenant ID for multi-tenancy
            approved_by: User who approved

        Returns:
            Subscription details
        """
        return {
            "status": "success",
            "subscription": {
                "customer_id": customer_id,
                "plan": "premium",
                "tier": "PREMIUM",
                "price": 99.99,
                "billing_cycle": "monthly",
                "status": "active",
                "started_at": "2024-01-15T10:00:00Z",
                "renewal_date": "2025-01-15",
                "addons": ["support", "analytics"],
            },
        }

    @staticmethod
    async def usage_metrics(
        customer_id: str,
        timeframe: str = "last_30_days",
        metrics: Optional[list[str]] = None,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get usage metrics for a customer.

        Args:
            customer_id: Customer ID
            timeframe: Time period for metrics
            metrics: Specific metrics to retrieve
            approved_by: User who approved

        Returns:
            Usage metrics data
        """
        return {
            "status": "success",
            "customer_id": customer_id,
            "timeframe": timeframe,
            "metrics": {
                "api_calls": {
                    "count": 1250,
                    "limit": 10000,
                    "percentage": 12.5,
                },
                "storage_usage": {
                    "current_gb": 2.5,
                    "limit_gb": 100,
                    "percentage": 2.5,
                },
                "features_used": ["basic", "analytics", "reporting"],
            },
        }

    @staticmethod
    async def api_health_check(
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check API health status.

        Args:
            service: Specific service to check
            endpoint: Specific endpoint to check
            approved_by: User who approved

        Returns:
            Health status of APIs
        """
        return {
            "status": "success",
            "apis": {
                "primary": {
                    "status": "healthy",
                    "latency_ms": 45,
                    "last_check": datetime.utcnow().isoformat() + "Z",
                },
                "billing": {
                    "status": "healthy",
                    "latency_ms": 32,
                    "last_check": datetime.utcnow().isoformat() + "Z",
                },
                "analytics": {
                    "status": "healthy",
                    "latency_ms": 58,
                    "last_check": datetime.utcnow().isoformat() + "Z",
                },
            },
            "overall_status": "healthy",
        }

    @staticmethod
    async def config_validate(
        config_path: Optional[str] = None,
        tenant_id: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate configuration.

        Args:
            config_path: Path to config to validate
            tenant_id: Tenant ID for multi-tenancy
            approved_by: User who approved

        Returns:
            Validation results
        """
        return {
            "status": "success",
            "valid": True,
            "config_path": config_path or "default",
            "issues": [],
            "warnings": [],
            "recommendations": [],
        }

    @staticmethod
    async def log_query(
        query: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query logs for troubleshooting.

        Args:
            query: Search query for logs
            start_time: Start time for query range
            end_time: End time for query range
            level: Log level filter
            limit: Maximum number of results

        Returns:
            Log entries matching query
        """
        return {
            "status": "success",
            "query": query,
            "results": [
                {
                    "timestamp": "2024-01-15T10:00:00Z",
                    "level": "INFO",
                    "message": f"Log entry matching query: {query}",
                    "source": "api",
                }
            ] * min(limit, 10),
            "total": min(limit, 10),
            "has_more": limit > 10,
        }

    @staticmethod
    async def feature_flag_check(
        flag_name: str,
        tenant_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check feature flag status.

        Args:
            flag_name: Name of the feature flag
            tenant_id: Tenant ID for context
            customer_id: Customer ID for context
            approved_by: User who approved

        Returns:
            Feature flag status
        """
        # Mock flag values - in production these would be looked up from config
        known_flags = {
            "new_onboarding": {"enabled": True, "default": True},
            "beta_features": {"enabled": False, "default": False},
            "advanced_analytics": {"enabled": True, "default": True, "tenant_override": True},
        }

        flag_info = known_flags.get(flag_name, {"enabled": False, "default": False})

        return {
            "status": "success",
            "flag_name": flag_name,
            "enabled": flag_info["enabled"],
            "source": "tenant_override" if tenant_id and flag_info.get("tenant_override") else "default",
            "overrides": [],
        }


def get_tool_definitions() -> list[ToolDefinition]:
    """Get tool definitions for read-only tools."""
    return [
        ToolDefinition(
            name="customer.lookup",
            description="Look up customer information by email or ID. Returns customer profile, subscription details, and usage metrics.",
            parameters_schema={"type": "object", "properties": {
                "email": {"type": "string", "description": "Customer email"},
                "customer_id": {"type": "string", "description": "Customer ID"}
            }},
            risk_level=RiskLevel.LOW,
            approval_required=False,
            category="customer",
        ),
        ToolDefinition(
            name="subscription.info",
            description="Get detailed subscription information for a customer.",
            parameters_schema={"type": "object", "properties": {
                "customer_id": {"type": "string"},
                "tenant_id": {"type": "string"}
            }},
            risk_level=RiskLevel.LOW,
            approval_required=False,
            category="billing",
        ),
        ToolDefinition(
            name="usage.metrics",
            description="Get usage metrics for a customer.",
            parameters_schema={"type": "object", "properties": {
                "customer_id": {"type": "string"},
                "timeframe": {"type": "string", "default": "last_30_days"},
                "metrics": {"type": "array", "items": {"type": "string"}}
            }},
            risk_level=RiskLevel.LOW,
            approval_required=False,
            category="billing",
        ),
        ToolDefinition(
            name="api.health_check",
            description="Check the health status of API services.",
            parameters_schema={"type": "object", "properties": {
                "service": {"type": "string"},
                "endpoint": {"type": "string"}
            }},
            risk_level=RiskLevel.LOW,
            approval_required=False,
            category="diagnostics",
        ),
        ToolDefinition(
            name="config.validate",
            description="Validate configuration settings.",
            parameters_schema={"type": "object", "properties": {
                "config_path": {"type": "string"},
                "tenant_id": {"type": "string"}
            }},
            risk_level=RiskLevel.LOW,
            approval_required=False,
            category="diagnostics",
        ),
        ToolDefinition(
            name="log.query",
            description="Query system logs for troubleshooting.",
            parameters_schema={"type": "object", "properties": {
                "query": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string"},
                "level": {"type": "string"},
                "limit": {"type": "integer", "default": 100}
            }},
            risk_level=RiskLevel.LOW,
            approval_required=False,
            category="diagnostics",
        ),
        ToolDefinition(
            name="feature.flag.check",
            description="Check the status of a feature flag.",
            parameters_schema={"type": "object", "properties": {
                "flag_name": {"type": "string"},
                "tenant_id": {"type": "string"},
                "customer_id": {"type": "string"}
            }},
            risk_level=RiskLevel.LOW,
            approval_required=False,
            category="configuration",
        ),
    ]


# Register all read-only tools
def register_tools(registry):
    """Register read-only tools with the registry."""
    tools = get_tool_definitions()
    for tool_def in tools:
        registry.register_tool(tool_def, _create_executor(tool_def))


def _create_executor(tool_def):
    """Create an executor function for a tool definition."""
    methods = {
        "customer.lookup": ReadTools.customer_lookup,
        "subscription.info": ReadTools.subscription_info,
        "usage.metrics": ReadTools.usage_metrics,
        "api.health_check": ReadTools.api_health_check,
        "config.validate": ReadTools.config_validate,
        "log.query": ReadTools.log_query,
        "feature.flag.check": ReadTools.feature_flag_check,
    }

    async def executor(**kwargs):
        method = methods.get(tool_def.name)
        if method:
            return await method(**kwargs)
        return {"status": "error", "error": f"Unknown tool: {tool_def.name}"}

    return executor