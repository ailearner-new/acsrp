"""Escalation and severity rules for the Autonomous Customer Support Platform.

This module defines the business rules for:
1. Escalation triggers - when to escalate tickets to human agents
2. Severity determination - how to classify ticket severity (only raises, never lowers)

These rules are used by the LangGraph workflow for routing decisions.
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime


class SeverityLevel(str, Enum):
    """Ticket severity levels.

    Ordered from lowest to highest severity.
    """
    LOW_P3 = "LOW_P3"
    MEDIUM_P2 = "MEDIUM_P2"
    HIGH_P1 = "HIGH_P1"
    CRITICAL_P0 = "CRITICAL_P0"


class EscalationTrigger(str, Enum):
    """Reasons for escalating a ticket."""
    CRITICAL_SEVERITY = "CRITICAL_SEVERITY"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    ENTERPRISE_NEGATIVE_SENTIMENT = "ENTERPRISE_NEGATIVE_SENTIMENT"
    NO_KNOWLEDGE_RESULTS = "NO_KNOWLEDGE_RESULTS"
    HIGH_RISK_ACTION_PENDING = "HIGH_RISK_ACTION_PENDING"
    MANUAL_ESCALATION = "MANUAL_ESCALATION"
    POLICY_MATCH = "POLICY_MATCH"
    SLA_BREACH_IMMINENT = "SLA_BREACH_IMMINENT"


@dataclass
class EscalationRule:
    """Rule defining when a ticket should be escalated.

    Attributes:
        name: Unique identifier for this rule
        trigger: The escalation trigger type
        condition: Callable that evaluates the condition
        priority: Lower number = higher priority (evaluated first)
        enabled: Whether this rule is active
        description: Human-readable description of the rule
    """
    name: str
    trigger: EscalationTrigger
    condition: Callable[[Dict[str, Any]], bool]
    priority: int = 100
    enabled: bool = True
    description: str = ""

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate if this escalation rule applies.

        Args:
            context: Dictionary containing ticket state, customer info, etc.

        Returns:
            True if the escalation condition is met
        """
        if not self.enabled:
            return False
        return self.condition(context)


@dataclass
class SeverityRule:
    """Rule for determining ticket severity.

    Severity rules can only RAISE severity, never lower it.
    This ensures we don't accidentally downgrade important tickets.

    Attributes:
        name: Unique identifier for this rule
        condition: Callable that evaluates if this rule applies
        severity: The severity level to set if condition matches
        priority: Lower number = higher priority (evaluated first)
        enabled: Whether this rule is active
        description: Human-readable description
    """
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: SeverityLevel
    priority: int = 100
    enabled: bool = True
    description: str = ""

    def evaluate(self, context: Dict[str, Any]) -> Optional[SeverityLevel]:
        """Evaluate if this severity rule applies.

        Args:
            context: Dictionary containing ticket data

        Returns:
            SeverityLevel if condition matches, None otherwise
        """
        if not self.enabled:
            return None
        if self.condition(context):
            return self.severity
        return None


# =============================================================================
# Escalation Conditions
# =============================================================================

def is_critical_severity(context: Dict[str, Any]) -> bool:
    """Check if ticket has CRITICAL_P0 severity."""
    severity = context.get("severity", "")
    return severity == SeverityLevel.CRITICAL_P0.value or severity == "CRITICAL_P0"


def is_low_confidence(context: Dict[str, Any]) -> bool:
    """Check if confidence score is below threshold (0.65)."""
    confidence = context.get("confidence_score", 1.0)
    threshold = context.get("confidence_threshold", 0.65)
    return confidence < threshold


def is_enterprise_negative_sentiment(context: Dict[str, Any]) -> bool:
    """Check if enterprise customer with negative sentiment."""
    tier = context.get("customer", {}).get("tier", "")
    sentiment = context.get("sentiment_score", 0.0)
    threshold = context.get("sentiment_threshold", -0.8)
    return tier == "ENTERPRISE" and sentiment < threshold


def is_no_knowledge_results(context: Dict[str, Any]) -> bool:
    """Check if knowledge retrieval returned no results."""
    retrieved_docs = context.get("retrieved_docs", [])
    return len(retrieved_docs) == 0


def has_high_risk_action_pending(context: Dict[str, Any]) -> bool:
    """Check if there are high-risk actions pending approval."""
    proposed_actions = context.get("proposed_actions", [])
    for action in proposed_actions:
        if action.get("requires_approval", False):
            risk = action.get("risk_level", "")
            if risk in ("HIGH", "CRITICAL"):
                return True
    return False


def is_manual_escalation(context: Dict[str, Any]) -> bool:
    """Check if manual escalation was requested."""
    return context.get("is_escalated", False) or context.get("manual_escalation", False)


