"""Agents module for the Autonomous Customer Support Platform.

This module contains the multi-agent orchestration and business rules
for ticket routing, escalation, severity determination, and security.

These rules and security measures are used by the LangGraph workflow
for routing decisions and input validation.
"""

from backend.app.agents.rules import (
    EscalationRule,
    EscalationTrigger,
    SeverityRule,
    SeverityLevel,
    evaluate_escalation,
    calculate_severity,
)
from backend.app.agents.security import (
    wrap_user_input,
    preprocess_agent_input,
    detect_prompt_injection,
    sanitize_input,
    PIIType,
    PIIRedactionRule,
    InjectionType,
    InjectionDetectionResult,
    is_suspicious_input,
    DEFAULT_SECURITY_CONFIG,
    DEFAULT_PII_RULES,
)

__all__ = [
    "EscalationRule",
    "EscalationTrigger",
    "SeverityRule",
    "SeverityLevel",
    "evaluate_escalation",
    "calculate_severity",
    "wrap_user_input",
    "preprocess_agent_input",
    "detect_prompt_injection",
    "sanitize_input",
    "PIIType",
    "PIIRedactionRule",
    "InjectionType",
    "InjectionDetectionResult",
    "is_suspicious_input",
    "DEFAULT_SECURITY_CONFIG",
    "DEFAULT_PII_RULES",
]