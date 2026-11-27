# CLAUDE.md - Autonomous Customer Support & Resolution Platform

This file provides comprehensive guidance for AI assistants working on this codebase. It captures architectural decisions, technology choices, and development conventions from the PRD/BRD, HLD, and LLD documents.

---

## Project Overview

**Platform Name:** Autonomous Customer Support & Resolution Platform (ACS-RP)  
**Core Mission:** Build an AI-native system that understands, investigates, retrieves, decides, acts, escalates, and remembers — going beyond answer generation to end-to-end autonomous resolution.

**Key Differentiators:**
- Multi-agent orchestration (Supervisor, Customer, Knowledge/RAG, Troubleshooting, Resolution, Escalation)
- Advanced RAG: Hybrid retrieval (vector + BM25 + graph), reranking, agentic query decomposition
- Action execution via MCP (not just answers — refunds, config changes, account updates)
- Persistent memory: Customer context, interaction history, resolution patterns
- Continuous learning: Feedback loops from resolved cases

---

## Architecture Summary

### High-Level Architecture (from HLD)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│ API Gateway │────▶│ Ingestion   │
│  (Web/Chat) │     │ (Kong/Envoy)│     │  Service    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                                                ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Memory    │◀────│Orchestration│◀────│  Knowledge  │
│   Service   │     │  Service    │     │   Agent     │
└─────────────┘     │(LangGraph)  │     └─────────────┘
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │ Customer    │  │ Troubleshoot│  │ Resolution  │
   │ Agent       │  │ Agent       │  │ Agent       │
   └─────────────┘  └─────────────┘  └─────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                    ┌─────────────┐
                    │ Escalation  │
                    │ Agent       │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Action    │
                    │  Executor   │
                    │  (MCP)      │
                    └─────────────┘
