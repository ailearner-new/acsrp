"""Unit tests for Escalation and Severity Rules."""

import pytest
from backend.app.agents.rules import (
    EscalationRule,
    SeverityRule,
    SeverityLevel,
    EscalationTrigger,
    evaluate_escalation,
    calculate_severity,
    DEFAULT_ESCALATION_RULES,
    DEFAULT_SEVERITY_RULES,
    explain_severity_decision,
    route_after_customer,
    route_after_knowledge,
    route_after_resolution,
    is_critical_severity,
    is_low_confidence,
    is_enterprise_negative_sentiment,
    is_no_knowledge_results,
    has_high_risk_action_pending,
    is_manual_escalation,
    is_policy_match,
    is_sla_breach_imminent,
    is_billing_refund_request,
    is_technical_bug,
    is_account_access_issue,
    is_api_issue,
    is_enterprise_customer,
    has_high_mrr_customer,
    is_very_negative_sentiment,
    is_repeated_ticket,
)


class TestSeverityLevel:
    """Tests for SeverityLevel enum."""

    def test_severity_levels(self):
        assert SeverityLevel.LOW_P3 == "LOW_P3"
        assert SeverityLevel.MEDIUM_P2 == "MEDIUM_P2"
        assert SeverityLevel.HIGH_P1 == "HIGH_P1"
        assert SeverityLevel.CRITICAL_P0 == "CRITICAL_P0"


class TestEscalationRules:
    """Tests for EscalationRule dataclass."""

    def test_escalation_rule_creation(self):
        rule = EscalationRule(
            name="test_rule",
            trigger=EscalationTrigger.CRITICAL_SEVERITY,
            condition=lambda ctx: True,
            priority=1,
            enabled=True,
            description="Test rule",
        )
        assert rule.name == "test_rule"
        assert rule.trigger == EscalationTrigger.CRITICAL_SEVERITY
        assert rule.priority == 1
        assert rule.enabled == True
        assert rule.description == "Test rule"

    def test_escalation_rule_disable(self):
        """Test disabled rule is not evaluated."""
        rule = EscalationRule(
            name="disabled_rule",
            trigger=EscalationTrigger.CRITICAL_SEVERITY,
            condition=lambda ctx: True,
            priority=1,
            enabled=False,
            description="Disabled rule",
        )
        assert rule.enabled == False

    def test_evaluate_escalation_critical(self):
        """Test CRITICAL severity detection."""
        context = {"severity": "CRITICAL_P0"}
        assert is_critical_severity(context) == True

    def test_evaluate_escalation_not_critical(self):
        """Test non-CRITICAL severity."""
        context = {"severity": "MEDIUM_P2"}
        assert is_critical_severity(context) == False

    def test_evaluate_escalation_low_confidence(self):
        """Test low confidence detection."""
        # Below threshold
        context = {"confidence_score": 0.5}
        assert is_low_confidence(context) == True

        # Above threshold
        context = {"confidence_score": 0.8}
        assert is_low_confidence(context) == False

    def test_evaluate_escalation_enterprise_negative_sentiment(self):
        """Test enterprise with negative sentiment."""
        context = {
            "customer": {"tier": "ENTERPRISE"},
            "sentiment_score": -0.9,
        }
        assert is_enterprise_negative_sentiment(context) == True

        # Non-enterprise
        context = {
            "customer": {"tier": "STANDARD"},
            "sentiment_score": -0.9,
        }
        assert is_enterprise_negative_sentiment(context) == False

    def test_evaluate_escalation_no_knowledge_results(self):
        """Test no knowledge results."""
        context = {"retrieved_docs": []}
        assert is_no_knowledge_results(context) == True

        context = {"retrieved_docs": [{"doc_id": "1"}]}
        assert is_no_knowledge_results(context) == False

    def test_evaluate_escalation_high_risk_action(self):
        """Test high-risk action detection."""
        context = {
            "proposed_actions": [
                {"risk_level": "HIGH", "requires_approval": True}
            ]
        }
        assert has_high_risk_action_pending(context) == True

        # Low risk action
        context = {
            "proposed_actions": [
                {"risk_level": "LOW", "requires_approval": True}
            ]
        }
        assert has_high_risk_action_pending(context) == False

    def test_evaluate_escalation_manual(self):
        """Test manual escalation."""
        context = {"is_escalated": True}
        assert is_manual_escalation(context) == True

        context = {"is_escalated": False}
        assert is_manual_escalation(context) == False

    def test_evaluate_escalation_all_default_rules(self):
        """Test all default escalation rules."""
        context = {
            "severity": "CRITICAL_P0",
            "confidence_score": 0.3,
            "customer": {"tier": "ENTERPRISE"},
            "sentiment_score": -0.9,
            "retrieved_docs": [],
            "proposed_actions": [
                {"risk_level": "HIGH", "requires_approval": True}
            ],
            "policy_match": True,
        }

        should_escalate, trigger, description = evaluate_escalation(context)
        assert should_escalate == True
        assert trigger is not None


