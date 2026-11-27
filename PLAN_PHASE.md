# PLAN_PHASE.md - Phase Exit Criteria, Files, Tests, Demo Gates

## Phase 0: Foundation (Weeks 1-4)

### Goal
Infrastructure provisioned, core data models defined, API contracts locked, ingestion pipeline operational.

### Exit Criteria
- [ ] Terraform modules for all 3 clouds apply cleanly to dev environment
- [ ] CI/CD pipelines run: build → test → security scan → staging deploy
- [ ] PostgreSQL 16 with pgvector, RLS policies applied and tested
- [ ] Redis 7 cluster operational with pub/sub
- [ ] Kafka (MSK/Event Hubs/PubSub) topics created with retention
- [ ] Vector DB (Weaviate/Qdrant/Pinecone) collection created with schema
- [ ] Object storage buckets with lifecycle policies
- [ ] OpenAPI 3.1 spec complete for all endpoints
- [ ] SQLAlchemy 2.0 async models generated from schema
- [ ] Alembic migrations for all tables (tenants, users, customers, tickets, messages, actions, cases)
- [ ] Ingestion service normalizes Email, Chat, Zendesk, Intercom, In-App to `SupportRequest`
- [ ] Deduplication logic for multi-channel submissions working

### Files to Create/Modify
```
infra/
  modules/
    kubernetes/
    postgresql/
    redis/
    vector-db/
    kafka/
    object-storage/
  environments/
    dev/
    staging/
    prod/
.github/workflows/
  ci.yml
  cd-staging.yml
  cd-prod.yml
backend/
  app/
    core/
      config.py
      security.py
      database.py
      redis.py
      kafka.py
    models/
      __init__.py
      tenant.py
      user.py
      customer.py
      ticket.py
      message.py
      action.py
      case.py
    schemas/
      __init__.py
      ingestion.py
      ticket.py
      action.py
    repositories/
      __init__.py
      base.py
      ticket.py
      customer.py
      action.py
    api/
      __init__.py
      v1/
        ingestion.py
        tickets.py
        health.py
services/
  ingestion-service/
    Dockerfile
    main.py
    adapters/
      email.py
      chat.py
      zendesk.py
      intercom.py
      in_app.py
```

### Tests Required
- [ ] Unit: Schema validation for all Pydantic models
- [ ] Unit: RLS policies enforce tenant isolation (attempt cross-tenant query → 0 rows)
- [ ] Unit: Ingestion normalization produces identical `SupportRequest` from all channels
- [ ] Unit: Deduplication merges same-customer multi-channel submissions
- [ ] Integration: Full ingestion → Kafka → consumer round-trip
- [ ] Load: 1000 req/sec ingestion with <500ms P95 latency
- [ ] Security: Pen test on ingestion endpoints (no auth bypass, no injection)

### Demo Gate
```bash
# Ingestion demo
curl -X POST localhost:8000/api/v1/tickets/ingest \
  -H "Authorization: Bearer <dev-token>" \
  -d '{"tenant_id": "...", "channel": "CHAT", "customer_email": "test@example.com", "subject": "Test", "body": "Help me"}'
# → Returns ticket_id, status="queued"
# Verify in Kafka topic: SupportRequest event with all fields
```

---

## Phase 1: Core Agents (Weeks 5-10)

### Week 5: Supervisor + Customer Agents

#### Exit Criteria
- [ ] LangGraph `StateGraph` compiles with `SupportState` schema
- [ ] Supervisor routes: customer_agent (default) → knowledge_agent
- [ ] Supervisor escalates: CRITICAL_P0 or ENTERPRISE+negative sentiment → escalation_agent
- [ ] Customer Agent: intent classification ≥95% accuracy on test set
- [ ] Customer Agent: entity extraction (email, account IDs, amounts, dates)
- [ ] Customer Agent: sentiment scoring -1.0 to +1.0
- [ ] Customer Agent: customer context lookup (profile, subscription, usage, history) <1s
- [ ] Redis cache for customer context with 15min TTL working

#### Files
```
services/
  orchestration-service/
    Dockerfile
    main.py
    graph/
      __init__.py
      state.py          # SupportState TypedDict
      supervisor.py     # SupervisorAgent node
      routing.py        # Conditional edge functions
  agents/
    customer/
      __init__.py
      agent.py          # CustomerAgent node
      tools.py          # customer_lookup, subscription_info, usage_metrics
      prompts.py
```