```

### Agent Responsibilities (from LLD)

| Agent | Responsibility | Key Tools |
|-------|---------------|-----------|
| **Supervisor** | Orchestrate workflow, route to specialists, manage state, trigger HITL | None (pure orchestration) |
| **Customer** | Intent classification, entity extraction, sentiment, customer context | `customer_lookup`, `subscription_info`, `usage_metrics` |
| **Knowledge** | Hybrid search (vector + BM25 + graph), reranking, synthesis with citations | `vector_search`, `bm25_search`, `graph_query`, `rerank`, `fetch_doc` |
| **Troubleshooting** | Diagnostics, hypothesis generation, correlation with known issues | `api_health_check`, `config_validate`, `log_query`, `feature_flag_check` |
| **Resolution** | Plan generation, response drafting, confidence scoring | `generate_response`, `validate_plan` |
| **Escalation** | Context packaging, team routing, SLA tracking | `route_to_team`, `notify_agent`, `create_ticket`, `set_sla` |

---

## Technology Stack (from HLD & LLD)

### Core Stack

| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| **Frontend** | Next.js 14 (App Router) | 14.x | SSR, React 18 |
| **UI Components** | shadcn/ui + Tailwind CSS | Latest | Accessible, customizable |
| **State Management** | Zustand + TanStack Query | Latest | Server-state focus |
| **Backend API** | FastAPI | 0.110+ | Async, type-safe, auto-docs |
| **Agent Framework** | LangGraph | 0.2+ | Stateful multi-agent, HITL native |
| **LLM Gateway** | LiteLLM / Custom | Latest | Multi-provider routing, caching |
| **Primary LLM** | Claude 3.5 Sonnet / GPT-4o | Latest | Quality reasoning + generation |
| **Fast LLM** | Claude 3 Haiku / GPT-4o mini | Latest | Classification, extraction |
| **Embeddings** | text-embedding-3-large / Cohere | Latest | 1536 dim |
| **Reranker** | Cohere Rerank / BGE | Latest | Cross-encoder |
| **Database** | PostgreSQL | 16 | ACID, JSONB, RLS, pgvector |
| **Cache** | Redis | 7 | Sessions, rate limits, pub/sub |
| **Vector DB** | Weaviate / Qdrant / Pinecone | Latest | Hybrid search, filtering |
| **Event Bus** | Kafka | 3.6+ | MSK / Event Hubs / PubSub |
| **Object Storage** | S3 / Blob / GCS | - | Documents, artifacts |
| **Search** | OpenSearch | 2.x | Full-text, analytics |
| **Orchestration** | Kubernetes | 1.29+ | EKS / AKS / GKE |
| **Service Mesh** | Istio | 1.20+ | mTLS, traffic, observability |
| **API Gateway** | Kong / Envoy Gateway | Latest | Routing, plugins, auth |
| **Auth** | Keycloak / Custom OIDC | Latest | RBAC, MFA |
| **IaC** | Terraform | 1.7+ | Multi-cloud modules |
| **CI/CD** | GitHub Actions / GitLab CI | - | Build, test, deploy |
| **Observability** | OTel + Grafana + Loki + Tempo | Latest | Open standard |
| **Agent Tracing** | LangSmith | Latest | Agent-specific debugging |
| **Secrets** | HashiCorp Vault | 1.15+ | Dynamic secrets, rotation |

### Multi-Cloud Abstraction

| Component | AWS | Azure | GCP |
|-----------|-----|-------|-----|
| Kubernetes | EKS | AKS | GKE |
| PostgreSQL | RDS | Azure DB | Cloud SQL |
| Redis | ElastiCache | Azure Cache | Memorystore |
| Vector DB | Pinecone/OpenSearch | Azure AI Search | Vertex AI Vector Search |
| Event Bus | MSK | Event Hubs (Kafka) | Pub/Sub |
| Object Storage | S3 | Blob Storage | Cloud Storage |
| Secrets | Secrets Manager | Key Vault | Secret Manager |

---

## Database Schema (from LLD)

### Core Tables

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Key tables: tenants, users, customers, tickets, ticket_messages, 
-- action_audits, resolved_cases (with pgvector embeddings)

-- Row-Level Security: ALL tables use tenant_id RLS policies
-- CREATE POLICY tenant_isolation_policy ON <table> 
-- USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### Redis Key Patterns

| Pattern | Type | TTL | Purpose |
|---------|------|-----|---------|
| `session:{ticket_id}:state` | Hash/JSON | 2hr | Active LangGraph state |
| `customer:{tenant_id}:{customer_id}:context` | String | 15min | Cached 360° view |
| `ratelimit:{tenant_id}:{ip_or_user}` | Counter | 1min | Token bucket |
| `agent:lock:{ticket_id}` | String | 30s | Distributed lock |
| `pubsub:ticket:{ticket_id}:events` | Channel | N/A | Real-time SSE/WS |

### Vector DB Schema (Pinecone/Weaviate/Qdrant)

```json
{
  "collection": "knowledge_documents",
  "dimension": 1536,
  "metric": "cosine",
  "properties": {
    "doc_id": "string (indexed)",
    "tenant_id": "string (indexed)",
    "title": "string (indexed)",
    "chunk_content": "string",
    "source_url": "string",
    "category": "string (indexed)",
    "access_level": "string (indexed)",
    "updated_at": "int (indexed)"
  }
}
```

---

## LangGraph Implementation (from LLD)

### State Schema (`SupportState`)

```python
from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator

class SupportState(TypedDict):
    ticket_id: str
    tenant_id: str
    messages: Annotated[List[TicketMessageDict], operator.add]
    customer: CustomerProfile
    intent: str
    category: str
    severity: str  # "LOW_P3", "MEDIUM_P2", "HIGH_P1", "CRITICAL_P0"
    sentiment_score: float
    retrieved_docs: List[RetrievedDoc]
    diagnostic_hypotheses: List[str]
    proposed_actions: List[PlannedAction]
    draft_response: str
    confidence_score: float
    is_escalated: bool
    escalation_reason: Optional[str]
    next_node: str