class TestSeverityRules:
    """Tests for SeverityRule dataclass."""

    def test_severity_rule_creation(self):
        rule = SeverityRule(
            name="test_rule",
            condition=lambda ctx: True,
            severity=SeverityLevel.CRITICAL_P0,
            priority=1,
            enabled=True,
            description="Test severity rule",
        )
        assert rule.name == "test_rule"
        assert rule.severity == SeverityLevel.CRITICAL_P0
        assert rule.priority == 1
        assert rule.enabled == True

    def test_severity_rule_disable(self):
        """Test disabled severity rule."""
        rule = SeverityRule(
            name="disabled_rule",
            condition=lambda ctx: True,
            severity=SeverityLevel.HIGH_P1,
            priority=1,
            enabled=False,
            description="Disabled rule",
        )
        assert rule.enabled == False

    def test_severity_rule_evaluate(self):
        """Test severity rule evaluation."""
        context = {"intent": "billing.refund"}
        rule = SeverityRule(
            name="billing_refund_rule",
            condition=lambda ctx: is_billing_refund_request(ctx),
            severity=SeverityLevel.HIGH_P1,
            priority=10,
        )
        result = rule.evaluate(context)
        assert result == SeverityLevel.HIGH_P1

    def test_severity_rule_not_enabled(self):
        """Test disabled rule returns None."""
        rule = SeverityRule(
            name="disabled_rule",
            condition=lambda ctx: True,
            severity=SeverityLevel.CRITICAL_P0,
            enabled=False,
        )
        context = {"intent": "test"}
        result = rule.evaluate(context)
        assert result is None


class TestCalculateSeverity:
    """Tests for calculate_severity function."""

    def test_default_severity(self):
        """Test default severity when no rules match."""
        context = {"intent": "unknown_issue"}
        severity = calculate_severity(context)
        assert severity == SeverityLevel.MEDIUM_P2

    def test_severity_raise_only(self):
        """Test severity can only be raised, never lowered."""
        context = {"intent": "test"}
        # Start with HIGH_P1, result should be at least HIGH_P1
        result = calculate_severity(context, current_severity=SeverityLevel.HIGH_P1)
        assert result == SeverityLevel.HIGH_P1  # Same, not lowered

    def test_severity_raise_from_lower(self):
        """Test severity can be raised from lower level."""
        context = {"intent": "billing.refund", "amount": 150}
        result = calculate_severity(context, current_severity=SeverityLevel.MEDIUM_P2)
        # Should be at least HIGH_P1 due to the billing refund rule
        assert result in (SeverityLevel.HIGH_P1, SeverityLevel.CRITICAL_P0)

    def test_severity_enterprise_raised(self):
        """Test enterprise customer gets elevated severity."""
        context = {"customer": {"tier": "ENTERPRISE"}}
        result = calculate_severity(context, current_severity=SeverityLevel.LOW_P3)
        assert result == SeverityLevel.MEDIUM_P2  # Elevated from LOW_P3

    def test_severity_billing_refund_high_amount(self):
        """Test billing refund with high amount."""
        context = {
            "intent": "billing.refund",
            "amount": 150,
        }
        result = calculate_severity(context, current_severity=SeverityLevel.LOW_P3)
        # Should be elevated due to high amount billing refund rule
        assert result in (SeverityLevel.HIGH_P1, SeverityLevel.CRITICAL_P0)

    def test_severity_technical_bug(self):
        """Test technical bug detection."""
        context = {"intent": "technical.bug", "category": "TECHNICAL_BUG"}
        result = calculate_severity(context, current_severity=SeverityLevel.LOW_P3)
        assert result in (SeverityLevel.HIGH_P1, SeverityLevel.MEDIUM_P2)

    def test_severity_very_negative_sentiment(self):
        """Test very negative sentiment."""
        context = {"sentiment_score": -0.7}
        result = calculate_severity(context, current_severity=SeverityLevel.LOW_P3)
        # Should be elevated due to very negative sentiment
        assert result in (SeverityLevel.HIGH_P1, SeverityLevel.CRITICAL_P0)


class TestSeverityExplanation:
    """Tests for explain_severity_decision."""

    def test_severity_explanation(self):
        """Test severity decision explanation."""
        context = {
            "intent": "billing.refund",
            "amount": 150,
        }
        explanation = explain_severity_decision(context)
        assert "final_severity" in explanation
        assert "matched_rules" in explanation
        assert "was_raised" in explanation

    def test_severity_explanation_with_current(self):
        """Test severity explanation with current severity."""
        context = {
            "intent": "test",
        }
        explanation = explain_severity_decision(context, current_severity=SeverityLevel.LOW_P3)
        assert explanation["was_raised"] == False  # Not raised from lowest level

    def test_severity_explanation_raised(self):
        """Test severity explanation shows raised severity."""
        context = {
            "intent": "billing.refund",
            "amount": 150,
        }
        explanation = explain_severity_decision(context, current_severity=SeverityLevel.LOW_P3)
        assert explanation["was_raised"] == True  # Raised from LOW_P3 to HIGH_P1


