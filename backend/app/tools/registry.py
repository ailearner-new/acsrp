"""Tool registry for MCP tools and action catalog."""

import uuid
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from backend.app.tools.policy import RiskLevel, ToolDefinition, Policy


class ToolStatus(str, Enum):
    """Status of a registered tool."""
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    DISABLED = "DISABLED"


@dataclass
class RegisteredTool:
    """A registered tool with its execution function."""
    definition: ToolDefinition
    execute: Callable[..., Awaitable[Dict[str, Any]]]
    status: ToolStatus = ToolStatus.ACTIVE
    description: str = ""

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def risk_level(self) -> RiskLevel:
        return self.definition.risk_level

    @property
    def requires_approval(self) -> bool:
        return self.definition.requires_approval


class ToolRegistry:
    """Registry for MCP tools and actions.

    Manages tool registration, policy enforcement, and execution routing.
    This is the central catalog for all actions that agents can take.
    """

    _instance: Optional['ToolRegistry'] = None
    _tools: Dict[str, RegisteredTool] = {}

    def __init__(self, policies: Optional[List[Policy]] = None):
        """Initialize the tool registry.

        Args:
            policies: List of policies for approval gating
        """
        if ToolRegistry._instance is not None:
            raise RuntimeError("ToolRegistry is a singleton. Use get_instance().")

        self.policies = policies or []
        self._tool_callbacks: Dict[str, Callable] = {}
        self._lock = False

        # Pre-register default tools
        for tool_def in _load_default_tools():
            self.register_tool(tool_def, _create_mock_executor(tool_def))

    @classmethod
    def get_instance(cls) -> 'ToolRegistry':
        """Get the singleton instance of the registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_tool(self, definition: ToolDefinition, execute: Callable) -> None:
        """Register a new tool.

        Args:
            definition: Tool definition
            execute: Async function to execute the tool
        """
        if self._lock:
            raise RuntimeError("Cannot register tools after registry is locked")

        tool = RegisteredTool(
            definition=definition,
            execute=execute,
            status=ToolStatus.ACTIVE,
        )
        self._tools[definition.name] = tool

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool.

        Args:
            name: Tool name

        Returns:
            True if tool was unregistered
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get_tool(self, name: str) -> Optional[RegisteredTool]:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            RegisteredTool or None if not found
        """
        return self._tools.get(name)

    def list_tools(
        self,
        category: Optional[str] = None,
        risk_level: Optional[RiskLevel] = None,
        status: Optional[ToolStatus] = None,
        tenant_id: Optional[str] = None,
    ) -> List[RegisteredTool]:
        """List registered tools with optional filters.

        Args:
            category: Filter by category
            risk_level: Filter by risk level
            status: Filter by status
            tenant_id: Include only tenant-scoped tools

        Returns:
            List of matching tools
        """
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.definition.category == category]

        if risk_level:
            tools = [t for t in tools if t.risk_level == risk_level]

        if status:
            tools = [t for t in tools if t.status == status]

        return tools

    def get_tools_by_risk_level(self, max_risk: RiskLevel) -> List[RegisteredTool]:
        """Get all tools with risk level up to max_risk.

        Args:
            max_risk: Maximum risk level to include

        Returns:
            List of tools with risk <= max_risk
        """
        risk_order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}
        max_level = risk_order.get(max_risk, 3)

        return [t for t in self._tools.values()
                if risk_order.get(t.risk_level, 3) <= max_level]

    def check_approval_needed(
        self,
        tool_name: str,
        context: Dict[str, Any],
    ) -> bool:
        """Check if a tool execution requires approval.

        Args:
            tool_name: Name of the tool
            context: Execution context (parameters, tenant, user info, etc.)

        Returns:
            True if approval is required
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return True  # Unknown tools require approval by default

        # Check if tool requires approval by definition
        if not tool.definition.requires_approval:
            return False

        # Check policies
        for policy in self.policies:
            if policy.check_approval_needed(context):
                return True

        # Check amount threshold for financial risks
        if tool.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            amount = context.get('parameters', {}).get('amount', 0)
            if amount and amount > 50.00:
                return True

        # Enterprise customers always need approval for HIGH/CRITICAL
        tier = context.get('parameters', {}).get('tier', context.get('tier', 'STANDARD'))
        if tier == "ENTERPRISE" and tool.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return True

        return False

    def execute_tool(
        self,
        name: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        approved_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a tool.

        Args:
            name: Tool name
            params: Tool parameters
            context: Execution context
            approved_by: User ID who approved (if applicable)

        Returns:
            Execution result
        """
        import asyncio

        tool = self.get_tool(name)
        if not tool:
            return {
                "status": "ERROR",
                "error": f"Tool '{name}' not found",
            }

        if tool.status != ToolStatus.ACTIVE:
            return {
                "status": "ERROR",
                "error": f"Tool '{name}' is not active (status: {tool.status})",
            }

        # Check approval
        if tool.definition.requires_approval and not approved_by:
            return {
                "status": "REQUIRES_APPROVAL",
                "message": f"Tool '{name}' requires approval",
                "action_required": True,
            }

        # Execute the tool
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(tool.execute(**params, approved_by=approved_by))
            return {"status": "SUCCESS", **result}
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
            }

    def lock(self) -> None:
        """Lock the registry to prevent further modifications."""
        self._lock = True

    def __repr__(self) -> str:
        return f"ToolRegistry(tools={len(self._tools)}, policies={len(self.policies)})"