#### Tests
- [ ] Unit: Supervisor routing logic (all branches covered)
- [ ] Unit: Customer Agent classification on 1000 labeled examples
- [ ] Unit: Customer context cache hit/miss behavior
- [ ] Integration: Full customer_agent → supervisor flow with mock LLM

#### Demo Gate
```bash
# Classification demo
python -m agents.customer.demo --text "I need a refund for my $50 charge last week"
# → intent: "billing.refund", entities: {"amount": 50, "timeframe": "last week"}, severity: "HIGH_P1"
```

---

### Week 6: Knowledge/RAG Agent

#### Exit Criteria
- [ ] Hybrid search: vector (semantic) + BM25 (keyword) + graph (relationships)
- [ ] Reciprocal Rank Fusion (RRF, k=60) implemented
- [ ] Cross-encoder reranking (Cohere/BGE) on top-50 → top-10
- [ ] Citations: doc_id, title, chunk, score, source_url in every result
- [ ] Precision@5 ≥85% on evaluation dataset
- [ ] Query decomposition for multi-part questions
- [ ] Real-time index updates <5min latency (doc changes → vector DB)
- [ ] Tenant-scoped namespaces + shared global corpus

#### Files
```
services/
  knowledge-service/
    Dockerfile
    main.py
    retrieval/
      __init__.py
      vector_search.py      # Pinecone/Weaviate/Qdrant client
      bm25_search.py        # OpenSearch/PostgreSQL full-text
      graph_search.py       # Relationship queries
      rrf_fusion.py         # reciprocal_rank_fusion()
      reranker.py           # Cohere/BGE cross-encoder
      indexer.py            # Real-time indexing pipeline
    agents/
      knowledge/
        __init__.py
        agent.py            # KnowledgeAgent node
        tools.py            # vector_search, bm25_search, graph_query, rerank, fetch_doc
        prompts.py
```

#### Tests
- [ ] Unit: RRF fusion correctness (known inputs → expected ranked output)
- [ ] Unit: Reranker improves precision over raw vector search
- [ ] Unit: Query decomposition splits complex questions correctly
- [ ] Integration: Knowledge Agent returns cited results for 50 test queries
- [ ] Benchmark: Retrieval latency <500ms P95 with 10M docs

#### Demo Gate
```bash
# Knowledge search demo
python -m knowledge_service.demo --query "How do I reset my password?" --tenant_id "demo"
# → Top 5 results with citations, confidence scores
```

---

### Week 7: Troubleshooting Agent

#### Exit Criteria
- [ ] Diagnostic tools: API health checks, config validation, log queries, feature flag checks
- [ ] Structured troubleshooting flows (decision trees) for top 20 issue types
- [ ] Correlation with known issues/incidents database
- [ ] Hypothesis generation ranked by probability
- [ ] Requests additional info from customer when needed

#### Files
```
services/
  agents/
    troubleshooting/
      __init__.py
      agent.py              # TroubleshootingAgent node
      tools.py              # api_health_check, config_validate, log_query, feature_flag_check
      flows/                # Decision tree definitions (YAML)
      prompts.py
```

#### Tests
- [ ] Unit: Each diagnostic tool returns expected format
- [ ] Unit: Decision tree traversal for known scenarios
- [ ] Integration: Troubleshooting Agent produces hypotheses for 20 test cases

#### Demo Gate
```bash
# Troubleshooting demo
python -m agents.troubleshooting.demo --ticket_id "TICKET-123" --intent "technical.api_error"
# → Hypotheses ranked, diagnostic steps suggested
```

---

### Week 8: Resolution Agent

#### Exit Criteria
- [ ] Generates structured resolution plan: steps, expected outcomes, rollback
- [ ] Differentiates: Autonomous (AI executes) vs Assisted (Agent executes) vs Escalated
- [ ] Customer-facing response + internal agent notes
- [ ] Knowledge citations and confidence scores included
- [ ] Ticket summary for handoff/escalation

#### Files
```
services/
  agents/
    resolution/
      __init__.py
      agent.py              # ResolutionAgent node
      tools.py              # generate_response, validate_plan
      templates/            # Response templates by category
      prompts.py
```

#### Tests
- [ ] Unit: Plan validation catches missing rollback steps
- [ ] Unit: Confidence scoring calibration (high confidence → correct resolution)
- [ ] Integration: Full resolution for 50 test cases across categories

#### Demo Gate
```bash
# Resolution demo
python -m agents.resolution.demo --hypotheses "[...]" --context "{...}"
# → Plan with steps, response, confidence, autonomous/assisted/escalated decision
```

---

### Week 9: Escalation Agent

