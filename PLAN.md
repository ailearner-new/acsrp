# PLAN.md - Requirement Catalog and Exit Bar

## Requirement Catalog (from PRD/BRD)

### Functional Requirements (P0 - Must Have for MVP)

| ID | Requirement | Category | Exit Criteria |
|----|-------------|----------|---------------|
| **FR-01** | Multi-Channel Ingestion | Ingestion | Email, Chat, Zendesk, Intercom, In-App all ingest to normalized `SupportRequest` |
| **FR-02** | Request Understanding & Classification | Classification | Intent, entities, sentiment, severity (P0-P3), category extracted with ≥95% accuracy |
| **FR-03** | Customer Context Retrieval | Context | Customer 360° view retrieved in <1s with tenant isolation enforced |
| **FR-04** | Knowledge Retrieval (RAG) | RAG | Hybrid search (vector+BM25+graph) with RRF fusion, reranking, citations; Precision@5 ≥85% |
| **FR-05** | Troubleshooting & Diagnosis | Troubleshooting | Diagnostic steps executed, hypotheses generated, correlation with known issues |
| **FR-06** | Resolution Planning & Generation | Resolution | Structured plan with steps, outcomes, rollback; confidence scoring; customer + agent responses |
| **FR-07** | Action Execution | Actions | MCP tools for refunds, subscriptions, passwords, feature flags; approval gating; audit log |
| **FR-08** | Escalation Management | Escalation | Auto-escalate on confidence<70%, critical severity, enterprise tier; full context package |
| **FR-09** | Memory & Learning | Memory | Customer memory, case memory (pgvector), pattern extraction, feedback loops |
| **FR-10** | Human-in-the-Loop (Agent Assist) | HITL | Real-time suggestions <500ms; accept/edit/reject; few-shot capture; coaching |
| **FR-11** | Analytics & Reporting | Analytics | Real-time dashboard: ARR, MTTR, CSAT, escalation rate, cost/ticket; drill-downs |
| **FR-12** | Admin & Configuration | Admin | Multi-tenant admin, RBAC, automation rules, KB management, action catalog, SLA config |

### Non-Functional Requirements (P0)

| ID | Requirement | Target | Exit Criteria |
|----|-------------|--------|---------------|
| **NFR-01** | End-to-end latency (autonomous) | <30s P50, <60s P95 | Load test with 1000 req/sec |
| **NFR-02** | Knowledge retrieval latency | <500ms P95 | Benchmark with 10M docs |
| **NFR-03** | System availability | 99.9% monthly | Multi-AZ deployment verified |
| **NFR-04** | Data encryption | AES-256 at rest, TLS 1.3 | Penetration test passed |
| **NFR-05** | Multi-tenancy | RLS + vector namespaces | Zero cross-tenant leakage in pen test |
| **NFR-06** | Observability | 100% trace coverage | LangSmith + OTel on all requests |

### Phase 2 Requirements (P1 - Months 4-6)

| ID | Requirement | Notes |
|----|-------------|-------|
| **FR-13** | Additional Channels | Slack, Teams, Discord, Social Media |
| **FR-14** | Advanced Categories | Technical bugs, API issues, integrations, complex billing |
| **FR-15** | Advanced Actions | Provisioning, config deployment, DB mutations |
| **FR-16** | Proactive Support | Predictive issue detection from telemetry |
| **FR-17** | Voice Support | Transcription + agent processing |
| **FR-18** | Multi-language | Spanish, French, German, Japanese |

## Exit Bar (Definition of Done for MVP)

### Code Quality
- [ ] All code passes type check (`mypy`/`pyright`), lint (`ruff`), format (`black`)
- [ ] Test coverage ≥80% on core services (orchestration, agents, actions, knowledge, memory)
- [ ] All tests run offline with `DEMO_MODE=true`, `LLM_PROVIDER=fake`, `VECTOR_STORE=memory`, `USE_FAKE_REDIS=true`
- [ ] No secrets, credentials, or PII in codebase

### Architecture Compliance
- [ ] Layering respected: API → Services → Repositories → Core (no reverse imports)
- [ ] All LLM calls through `call_structured`; all tools through `ToolRegistry`
- [ ] Ticket text wrapped with `wrap_untrusted` everywhere
- [ ] Policy decisions in `agents/rules.py` and `backend/app/tools/policy.py`
- [ ] Severity rules only raise, never lower

### Functional Verification
- [ ] `make demo` runs: `TICKET=CD-1002` pauses for approval, `TICKET=CD-1005` escalates by policy
- [ ] Agent Assist UI: suggestions <500ms, accept/edit/reject works, few-shot captured
- [ ] HITL approval queue: approve/reject only when `approval_status=pending`
- [ ] Viewer role receives 403 on run, reply, approve
- [ ] Autonomous resolution rate ≥70% on test dataset
- [ ] MTTR <5 min (auto), <2 hr (assisted) on test dataset

### Observability
- [ ] LangSmith traces on all agent workflows
- [ ] OTel metrics: RED + business KPIs in Grafana
- [ ] Structured JSON logs with correlation IDs, PII scrubbed
- [ ] Alerting: P0→PagerDuty 5min, P1→PagerDuty 15min, P2→Slack 1hr

### Security & Compliance
- [ ] Penetration test passed (OWASP top 10)
- [ ] GDPR: erasure API, DPA templates, EU data residency
- [ ] CCPA: disclosure API, opt-out, deletion workflows
- [ ] SOC 2: audit logging, access reviews, change management
- [ ] AES-256 at rest, TLS 1.3 in transit, field-level PII encryption

### Documentation
- [ ] API contracts in `docs/API_CONTRACT.md`
- [ ] Architecture diagrams in `docs/ARCHITECTURE.md`
- [ ] Git/GitHub workflow in `docs/Git_GitHub_Workflow_Guide.md`
- [ ] ADRs for all major decisions in `docs/adr/`

### Deployment
- [ ] Terraform modules for all 3 clouds (EKS/AKS/GKE, RDS/Azure DB/Cloud SQL, etc.)
- [ ] CI/CD pipelines: build → test → security scan → staging deploy
- [ ] Staging deployed with anonymized production data
- [ ] Runbooks for on-call, customer onboarding guide

---

*Set the TASKS.md row to `Completed ✅` only after that sub-task has merged.*