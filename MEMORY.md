# MEMORY.md - Locked Decisions and Honest Status

## Locked Decisions

| Decision | Date | Status | Details |
|----------|------|--------|---------|
| **Architecture** | 2026-11-26 | ✅ Locked | Event-driven, multi-agent, cloud-native with LangGraph orchestration |
| **Agent Framework** | 2026-11-26 | ✅ Locked | LangGraph 0.2+ for stateful multi-agent with HITL |
| **Primary Database** | 2026-11-26 | ✅ Locked | PostgreSQL 16 with pgvector, RLS for multi-tenancy |
| **Vector Database** | 2026-11-26 | ✅ Locked | Weaviate/Qdrant/Pinecone (cloud-agnostic abstraction) |
| **Event Bus** | 2026-11-26 | ✅ Locked | Kafka (MSK/Event Hubs/PubSub) |
| **Frontend Framework** | 2026-11-26 | ✅ Locked | Next.js 14 App Router, shadcn/ui, Tailwind CSS |
| **Backend Framework** | 2026-11-26 | ✅ Locked | FastAPI 0.110+, Pydantic v2, SQLAlchemy 2.0 async |
| **Multi-Cloud Strategy** | 2026-11-26 | ✅ Locked | Terraform + Kubernetes (EKS/AKS/GKE) from day one |
| **LLM Providers** | 2026-11-26 | ✅ Locked | Primary: Claude 3.5 Sonnet/GPT-4o; Fast: Claude 3 Haiku/GPT-4o mini |
| **Embedding Model** | 2026-11-26 | ✅ Locked | text-embedding-3-large / Cohere (1536 dim) |
| **Reranker** | 2026-11-26 | ✅ Locked | Cohere Rerank / BGE cross-encoder |
| **Auth** | 2026-11-26 | ✅ Locked | OIDC/SAML via Keycloak, RBAC + ABAC |
| **Observability** | 2026-11-26 | ✅ Locked | OTel + Grafana + Loki + Tempo + LangSmith |

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| **PRD/BRD** | ✅ Complete | 600 lines, 14 sections |
| **HLD** | ✅ Complete | 935 lines, 15 sections + diagrams |
| **LLD** | ✅ Complete | 625 lines, 10 sections + code |
| **CLAUDE.md** | ✅ Complete | 652 lines, comprehensive guidance |
| **Core Agents** | ✅ Complete | 8 agents (Explore, planner, implementer, code-reviewer, opus-consultant, log-triage, architect, test-engineer) |
| **Core Skills** | ✅ Complete | 10 skills (plan, implement, review, consult-opus, cost-report, wait, test, fix-issue, pr-review, clouddesk-support) |
| **Rules** | ✅ Complete | 3 rules (cost-and-delegation, backend, tests) |
| **Hooks** | ✅ Complete | pre-commit.sh with fail-open behavior |
| **Settings** | ✅ Complete | Model pins, subagent defaults, spawn depth, hooks |
| **Git Ignore** | ✅ Complete | Protects .claude internals |

## Active Phase

**Phase 0: Foundation (Weeks 1-4)** - Infrastructure provisioning, core data models, API contracts, ingestion pipeline

## Next Milestone

**Week 4**: Ingestion pipeline + normalization (Email/Chat/Ticket adapters, `SupportRequest` schema)

## Known Risks (from PRD)

1. **Hallucination in autonomous responses** - High likelihood, Critical impact
2. **Data leakage across tenants** - Medium likelihood, Critical impact
3. **Action execution failures** - Medium likelihood, High impact
4. **Model drift / quality degradation** - High likelihood, High impact
5. **Cost overrun (LLM tokens, vector DB)** - Medium likelihood, High impact

## Cloud Credentials Status

| Provider | Status | Notes |
|----------|--------|-------|
| AWS | ⏳ Pending | Need account, IAM roles, MSK, RDS, ElastiCache |
| Azure | ⏳ Pending | Need subscription, AKS, Event Hubs, Cosmos DB |
| GCP | ⏳ Pending | Need project, GKE, Pub/Sub, Cloud SQL |

## Deploy State

| Environment | Status | Last Updated |
|-------------|--------|--------------|
| Local Dev | ⏳ Not started | - |
| Staging | ⏳ Not started | - |
| Production | ⏳ Not started | - |

---

*Update this file when implementation, local validation, cloud credentials, or deploy state changes.*