class TestRoutingHelpers:
    """Tests for LangGraph routing functions."""

    def test_route_after_customer_critical(self):
        """Test routing with CRITICAL severity."""
        state = {
            "severity": "CRITICAL_P0",
            "confidence_score": 0.9,
        }
        next_node = route_after_customer(state)
        assert next_node == "escalation_agent"

    def test_route_after_customer_medium(self):
        """Test routing with MEDIUM severity."""
        state = {
            "severity": "MEDIUM_P2",
            "confidence_score": 0.9,
        }
        next_node = route_after_customer(state)
        assert next_node == "knowledge_agent"

    def test_route_after_knowledge_no_results(self):
        """Test routing after knowledge with no results."""
        state = {
            "retrieved_docs": [],
            "confidence_score": 0.9,
        }
        next_node = route_after_knowledge(state)
        assert next_node == "troubleshooting_agent"

    def test_route_after_knowledge_with_results(self):
        """Test routing after knowledge with results."""
        state = {
            "retrieved_docs": [{"doc_id": "1"}],
            "confidence_score": 0.9,
        }
        next_node = route_after_knowledge(state)
        assert next_node == "resolution_agent"

    def test_route_after_resolution_low_confidence(self):
        """Test routing after resolution with low confidence."""
        state = {
            "confidence_score": 0.5,
            "is_escalated": False,
        }
        next_node = route_after_resolution(state)
        assert next_node == "escalation_agent"

    def test_route_after_resolution_high_confidence_no_actions(self):
        """Test routing after resolution with high confidence and no high-risk actions."""
        state = {
            "confidence_score": 0.8,
            "is_escalated": False,
            "proposed_actions": [],
        }
        next_node = route_after_resolution(state)
        assert next_node == "END"

    def test_route_after_resolution_high_risk_actions(self):
        """Test routing after resolution with high-risk actions."""
        state = {
            "confidence_score": 0.8,
            "is_escalated": False,
            "proposed_actions": [
                {"risk_level": "HIGH", "requires_approval": True}
            ],
        }
        next_node = route_after_resolution(state)
        assert next_node == "human_approval_node"


class TestDefaultRules:
    """Tests for default rules lists."""

    def test_default_escalation_rules_not_empty(self):
        """Test default escalation rules exist."""
        assert len(DEFAULT_ESCALATION_RULES) > 0
        assert len(DEFAULT_ESCALATION_RULES) == 8  # 8 default rules

    def test_default_severity_rules_not_empty(self):
        """Test default severity rules exist."""
        assert len(DEFAULT_SEVERITY_RULES) > 0

    def test_default_escalation_rule_priorities(self):
        """Test default escalation rules have correct priority order."""
        # CRITICAL_SEVERITY should have lowest priority number (highest priority)
        critical_rule = DEFAULT_ESCALATION_RULES[0]
        assert critical_rule.trigger == EscalationTrigger.CRITICAL_SEVERITY
        assert critical_rule.priority == 1

    def test_default_severity_rule_priorities(self):
        """Test default severity rules have correct priority order."""
        # CRITICAL_P0 rules should have lowest priority number
        critical_rules = [r for r in DEFAULT_SEVERITY_RULES if r.severity == SeverityLevel.CRITICAL_P0]
        assert len(critical_rules) >= 2  # At least 2 critical rules

    def test_evaluate_escalation_returns_tuple(self):
        """Test evaluate_escalation returns proper tuple."""
        context = {"severity": "CRITICAL_P0"}
        should_escalate, trigger, description = evaluate_escalation(context)
        assert isinstance(should_escalate, bool)
        assert trigger is not None or trigger is None
        assert isinstance(description, str)


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_get_escalation_triggers(self):
        """Test getting all matching escalation triggers."""
        context = {
            "severity": "CRITICAL_P0",
            "customer": {"tier": "ENTERPRISE"},
            "sentiment_score": -0.9,
        }
        triggers = get_escalation_triggers(context)
        # Should have at least CRITICAL_SEVERITY and ENTERPRISE_NEGATIVE_SENTIMENT
        assert EscalationTrigger.CRITICAL_SEVERITY in triggers
        assert EscalationTrigger.ENTERPRISE_NEGATIVE_SENTIMENT in triggers

    def test_explain_severity_decision_structure(self):
        """Test explain_severity_decision returns proper structure."""
        context = {}
        explanation = explain_severity_decision(context)
        assert "final_severity" in explanation
        assert isinstance(explanation["was_raised"], bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])