def is_policy_match(context: Dict[str, Any]) -> bool:
    """Check if escalation policy matches."""
    policy_match = context.get("policy_match", False)
    escalation_reason = context.get("escalation_reason", "")
    return policy_match or escalation_reason == "POLICY_MATCH"


def is_sla_breach_imminent(context: Dict[str, Any]) -> bool:
    """Check if SLA breach is imminent."""
    return context.get("sla_breach_imminent", False)


# =============================================================================
# Severity Conditions
# =============================================================================

def is_billing_refund_request(context: Dict[str, Any]) -> bool:
    """Check if this is a billing/refund request."""
    intent = context.get("intent", "").lower()
    category = context.get("category", "").lower()
    content = context.get("content", "").lower()

    billing_keywords = ["refund", "billing", "charge", "payment", "invoice", "credit"]
    return (
        "billing" in intent or
        "refund" in intent or
        "billing" in category or
        any(kw in content for kw in billing_keywords)
    )


def is_technical_bug(context: Dict[str, Any]) -> bool:
    """Check if this is a technical bug report."""
    intent = context.get("intent", "").lower()
    category = context.get("category", "").lower()
    content = context.get("content", "").lower()

    bug_keywords = ["bug", "error", "crash", "broken", "not working", "issue"]
    return (
        "technical" in intent or
        "bug" in category or
        any(kw in content for kw in bug_keywords)
    )


def is_account_access_issue(context: Dict[str, Any]) -> bool:
    """Check if this is an account access issue."""
    intent = context.get("intent", "").lower()
    category = context.get("category", "").lower()
    content = context.get("content", "").lower()

    access_keywords = ["login", "password", "access", "locked", "cannot sign in", "account"]
    return (
        "account" in intent or
        "access" in category or
        any(kw in content for kw in access_keywords)
    )


def is_api_issue(context: Dict[str, Any]) -> bool:
    """Check if this is an API-related issue."""
    intent = context.get("intent", "").lower()
    category = context.get("category", "").lower()
    content = context.get("content", "").lower()

    api_keywords = ["api", "endpoint", "integration", "webhook", "sdk", "developer"]
    return (
        "api" in intent or
        "api" in category or
        "integration" in category or
        any(kw in content for kw in api_keywords)
    )


def is_enterprise_customer(context: Dict[str, Any]) -> bool:
    """Check if customer is enterprise tier."""
    tier = context.get("customer", {}).get("tier", "")
    return tier == "ENTERPRISE"


def has_high_mrr_customer(context: Dict[str, Any]) -> bool:
    """Check if customer has high MRR (> $1000)."""
    mrr = context.get("customer", {}).get("mrr", 0)
    threshold = context.get("high_mrr_threshold", 1000)
    return mrr >= threshold


def is_very_negative_sentiment(context: Dict[str, Any]) -> bool:
    """Check if sentiment is very negative (< -0.5)."""
    sentiment = context.get("sentiment_score", 0.0)
    threshold = context.get("negative_sentiment_threshold", -0.5)
    return sentiment < threshold


def is_repeated_ticket(context: Dict[str, Any]) -> bool:
    """Check if this is a repeated/recurring issue."""
    open_tickets = context.get("customer", {}).get("open_tickets_count", 0)
    return open_tickets > 1


# =============================================================================
# Default Escalation Rules
# =============================================================================

DEFAULT_ESCALATION_RULES: List[EscalationRule] = [
    # Critical severity always escalates (highest priority)
    EscalationRule(
        name="critical_severity",
        trigger=EscalationTrigger.CRITICAL_SEVERITY,
        condition=is_critical_severity,
        priority=1,
        enabled=True,
        description="CRITICAL_P0 severity tickets always escalate",
    ),

    # Low confidence after resolution agent
    EscalationRule(
        name="low_confidence",
        trigger=EscalationTrigger.LOW_CONFIDENCE,
        condition=is_low_confidence,
        priority=10,
        enabled=True,
        description="Confidence score below 0.65 threshold",
    ),

    # Enterprise with negative sentiment
    EscalationRule(
        name="enterprise_negative_sentiment",
        trigger=EscalationTrigger.ENTERPRISE_NEGATIVE_SENTIMENT,
        condition=is_enterprise_negative_sentiment,
        priority=5,
        enabled=True,
        description="Enterprise customer with sentiment < -0.8",
    ),

    # No knowledge results
    EscalationRule(
        name="no_knowledge_results",
        trigger=EscalationTrigger.NO_KNOWLEDGE_RESULTS,
        condition=is_no_knowledge_results,
        priority=20,
        enabled=True,
        description="No relevant knowledge documents found",
    ),

    # High-risk action pending
    EscalationRule(
        name="high_risk_action_pending",
        trigger=EscalationTrigger.HIGH_RISK_ACTION_PENDING,
        condition=has_high_risk_action_pending,
        priority=15,
        enabled=True,
        description="HIGH or CRITICAL risk action requires approval",
    ),

    # Manual escalation
    EscalationRule(
        name="manual_escalation",
        trigger=EscalationTrigger.MANUAL_ESCALATION,
        condition=is_manual_escalation,
        priority=2,
        enabled=True,
        description="Manual escalation requested by agent or system",
    ),

    # Policy match
    EscalationRule(
        name="policy_match",
        trigger=EscalationTrigger.POLICY_MATCH,
        condition=is_policy_match,
        priority=25,
        enabled=True,
        description="Escalation policy rule matched",
    ),

    # SLA breach imminent
    EscalationRule(
        name="sla_breach_imminent",
        trigger=EscalationTrigger.SLA_BREACH_IMMINENT,
        condition=is_sla_breach_imminent,
        priority=50,
        enabled=True,
        description="SLA breach is imminent",
    ),
]