```

### Workflow Graph Structure

```python
# Entry: customer_agent
# Routes:
#   customer_agent → knowledge_agent (default)
#   customer_agent → escalation_agent (CRITICAL_P0 or ENTERPRISE + negative sentiment)
#   knowledge_agent → troubleshooting_agent (low confidence/no results)
#   knowledge_agent → resolution_agent (default)
#   troubleshooting_agent → resolution_agent
#   resolution_agent → human_approval_node (high-risk actions)
#   resolution_agent → escalation_agent (confidence < 0.65)
#   resolution_agent → END (autonomous resolution)
```

---

## Advanced RAG Pipeline (from LLD)

### Hybrid Retrieval Flow

```
Query → Query Decomposition → Parallel Search (Dense + Sparse) 
        → Reciprocal Rank Fusion (RRF, k=60)
        → Cross-Encoder Rerank (Cohere/BGE)
        → Top-K with citations
```

### Key Implementation (from LLD)

```python
def reciprocal_rank_fusion(vector_results, bm25_results, k=60):
    scores = {}
    doc_map = {}
    for rank, doc in enumerate(vector_results):
        scores[doc["doc_id"]] = scores.get(doc["doc_id"], 0) + 1.0/(k+rank+1)
        doc_map[doc["doc_id"]] = doc
    for rank, doc in enumerate(bm25_results):
        scores[doc["doc_id"]] = scores.get(doc["doc_id"], 0) + 1.0/(k+rank+1)
        doc_map[doc["doc_id"]] = doc
    return [doc_map[doc_id] | {"rrf_score": score} 
            for doc_id, score in sorted(scores.items(), key=lambda x: -x[1])]
```

---

## MCP Tool System (from LLD)

### Tool Definition Pattern

```python
class MCPRefundTool:
    name = "issue_customer_refund"
    description = "Issues a partial or full financial refund to a customer account."
    parameters_schema = RefundParameters.schema()
    risk_level = "HIGH"  # Requires approval if amount > $50
    
    async def execute(self, params: RefundParameters, approved_by: Optional[str] = None):
        if params.amount > 50.00 and not approved_by:
            return {"status": "REQUIRES_APPROVAL", ...}
        # Execute via Stripe/Billing API
        return {"status": "SUCCESS", "transaction_id": "...", "amount": params.amount}
```

### Approved Action Catalog (Risk-Level Gated)

| Tool | Category | Risk | Auto-Execute Threshold |
|------|----------|------|------------------------|
| `customer.lookup` | Read | LOW | Always |
| `subscription.get` | Read | LOW | Always |
| `subscription.change` | Write | MEDIUM | Tier change requires approval |
| `billing.refund` | Write | HIGH | **Always requires approval** |
| `account.password_reset` | Write | MEDIUM | With verification |
| `feature_flag.toggle` | Write | HIGH | Always requires approval |
| `config.update` | Write | HIGH | Always requires approval |

---

## Memory Architecture (from LLD)

### Three-Layer Memory

1. **Short-Term (Working Memory)** — Redis `session:{ticket_id}:state` — Active dialogue state, 2hr TTL
2. **Episodic (Case Memory)** — PostgreSQL `resolved_cases` with pgvector embeddings — Similarity search for historical resolutions
3. **Semantic (Customer Memory)** — PostgreSQL `customers.metadata` — Preferences, product usage, interaction patterns

```python
async def recall_similar_cases(tenant_id: str, issue_embedding: List[float], limit: int = 3):
    # pgvector cosine similarity search
    query = """
        SELECT case_id, issue_summary, root_cause, resolution_steps,
               1 - (embedding <=> :vector::vector) as similarity
        FROM resolved_cases
        WHERE tenant_id = :tenant_id
        ORDER BY embedding <=> :vector::vector ASC
        LIMIT :limit;
    """