#### Exit Criteria
- [ ] Auto-escalation triggers: confidence<0.7, critical severity, enterprise tier, policy match
- [ ] Context package: customer 360°, conversation history, investigation steps, hypotheses, attempted actions, suggested next steps
- [ ] Routing to correct team/individual based on skills, load, timezone
- [ ] SLA timer starts, alerts at 50%/80%/100%
- [ ] Warm handoff: AI stays in loop for context

#### Files
```
services/
  agents/
    escalation/
      __init__.py
      agent.py              # EscalationAgent node
      tools.py              # route_to_team, notify_agent, create_ticket, set_sla
      router.py             # Skills/load/timezone matching
      prompts.py
```

#### Tests
- [ ] Unit: Escalation triggers fire correctly on threshold boundaries
- [ ] Unit: Routing logic matches engineer skills to issue category
- [ ] Integration: Full escalation package generated for 20 test cases

#### Demo Gate
```bash
# Escalation demo
python -m agents.escalation.demo --ticket_id "TICKET-456" --reason "confidence_low"
# → Escalation package, routing decision, SLA timer started
```

---

### Week 10: Integration & E2E Testing

#### Exit Criteria
- [ ] Full LangGraph workflow: ingestion → supervisor → all agents → resolution/escalation
- [ ] End-to-end latency <30s P50, <60s P95 for autonomous resolution
- [ ] Load test: 1000 concurrent sessions, 1000 req/sec
- [ ] Chaos testing: agent failures, Kafka latency, DB failures → graceful degradation
- [ ] All agent-to-agent handoffs preserve context

#### Files
```
services/
  orchestration-service/
    graph/
      workflow.py           # Compiled StateGraph
      checkpoints.py        # Redis checkpointing
tests/
  integration/
    test_full_workflow.py
    test_load.py
    test_chaos.py
```

#### Tests
- [ ] E2E: 100 tickets from ingestion to resolution/escalation
- [ ] Load: Sustained 1000 req/sec for 10 minutes
- [ ] Chaos: Kill agent pods mid-workflow → recovery verified

#### Demo Gate
```bash
# Full workflow demo
make demo TICKET=CD-1002  # Must pause for approval
make demo TICKET=CD-1005  # Must escalate by policy
```

---

## Phase 2: Action & Memory (Weeks 11-14)

### Week 11: Action Framework + Approval UI

#### Exit Criteria
- [ ] MCP tool registry with 15+ tools (read/write)
- [ ] Risk levels: LOW/MEDIUM/HIGH/CRITICAL with approval gating
- [ ] Approval UI: pending queue, context, risk assessment, rollback plan
- [ ] Action execution with verification and compensation/rollback
- [ ] Immutable audit log (who, what, when, result)

#### Files
```
services/
  action-executor/
    Dockerfile
    main.py
    mcp/
      __init__.py
      registry.py           # ToolRegistry
      tools/                # 15+ tool implementations
    approval/
      __init__.py
      service.py            # Approval workflow
      api.py                # /approvals/pending, /actions/{id}/approve
    audit/
      __init__.py
      logger.py             # Immutable audit logging
frontend/
  src/app/
    approvals/
      page.tsx              # Approval queue UI
    tickets/[ticketId]/
      ActionApprovalCard.tsx
```

#### Tests
- [ ] Unit: Each MCP tool executes correctly (mocked external APIs)
- [ ] Unit: Approval gating: HIGH/CRITICAL always require approval
- [ ] Unit: Rollback executes on failure
- [ ] Integration: Full action → approval → execution → audit flow

#### Demo Gate
```bash
# Action execution demo
python -m action_executor.demo --tool "billing.refund" --params '{"amount": 75, "ticket_id": "..."}'
# → Requires approval (amount > $50)
# Approve via UI → executes → audit log entry
```

---

### Week 12: Memory System

#### Exit Criteria
- [ ] Short-term: Redis `session:{ticket_id}:state` with 2hr TTL
- [ ] Episodic: PostgreSQL `resolved_cases` with pgvector embeddings
- [ ] Semantic: Customer preferences, usage patterns in `customers.metadata`
- [ ] Similarity search: `recall_similar_cases()` returns relevant historical resolutions
- [ ] Pattern extraction: Auto-detect ≥5 similar resolutions in 30 days → draft KB article

#### Files
```
services/
  memory-service/
    Dockerfile
    main.py
    working/
      __init__.py
      redis_state.py        # session:{ticket_id}:state
    episodic/
      __init__.py
      case_store.py         # resolved_cases CRUD + vector search
    semantic/
      __init__.py
      customer_memory.py    # customers.metadata management
    patterns/
      __init__.py
      extractor.py          # Pattern detection → KB drafts
```