# =============================================================================
# Default Severity Rules
# =============================================================================

DEFAULT_SEVERITY_RULES: List[SeverityRule] = [
    # CRITICAL_P0 rules (highest severity)
    SeverityRule(
        name="critical_enterprise_high_mrr",
        condition=lambda ctx: (
            is_enterprise_customer(ctx) and
            has_high_mrr_customer(ctx) and
            is_very_negative_sentiment(ctx)
        ),
        severity=SeverityLevel.CRITICAL_P0,
        priority=1,
        description="Enterprise + High MRR + Very negative sentiment",
    ),

    SeverityRule(
        name="critical_repeated_issue",
        condition=lambda ctx: is_repeated_ticket(ctx) and is_very_negative_sentiment(ctx),
        severity=SeverityLevel.CRITICAL_P0,
        priority=2,
        description="Repeated issue with very negative sentiment",
    ),

    # HIGH_P1 rules
    SeverityRule(
        name="high_billing_large_amount",
        condition=lambda ctx: is_billing_refund_request(ctx) and ctx.get("amount", 0) > 100,
        severity=SeverityLevel.HIGH_P1,
        priority=10,
        description="Billing/refund request with amount > $100",
    ),

    SeverityRule(
        name="high_api_issue_enterprise",
        condition=lambda ctx: is_api_issue(ctx) and is_enterprise_customer(ctx),
        severity=SeverityLevel.HIGH_P1,
        priority=11,
        description="API issue for enterprise customer",
    ),

    SeverityRule(
        name="high_account_access",
        condition=lambda ctx: is_account_access_issue(ctx),
        severity=SeverityLevel.HIGH_P1,
        priority=12,
        description="Account access issues (login, password)",
    ),

    SeverityRule(
        name="high_technical_bug",
        condition=is_technical_bug,
        severity=SeverityLevel.HIGH_P1,
        priority=13,
        description="Technical bug reports",
    ),

    SeverityRule(
        name="high_negative_sentiment",
        condition=is_very_negative_sentiment,
        severity=SeverityLevel.HIGH_P1,
        priority=14,
        description="Very negative sentiment (< -0.5)",
    ),

    # MEDIUM_P2 rules (default)
    SeverityRule(
        name="medium_enterprise",
        condition=is_enterprise_customer,
        severity=SeverityLevel.MEDIUM_P2,
        priority=50,
        description="Enterprise customer (default elevated)",
    ),

    SeverityRule(
        name="medium_repeated_ticket",
        condition=is_repeated_ticket,
        severity=SeverityLevel.MEDIUM_P2,
        priority=51,
        description="Customer has multiple open tickets",
    ),
]


# =============================================================================
# Evaluation Functions
# =============================================================================

def evaluate_escalation(
    context: Dict[str, Any],
    rules: Optional[List[EscalationRule]] = None,
) -> tuple[bool, Optional[EscalationTrigger], str]:
    """Evaluate if a ticket should be escalated.

    Args:
        context: Dictionary containing ticket state, customer info, etc.
        rules: Optional list of escalation rules (uses DEFAULT_ESCALATION_RULES if None)

    Returns:
        Tuple of (should_escalate, trigger_reason, description)
    """
    if rules is None:
        rules = DEFAULT_ESCALATION_RULES

    # Sort rules by priority (lower = higher priority)
    sorted_rules = sorted(rules, key=lambda r: r.priority)

    for rule in sorted_rules:
        if rule.evaluate(context):
            return (True, rule.trigger, rule.description)

    return (False, None, "")