```

---

## Frontend Architecture (from LLD)

### Next.js 14 Structure

```
src/
├── app/
│   ├── (auth)/login/page.tsx
│   ├── dashboard/
│   │   ├── page.tsx                    # Overview KPIs
│   │   ├── tickets/page.tsx            # Ticket queue (Grid.js)
│   │   ├── tickets/[ticketId]/page.tsx # Agent Assist (real-time)
│   │   └── approvals/page.tsx          # HITL approval queue
├── components/
│   ├── agent-assist/
│   │   ├── ConversationThread.tsx
│   │   ├── AISuggestionPanel.tsx
│   │   ├── KnowledgeCitations.tsx
│   │   └── ActionApprovalCard.tsx
│   └── ui/ (shadcn components)
```

### Real-Time WebSocket Hook

```typescript
export function useTicketStream(ticketId: string) {
  const [messages, setMessages] = useState<any[]>([]);
  const [agentState, setAgentState] = useState<any>(null);

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/api/v1/ws/tickets/${ticketId}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'NEW_MESSAGE') setMessages(prev => [...prev, data.payload]);
      else if (data.type === 'STATE_UPDATE') setAgentState(data.payload);
    };
    return () => ws.close();
  }, [ticketId]);
  return { messages, agentState };
}
```

---

## Guardrails & Security (from LLD)

### Guardrail Pipeline

```
Input → PII Scrubbing → Prompt Injection Detection → Agent Execution 
       → Hallucination/Fact Check → Output
```

### Implementation

```python
class SafetyGuardrail:
    PII_REGEX = {
        "email": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
        "credit_card": r'\b(?:\d[ -]*?){13,16}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b'
    }
    
    @classmethod
    def sanitize_input(cls, text: str) -> str:
        for pii_type, pattern in cls.PII_REGEX.items():
            text = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", text)
        return text
    
    @classmethod
    def detect_prompt_injection(cls, text: str) -> bool:
        keywords = ["ignore previous instructions", "system prompt", 
                    "you are now DAN", "disregard safety rules"]
        return any(kw in text.lower() for kw in keywords)
```

### Compliance Requirements

- **GDPR**: Data residency (EU region), right to erasure API, DPA templates
- **CCPA**: Data disclosure API, opt-out of sale, deletion workflows
- **SOC 2**: Audit logging, access reviews, change management
- **HIPAA**: Optional module (BAA, encryption, access controls)

---

## Observability & Evaluation (from HLD & LLD)

### Observability Stack

| Signal | Collection | Storage | Visualization |
|--------|------------|---------|---------------|
| Traces | OTel SDK + LangSmith | LangSmith + Tempo/Jaeger | LangSmith UI, Grafana |
| Metrics | Prometheus + OTel | Prometheus + Thanos/Mimir | Grafana |
| Logs | Structured JSON (stdout) | Loki / CloudWatch / Azure Monitor | Grafana, Kibana |
| Business KPIs | Custom OTel metrics | Prometheus | Grafana dashboards |
| Agent Quality | LangSmith evaluations | LangSmith | LangSmith dashboard |

### Key Dashboards

1. **Operations Overview** — Uptime, latency P50/P95/P99, error rate, saturation
2. **Business KPIs** — ARR, MTTR, CSAT, escalation rate, cost/ticket
3. **Agent Quality** — Retrieval precision, classification accuracy, hallucination rate
4. **Tenant Health** — Per-tenant volume, resolution rate, SLA compliance
5. **Security** — Failed auth, rate limit hits, WAF blocks
6. **Cost** — Token usage, compute, storage, cost per resolution

### LangSmith Tracing

```python
from langsmith import trace

@trace(name="KnowledgeAgent_Execution", run_type="chain")
async def trace_knowledge_agent(query: str, tenant_id: str):
    results = await run_hybrid_search(query, tenant_id)
    return results