#### Tests
- [ ] Unit: Redis state checkpoint/restore
- [ ] Unit: pgvector similarity search accuracy
- [ ] Unit: Pattern detector finds ≥5 similar cases
- [ ] Integration: Memory persists across agent restarts

#### Demo Gate
```bash
# Memory demo
python -m memory_service.demo --ticket_id "TICKET-789" --action "recall_similar"
# → Shows 3 similar historical cases with resolution steps
```

---

### Week 13: Agent Assist UI

#### Exit Criteria
- [ ] Real-time WebSocket: `/api/v1/ws/tickets/{ticket_id}`
- [ ] ConversationThread component with message history
- [ ] AISuggestionPanel: response, actions, knowledge links, similar cases
- [ ] One-click accept/edit/reject for AI suggestions
- [ ] Few-shot capture from agent corrections
- [ ] Real-time coaching: "Customer seems frustrated — consider empathy"

#### Files
```
frontend/
  src/
    components/
      agent-assist/
        ConversationThread.tsx
        AISuggestionPanel.tsx
        KnowledgeCitations.tsx
        ActionApprovalCard.tsx
    hooks/
      useTicketStream.ts    # WebSocket hook
    app/
      tickets/
        [ticketId]/
          page.tsx          # Agent Assist page
```

#### Tests
- [ ] Unit: WebSocket reconnection logic
- [ ] Unit: Suggestion panel renders <500ms after message
- [ ] E2E: Agent accepts suggestion → sends to customer
- [ ] E2E: Agent edits suggestion → few-shot captured

#### Demo Gate
```bash
# Agent Assist demo
npm run dev
# Open /dashboard/tickets/TICKET-123
# Customer sends message → AI suggestion appears in <500ms
# Agent clicks accept → response sent
```

---

### Week 14: Analytics Dashboard

#### Exit Criteria
- [ ] Real-time dashboard: Volume, ARR, MTTR, CSAT, Escalation rate, Cost/ticket
- [ ] Drill-down by: Channel, Category, Agent, Customer segment, Time
- [ ] Cost savings calculator: Agent hours saved, Cost per ticket
- [ ] Quality audit: Sample review workflow for AI responses
- [ ] Export: CSV, API, scheduled reports

#### Files
```
services/
  admin-service/
    Dockerfile
    main.py
    analytics/
      __init__.py
      metrics.py            # Business KPI calculations
      api.py                # /analytics/overview, /tickets, /agents
frontend/
  src/
    app/
      dashboard/
        page.tsx            # Overview KPIs
        tickets/page.tsx    # Ticket queue (Grid.js)
        approvals/page.tsx  # HITL queue
```

#### Tests
- [ ] Unit: Metric calculations match SQL definitions
- [ ] Unit: Drill-down filters work correctly
- [ ] Integration: Dashboard updates in real-time from Kafka events

#### Demo Gate
```bash
# Analytics demo
npm run dev
# Open /dashboard → shows real-time KPIs
# Filter by channel/category → updates instantly
```

---

## Phase 3: Hardening & Launch (Weeks 15-16)

### Week 15: Security Audit & Penetration Testing

#### Exit Criteria
- [ ] Third-party penetration test passed (OWASP Top 10)
- [ ] Automated scanning: SAST, DAST, SCA in CI
- [ ] All critical/high findings remediated
- [ ] Compliance evidence: GDPR, CCPA, SOC 2, HIPAA (optional)
- [ ] Secrets management: Vault rotation, no secrets in code/images

### Week 16: Production Launch & Monitoring

#### Exit Criteria
- [ ] Staging deployed with anonymized production data
- [ ] Runbooks for on-call (incident response, rollback, scaling)
- [ ] Customer onboarding guide
- [ ] Monitoring: Grafana dashboards, PagerDuty alerts, log aggregation
- [ ] Cost tracking: Token usage, compute, storage, cost per resolution

---

## Phase 4: Enhancement (Months 4-6)

- Multi-language (ES, FR, DE, JA)
- Voice support (transcription + agent processing)
- Proactive support (predictive from telemetry)
- Advanced actions (provisioning, config deployment, DB mutations)
- Additional channels (Slack, Teams, Discord, Social)
- Multi-cloud optimization (cost, latency, data residency)

---

*Phase exit criteria must be met before advancing. Demo gates must pass for each week.*