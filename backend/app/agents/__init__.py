"""Agents module for the Autonomous Customer Support Platform.

This module contains the multi-agent orchestration and business rules
for ticket routing, escalation, and severity determination.
"""

from backend.app.agents.rules import (
    EscalationRule,
    EscalationTrigger,
    SeverityRule,
    SeverityLevel,
    evaluate_escalation,
    calculate_severity,
)

__all__ = [
    "EscalationRule",
    "EscalationTrigger",
    "SeverityRule",
    "SeverityLevel",
    "evaluate_escalation",
    "calculate_severity",
]