```

---

## Development Conventions

### Project Structure (Target)

```
acsrp/
├── .github/workflows/       # CI/CD pipelines
├── docker/
│   ├── Dockerfile.api       # FastAPI service
│   ├── Dockerfile.agent     # Agent workers
│   └── docker-compose.yml   # Local dev
├── infra/                   # Terraform modules
│   ├── modules/
│   │   ├── kubernetes/
│   │   ├── postgresql/
│   │   ├── redis/
│   │   ├── vector-db/
│   │   └── kafka/
│   ├── environments/
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   └── main.tf
├── services/
│   ├── api-gateway/         # Kong/Envoy config
│   ├── auth-service/        # FastAPI + OIDC
│   ├── ingestion-service/   # Channel adapters
│   ├── orchestration-service/ # LangGraph workflows
│   ├── agents/
│   │   ├── customer/
│   │   ├── knowledge/
│   │   ├── troubleshooting/
│   │   ├── resolution/
│   │   └── escalation/
│   ├── action-executor/     # MCP tools + approval
│   ├── knowledge-service/   # RAG pipeline
│   ├── memory-service/      # Memory layers
│   ├── admin-service/       # Config, RBAC, analytics
│   └── notification-service/# Email, Slack, webhooks
├── frontend/                # Next.js 14 app
│   ├── src/app/
│   ├── src/components/
│   └── src/lib/
├── shared/
│   ├── schemas/             # Pydantic models (shared)
│   ├── database/            # SQLAlchemy models, migrations
│   └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── evaluation/          # LangSmith eval datasets
└── docs/
    ├── PRD_BRD.md
    ├── HLD.md
    ├── LLD.md
    └── ADRs/
```

### Code Style & Patterns

- **Python**: FastAPI + Pydantic v2, type hints mandatory, async/await throughout
- **Database**: SQLAlchemy 2.0 async, Alembic migrations, pgvector for embeddings
- **Testing**: pytest + pytest-asyncio, Testcontainers for integration tests
- **Agents**: LangGraph StateGraph, structured outputs via Pydantic
- **API**: OpenAPI 3.1 auto-generated, versioned `/api/v1/`
- **Frontend**: TypeScript strict mode, React 18 + Next.js 14 App Router
- **Secrets**: Never in code — Vault + External Secrets Operator

---

## Key API Endpoints (from LLD)

### Ingestion
```
POST   /api/v1/tickets/ingest              # Multi-channel ingestion
GET    /api/v1/tickets/{ticket_id}         # Ticket details
GET    /api/v1/tickets/{ticket_id}/messages # Conversation history
```

### Agent Assist (Real-time)
```
WS     /api/v1/ws/tickets/{ticket_id}      # Real-time agent state stream
POST   /api/v1/tickets/{ticket_id}/agent-action  # Agent accepts/edits AI suggestion
```

### Human-in-the-Loop
```
GET    /api/v1/approvals/pending           # Pending approvals queue
POST   /api/v1/actions/{action_id}/approve # Approve/reject action
```

### Knowledge Management
```
POST   /api/v1/knowledge/search            # Hybrid search
POST   /api/v1/knowledge/index             # Trigger reindex
GET    /api/v1/knowledge/documents         # List documents
```

### Analytics
```
GET    /api/v1/analytics/overview          # Dashboard KPIs
GET    /api/v1/analytics/tickets           # Ticket metrics (filterable)
GET    /api/v1/analytics/agents            # Agent performance
```

---

## Deployment & Environments

### Environment Topology

| Environment | Purpose | Infrastructure |
|-------------|---------|----------------|
| **Local Dev** | Developer loop | Docker Compose (all services) |
| **Staging** | E2E, load, security | Cloud (same as prod, smaller) |
| **Production** | Live traffic | Multi-AZ K8s (EKS/AKS/GKE) |

### Kubernetes Namespaces

```yaml
namespaces:
  - platform-system    # Istio, cert-manager, monitoring
  - auth               # Auth service, OIDC proxy
  - ingestion          # Channel adapters
  - orchestration      # LangGraph workflows
  - agents             # Agent workers (per-agent deployments)
  - actions            # Action executor, approval service
  - knowledge          # RAG service, indexer
  - memory             # Memory service
  - admin              # Admin API, dashboard BFF
  - data               # PostgreSQL, Redis, Vector DB operators
  - observability      # OTel, Prometheus, Grafana, Loki