async def _tool_executor_mock(
    name: str,
    description: str,
    **kwargs
) -> Dict[str, Any]:
    """Mock tool executor for testing purposes.

    In production, this would call actual implementations.
    """
    import uuid
    from datetime import datetime

    # Simulate execution delay
    import asyncio
    await asyncio.sleep(0.1)

    return {
        "status": "success",
        "result": f"Executed {name}",
        "execution_id": str(uuid.uuid4()),
        "executed_at": datetime.utcnow().isoformat(),
        "parameters": kwargs,
    }


def _load_default_tools() -> List[ToolDefinition]:
    """Load default tool definitions."""
    from backend.app.tools.policy import DEFAULT_TOOLS
    return DEFAULT_TOOLS


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return ToolRegistry.get_instance()


# Factory function for creating the registry
def create_registry(
    policies: Optional[List[Policy]] = None,
    with_defaults: bool = True,
) -> ToolRegistry:
    """Create a new tool registry.

    Use this for testing or multi-tenant scenarios where you need
    isolated registries.

    Args:
        policies: Optional list of approval policies
        with_defaults: Whether to pre-register default tools

    Returns:
        New ToolRegistry instance
    """
    # Clear instance for testing
    ToolRegistry._instance = None

    registry = ToolRegistry(policies=policies or [])

    if with_defaults:
        for tool_def in _load_default_tools():
            registry.register_tool(tool_def, _create_mock_executor(tool_def))

    return registry


def _create_mock_executor(tool_def: ToolDefinition) -> Callable:
    """Create a mock executor for a tool definition."""
    async def executor(**kwargs):
        if tool_def.name == "billing.refund":
            amount = kwargs.get('amount', 0)
            return {
                "status": "SUCCESS",
                "transaction_id": f"tx_refund_{uuid.uuid4().hex[:8]}",
                "amount": amount,
                "message": f"Refund of ${amount} processed",
            }
        elif tool_def.name == "subscription.change":
            return {
                "status": "SUCCESS",
                "message": "Subscription changed",
                "changes": kwargs,
            }
        elif tool_def.name == "feature_flag.toggle":
            return {
                "status": "SUCCESS",
                "message": f"Feature flag {kwargs.get('flag_name')} toggled to {kwargs.get('enabled')}",
            }
        else:
            return {
                "status": "success",
                "message": f"Tool {tool_def.name} executed",
            }

    return executor