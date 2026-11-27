# ADR-006: Human-in-the-Loop for All Write Actions Above Risk Threshold

## Status
Accepted

## Context
Autonomous actions carry risk:
- Financial: refunds, billing changes
- Account: password resets, profile updates
- Configuration: feature flags, system config
- Provisioning: resource creation/deletion

Need safety guardrail that balances autonomy with control.

Evaluated options:
1. **No HITL** - Full autonomy, high risk
2. **HITL for all actions** - Maximum safety, no autonomy
3. **Risk-tiered HITL** - LOW auto, MEDIUM+HIGH require approval
4. **Confidence-tiered HITL** - Low confidence requires approval

## Decision
Implement **risk-tiered HITL**: All write actions with risk level ≥ MEDIUM require human approval. LOW risk actions auto-execute. Risk levels: LOW, MEDIUM, HIGH, CRITICAL.

## Consequences

### Positive
- Safety: Financial/account/config changes never execute without approval
- Autonomy: Read actions and LOW-risk writes auto-execute
- Audit trail: Every action logged with approval status
- Compliance: Meets SOC 2, financial control requirements

### Negative
- Latency: Approval workflow adds minutes to resolution
- Complexity: Approval UI, queue, notification system needed
- Agent frustration: May delay autonomous resolution

## Implementation Notes
- Risk levels in MCP tool definitions:
  - LOW: `customer.lookup`, `subscription.get`, `billing.invoice.get`, `config.get`, `api.health_check`
  - MEDIUM: `subscription.change` (tier change), `account.password_reset`, `account.update_profile`, `log.query`, `ticket.create`, `ticket.update`, `notification.send`
  - HIGH: `billing.refund` (always), `feature_flag.toggle`, `config.update`
  - CRITICAL: Provisioning, DB mutations (Phase 2+)
- Approval API: `POST /api/v1/actions/{action_id}/approve`
- Approval UI: Pending queue with context, risk assessment, rollback plan
- Immutable audit log: who, what, when, result, approval chain

## Related
- ADR-001: LangGraph Orchestration (HITL node in graph)
- ADR-007: Action Execution Framework (MCP tools)