```

---

## ADRs (Architecture Decision Records)

| ADR | Decision | Status |
|-----|----------|--------|
| ADR-001 | LangGraph for agent orchestration | ✅ Accepted |
| ADR-002 | Event-driven architecture (Kafka) | ✅ Accepted |
| ADR-003 | PostgreSQL as primary store (RLS, pgvector) | ✅ Accepted |
| ADR-004 | Multi-cloud from day one (Terraform, K8s) | ✅ Accepted |
| ADR-005 | Hybrid retrieval (Vector + BM25 + Graph + RRF) | ✅ Accepted |
| ADR-006 | HITL for all write actions above risk threshold | ✅ Accepted |

---

## Success Metrics (from PRD)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Autonomous Resolution Rate | ≥ 70% | Daily, per category |
| MTTR (autonomous) | < 5 min | Real-time |
| MTTR (assisted) | < 2 hr | Real-time |
| CSAT | ≥ 4.5 / 5.0 | Per interaction |
| First Contact Resolution | ≥ 85% | Daily |
| Escalation Rate | < 30% | Daily |
| Cost per Ticket | < $2 (auto), < $15 (assisted) | Monthly |
| System Uptime | 99.9% | Monthly |
| Retrieval Precision@5 | ≥ 85% | Continuous |
| Classification Accuracy | ≥ 95% | Continuous |
| Action Success Rate | ≥ 99.5% | Continuous |

---

## Risk Register (from PRD)

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Hallucination in autonomous responses | High | Critical | RAG + citations, confidence thresholds, HITL, guardrails |
| Data leakage across tenants | Medium | Critical | RLS, vector namespaces, penetration testing |
| Action execution failures | Medium | High | Idempotent APIs, compensation transactions, rollback |
| Model drift / quality degradation | High | High | Continuous evaluation, A/B testing, regression detection |
| Integration API changes | Medium | Medium | Adapter pattern, versioned integrations, monitoring |
| Agent resistance to AI adoption | Medium | High | Involve agents in design, gradual rollout |
| Cost overrun (LLM tokens, vector DB) | Medium | High | Token budgets, caching, model routing |
| Regulatory compliance gaps | Low | Critical | Privacy by design, DPIA, legal review each phase |

---

## Commands & Workflows

### Local Development

```bash
# Start all services locally
docker-compose -f docker/docker-compose.yml up -d

# Run database migrations
alembic upgrade head

# Run tests
pytest tests/ -v --asyncio-mode=auto

# Run evaluation suite
python -m evaluation.run_evals
```

### Deployment

```bash
# Deploy to staging
cd infra/environments/staging && terraform apply

# Deploy to production (requires approval)
cd infra/environments/prod && terraform apply
```

---

## Important Notes for AI Assistants

1. **Always use the shared Pydantic schemas** from `shared/schemas/` — never redefine models
2. **Multi-tenancy is mandatory** — every query must include tenant_id context
3. **RLS is enforced at DB level** — set `app.current_tenant_id` session variable
4. **HITL is required** for all write actions with risk_level ≥ MEDIUM
5. **Observability is first-class** — add traces, metrics, logs for every new feature
6. **Guardrails run on every request** — PII scrubbing + prompt injection detection
7. **Use LangSmith tracing** for all agent workflows — `@trace` decorator
8. **Event-driven by default** — async communication via Kafka topics
9. **Cloud-agnostic code** — no cloud-specific SDKs in business logic
10. **Test with realistic data** — use anonymized production samples in staging

---

## References

- **PRD/BRD**: `docs/PRD_BRD.md` — Business requirements, user stories, success metrics
- **HLD**: `docs/HLD.md` — Architecture, components, deployment, security
- **LLD**: `docs/LLD.md` — Database schemas, API specs, LangGraph code, RAG pipeline, MCP tools
- **ADRs**: `docs/ADRs/` — Architecture decision records

---

*This CLAUDE.md is generated from the project's PRD/BRD, HLD, and LLD documents. Update it when architecture decisions change.*