def calculate_severity(
    context: Dict[str, Any],
    rules: Optional[List[SeverityRule]] = None,
    current_severity: Optional[SeverityLevel] = None,
) -> SeverityLevel:
    """Calculate ticket severity based on rules.

    IMPORTANT: Severity can only be RAISED, never lowered.
    If current_severity is provided, the result will be >= current_severity.

    Args:
        context: Dictionary containing ticket data
        rules: Optional list of severity rules (uses DEFAULT_SEVERITY_RULES if None)
        current_severity: Current severity level (if any)

    Returns:
        Calculated SeverityLevel (never lower than current_severity)
    """
    if rules is None:
        rules = DEFAULT_SEVERITY_RULES

    # Sort rules by priority (lower = higher priority)
    sorted_rules = sorted(rules, key=lambda r: r.priority)

    # Find highest matching severity
    highest_severity = None
    for rule in sorted_rules:
        severity = rule.evaluate(context)
        if severity is not None:
            highest_severity = severity
            break  # First match wins due to priority sorting

    # Default to MEDIUM_P2 if no rules matched
    if highest_severity is None:
        highest_severity = SeverityLevel.MEDIUM_P2

    # Never lower severity - only raise
    if current_severity is not None:
        if _severity_value(highest_severity) < _severity_value(current_severity):
            return current_severity

    return highest_severity


def _severity_value(severity: SeverityLevel) -> int:
    """Convert severity to numeric value for comparison.

    Higher value = higher severity.
    """
    values = {
        SeverityLevel.LOW_P3: 0,
        SeverityLevel.MEDIUM_P2: 1,
        SeverityLevel.HIGH_P1: 2,
        SeverityLevel.CRITICAL_P0: 3,
    }
    return values.get(severity, 1)


# =============================================================================
# LangGraph Routing Helpers
# =============================================================================

def route_after_customer(state: Dict[str, Any]) -> str:
    """Routing logic after customer agent.

    This function is used by LangGraph to determine the next node.

    Args:
        state: LangGraph SupportState dictionary

    Returns:
        Next node name: "escalation_agent" or "knowledge_agent"
    """
    should_escalate, _, _ = evaluate_escalation(state)

    if should_escalate:
        return "escalation_agent"
    return "knowledge_agent"


def route_after_knowledge(state: Dict[str, Any]) -> str:
    """Routing logic after knowledge agent.

    Args:
        state: LangGraph SupportState dictionary

    Returns:
        Next node name: "troubleshooting_agent" or "resolution_agent"
    """
    retrieved_docs = state.get("retrieved_docs", [])
    confidence = state.get("confidence_score", 1.0)

    if not retrieved_docs or confidence < 0.4:
        return "troubleshooting_agent"
    return "resolution_agent"


def route_after_resolution(state: Dict[str, Any]) -> str:
    """Routing logic after resolution agent.

    Args:
        state: LangGraph SupportState dictionary

    Returns:
        Next node name: "escalation_agent", "human_approval_node", or END
    """
    confidence = state.get("confidence_score", 1.0)
    is_escalated = state.get("is_escalated", False)
    proposed_actions = state.get("proposed_actions", [])

    # Low confidence -> escalate
    if confidence < 0.65 or is_escalated:
        return "escalation_agent"

    # High-risk actions -> human approval
    has_high_risk = any(
        a.get("requires_approval", False)
        for a in proposed_actions
    )
    if has_high_risk:
        return "human_approval_node"

    return "END"


# =============================================================================
# Utility Functions
# =============================================================================

def get_escalation_triggers(context: Dict[str, Any]) -> List[EscalationTrigger]:
    """Get all escalation triggers that apply.

    Unlike evaluate_escalation which returns the first match,
    this returns all matching triggers for debugging/analysis.

    Args:
        context: Dictionary containing ticket state

    Returns:
        List of all matching EscalationTrigger values
    """
    triggers = []
    for rule in DEFAULT_ESCALATION_RULES:
        if rule.evaluate(context):
            triggers.append(rule.trigger)
    return triggers


def explain_severity_decision(
    context: Dict[str, Any],
    current_severity: Optional[SeverityLevel] = None,
) -> Dict[str, Any]:
    """Explain why a severity level was assigned.

    Useful for debugging and agent transparency.

    Args:
        context: Dictionary containing ticket data
        current_severity: Current severity if any

    Returns:
        Dictionary with explanation details
    """
    matched_rules = []
    for rule in DEFAULT_SEVERITY_RULES:
        severity = rule.evaluate(context)
        if severity is not None:
            matched_rules.append({
                "rule_name": rule.name,
                "severity": severity.value,
                "description": rule.description,
            })

    final_severity = calculate_severity(context, current_severity=current_severity)

    return {
        "final_severity": final_severity.value,
        "matched_rules": matched_rules,
        "current_severity": current_severity.value if current_severity else None,
        "was_raised": (
            _severity_value(final_severity) > _severity_value(current_severity)
            if current_severity else False
        ),
    }
