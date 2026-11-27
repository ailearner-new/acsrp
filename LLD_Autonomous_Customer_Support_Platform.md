# Low-Level Design (LLD)

## Autonomous Customer Support & Resolution Platform

**Version:** 1.0  
**Date:** 2026-11-27  
**Status:** Draft  
**Document Owner:** Engineering & Architecture Team  
**Classification:** Internal - Confidential

---

## Table of Contents

1. [Database Schema & Data Models](#1-database-schema--data-models)
2. [API Specifications & Pydantic Schemas](#2-api-specifications--pydantic-schemas)
3. [LangGraph Multi-Agent Architecture](#3-langgraph-multi-agent-architecture)
4. [Advanced RAG & Retrieval Engine](#4-advanced-rag--retrieval-engine)
5. [MCP Tool System & Action Executor](#5-mcp-tool-system--action-executor)
6. [Agent Memory Architecture](#6-agent-memory-architecture)
7. [Frontend Architecture (Next.js/React)](#7-frontend-architecture-nextjsreact)
8. [Production Engineering, Guardrails & Security](#8-production-engineering-guardrails--security)
9. [Evaluation & Observability Engine](#9-evaluation--observability-engine)
10. [Multi-Cloud Infrastructure Mapping](#10-multi-cloud-infrastructure-mapping)

---

## 1. Database Schema & Data Models

### 1.1 PostgreSQL Relational Schema (DDL)

```sql
-- Enable UUID and Vector Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Enum Types
CREATE TYPE channel_type AS ENUM ('EMAIL', 'CHAT', 'TICKET_ZENDESK', 'TICKET_INTERCOM', 'IN_APP', 'SLACK');
CREATE TYPE severity_level AS ENUM ('LOW_P3', 'MEDIUM_P2', 'HIGH_P1', 'CRITICAL_P0');
CREATE TYPE ticket_status AS ENUM ('NEW', 'PROCESSING', 'AWAITING_CUSTOMER', 'AWAITING_APPROVAL', 'RESOLVED', 'ESCALATED', 'CLOSED');
CREATE TYPE action_risk_level AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE action_status AS ENUM ('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'EXECUTING', 'SUCCESS', 'FAILED', 'ROLLED_BACK');
CREATE TYPE role_type AS ENUM ('SUPER_ADMIN', 'TENANT_ADMIN', 'SUPPORT_MANAGER', 'TIER1_AGENT', 'TIER2_ENGINEER', 'READ_ONLY');

-- 1. Tenants Table
CREATE TABLE tenants (
    tenant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users / Agents Table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role role_type NOT NULL DEFAULT 'TIER1_AGENT',
    skills TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, email)
);

-- 3. Customers Table
CREATE TABLE customers (
    customer_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    organization VARCHAR(255),
    tier VARCHAR(50) DEFAULT 'STANDARD', -- STANDARD, PREMIUM, ENTERPRISE
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, email)
);

-- 4. Conversations / Tickets Table
CREATE TABLE tickets (
    ticket_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(customer_id),
    assigned_agent_id UUID REFERENCES users(user_id),
    channel channel_type NOT NULL,
    external_ref_id VARCHAR(255),
    subject VARCHAR(500),
    status ticket_status DEFAULT 'NEW',
    severity severity_level DEFAULT 'MEDIUM_P2',
    category VARCHAR(100),
    subcategory VARCHAR(100),
    sentiment_score NUMERIC(3,2), -- -1.00 to +1.00
    confidence_score NUMERIC(3,2), -- 0.00 to 1.00
    is_autonomous_resolved BOOLEAN DEFAULT FALSE,
    resolution_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Row-Level Security for Tenants
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON tickets 
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- 5. Ticket Messages Table
CREATE TABLE ticket_messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL, -- 'CUSTOMER', 'AI_AGENT', 'HUMAN_AGENT', 'SYSTEM'
    sender_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    cleaned_content TEXT,
    attachments JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 6. Action Execution Audit Log
CREATE TABLE action_audits (
    action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    action_name VARCHAR(150) NOT NULL,
    tool_name VARCHAR(150) NOT NULL,
    risk_level action_risk_level NOT NULL,
    parameters JSONB NOT NULL,
    status action_status DEFAULT 'PENDING_APPROVAL',
    requested_by VARCHAR(100) NOT NULL, -- Agent Name or AI Agent ID
    approved_by UUID REFERENCES users(user_id),
    approval_comment TEXT,
    execution_result JSONB,
    error_message TEXT,
    rollback_parameters JSONB,
    executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 7. Case Memory / Resolved Case Repository (Vector Embeddings)
CREATE TABLE resolved_cases (
    case_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    ticket_id UUID UNIQUE REFERENCES tickets(ticket_id),
    issue_summary TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    resolution_steps TEXT NOT NULL,
    category VARCHAR(100),
    embedding vector(1536), -- OpenAI text-embedding-3-small/large
    csat_score INT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_tickets_tenant_status ON tickets(tenant_id, status);
CREATE INDEX idx_tickets_customer ON tickets(customer_id);
CREATE INDEX idx_action_audits_ticket ON action_audits(ticket_id);
CREATE INDEX idx_resolved_cases_vector ON resolved_cases USING hnsw (embedding vector_cosine_ops);
```

### 1.2 Redis Schema & Key Conventions

| Key Pattern | Data Type | TTL | Purpose |
|-------------|-----------|-----|---------|
| `session:{ticket_id}:state` | Hash / JSON | 2 hours | Active LangGraph state checkpoint |
| `customer:{tenant_id}:{customer_id}:context` | String (JSON) | 15 minutes | Cached Customer 360° metrics |
| `ratelimit:{tenant_id}:{ip_or_user}` | String (Counter) | 1 minute | Token Bucket / Fixed Window counter |
| `agent:lock:{ticket_id}` | String | 30 seconds | Distributed lock for concurrent agent processing |
| `pubsub:ticket:{ticket_id}:events` | Pub/Sub Channel | N/A | Real-time SSE/WebSocket stream to Frontend |

### 1.3 Vector Database Indexing Schema (Pinecone / Weaviate / Qdrant)

```json
{
  "collection_name": "knowledge_documents",
  "vector_dimension": 1536,
  "metric": "cosine",
  "schema": {
    "properties": [
      { "name": "doc_id", "type": "string", "index": true },
      { "name": "tenant_id", "type": "string", "index": true },
      { "name": "title", "type": "string", "index": true },
      { "name": "chunk_content", "type": "string", "index": false },
      { "name": "source_url", "type": "string", "index": false },
      { "name": "category", "type": "string", "index": true },
      { "name": "access_level", "type": "string", "index": true },
      { "name": "updated_at", "type": "int", "index": true }
    ]
  }
}
```

---

## 2. API Specifications & Pydantic Schemas

### 2.1 Core Ingestion & Workflow API Endpoints

#### `POST /api/v1/tickets/ingest`
Inbound endpoint for receiving support requests across channels.

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import uuid

class ChannelEnum(str, Enum):
    EMAIL = "EMAIL"
    CHAT = "CHAT"
    TICKET_ZENDESK = "TICKET_ZENDESK"
    TICKET_INTERCOM = "TICKET_INTERCOM"
    IN_APP = "IN_APP"

class IngestTicketRequest(BaseModel):
    tenant_id: uuid.UUID
    channel: ChannelEnum
    external_ref_id: Optional[str] = None
    customer_email: EmailStr
    customer_name: Optional[str] = None
    subject: str = Field(..., max_length=500)
    body: str
    attachments: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

class IngestTicketResponse(BaseModel):
    ticket_id: uuid.UUID
    status: str
    message: str
    queued_at: datetime
```

#### `POST /api/v1/actions/{action_id}/approve`
Human-in-the-loop approval endpoint for high-risk autonomous actions.

```python
class ActionApprovalRequest(BaseModel):
    approved: bool
    approver_id: uuid.UUID
    comment: Optional[str] = None
    override_parameters: Optional[Dict[str, Any]] = None

class ActionApprovalResponse(BaseModel):
    action_id: uuid.UUID
    status: str # "EXECUTING", "REJECTED"
    executed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
```

---

## 3. LangGraph Multi-Agent Architecture

### 3.1 LangGraph State Definition (`SupportState`)

```python
from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator

class TicketMessageDict(TypedDict):
    role: str # "customer", "assistant", "agent", "system"
    content: str
    timestamp: str

class CustomerProfile(TypedDict):
    customer_id: str
    email: str
    tier: str # "STANDARD", "PREMIUM", "ENTERPRISE"
    plan: str
    mrr: float
    open_tickets_count: int

class RetrievedDoc(TypedDict):
    doc_id: str
    title: str
    content: str
    score: float
    source_url: str

class PlannedAction(TypedDict):
    action_id: str
    tool_name: str
    risk_level: str # "LOW", "MEDIUM", "HIGH"
    parameters: Dict[str, Any]
    requires_approval: bool
    status: str

class SupportState(TypedDict):
    # Core identifiers
    ticket_id: str
    tenant_id: str
    
    # Message History (Appended using operator.add)
    messages: Annotated[List[TicketMessageDict], operator.add]
    
    # Context & Classification
    customer: CustomerProfile
    intent: str
    category: str
    severity: str # "LOW_P3", "MEDIUM_P2", "HIGH_P1", "CRITICAL_P0"
    sentiment_score: float
    
    # Agent Reasoning Outputs
    retrieved_docs: List[RetrievedDoc]
    diagnostic_hypotheses: List[str]
    proposed_actions: List[PlannedAction]
    draft_response: str
    
    # Control Flags
    confidence_score: float
    is_escalated: bool
    escalation_reason: Optional[str]
    next_node: str
```

### 3.2 LangGraph Orchestration Workflow (State Graph)

```python
from langgraph.graph import StateGraph, END
from typing import Literal

def build_support_graph():
    workflow = StateGraph(SupportState)

    # Define Agent Nodes
    workflow.add_node("customer_agent", run_customer_agent)
    workflow.add_node("knowledge_agent", run_knowledge_agent)
    workflow.add_node("troubleshooting_agent", run_troubleshooting_agent)
    workflow.add_node("resolution_agent", run_resolution_agent)
    workflow.add_node("escalation_agent", run_escalation_agent)
    workflow.add_node("human_approval_node", run_human_approval)

    # Set Entry Point
    workflow.set_entry_point("customer_agent")

    # Routing Logic after Customer Agent
    def route_after_customer(state: SupportState) -> str:
        if state["severity"] == "CRITICAL_P0" or state["customer"]["tier"] == "ENTERPRISE" and state["sentiment_score"] < -0.8:
            return "escalation_agent"
        return "knowledge_agent"

    workflow.add_conditional_edges("customer_agent", route_after_customer)

    # Routing Logic after Knowledge Agent
    def route_after_knowledge(state: SupportState) -> str:
        if not state["retrieved_docs"] or state["confidence_score"] < 0.4:
            return "troubleshooting_agent"
        return "resolution_agent"

    workflow.add_conditional_edges("knowledge_agent", route_after_knowledge)
    workflow.add_edge("troubleshooting_agent", "resolution_agent")

    # Routing Logic after Resolution Agent
    def route_after_resolution(state: SupportState) -> str:
        if state["confidence_score"] < 0.65 or state["is_escalated"]:
            return "escalation_agent"
        
        # Check if high risk actions are pending approval
        has_high_risk_actions = any(a["requires_approval"] for a in state["proposed_actions"])
        if has_high_risk_actions:
            return "human_approval_node"
            
        return END

    workflow.add_conditional_edges("resolution_agent", route_after_resolution)
    workflow.add_edge("human_approval_node", END)
    workflow.add_edge("escalation_agent", END)

    return workflow.compile()
```

---

## 4. Advanced RAG & Retrieval Engine

### 4.1 Hybrid Retrieval Architecture

The Knowledge/RAG Agent utilizes a **Hybrid Search Pipeline** combining Dense Semantic Vector Search and Sparse Lexical BM25 Search, fused via **Reciprocal Rank Fusion (RRF)** and reranked using a **Cross-Encoder Model**.

```
Query -> Query Decomposition -> Parallel (Dense Search + Sparse Search) -> RRF Fusion -> Cross-Encoder Rerank -> Top-K
```

### 4.2 Python Implementation of RRF & Reranker

```python
from typing import List, Dict, Any
import numpy as np

def reciprocal_rank_fusion(
    vector_results: List[Dict[str, Any]], 
    bm25_results: List[Dict[str, Any]], 
    k: int = 60
) -> List[Dict[str, Any]]:
    """Combines vector search and BM25 search results using Reciprocal Rank Fusion."""
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict[str, Any]] = {}

    for rank, doc in enumerate(vector_results):
        doc_id = doc["doc_id"]
        doc_map[doc_id] = doc
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))

    for rank, doc in enumerate(bm25_results):
        doc_id = doc["doc_id"]
        doc_map[doc_id] = doc
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))

    sorted_docs = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    
    fused_results = []
    for doc_id, score in sorted_docs:
        retrieved_item = doc_map[doc_id]
        retrieved_item["rrf_score"] = score
        fused_results.append(retrieved_item)

    return fused_results
```

---

## 5. MCP Tool System & Action Executor

### 5.1 Model Context Protocol (MCP) Integration

The platform defines tool actions following the standard MCP schema, allowing agents to execute actions safely.

```python
from pydantic import BaseModel, Field

class RefundParameters(BaseModel):
    ticket_id: str = Field(..., description="The unique ticket ID")
    customer_id: str = Field(..., description="Customer ID receiving refund")
    amount: float = Field(..., gt=0.0, le=500.0, description="Refund amount in USD")
    reason: str = Field(..., min_length=10, description="Reason for issuing refund")

class MCPRefundTool:
    name = "issue_customer_refund"
    description = "Issues a partial or full financial refund to a customer account."
    parameters_schema = RefundParameters.schema()
    risk_level = "HIGH" # Requires Human Approval if amount > $50

    async def execute(self, params: RefundParameters, approved_by: Optional[str] = None) -> Dict[str, Any]:
        if params.amount > 50.00 and not approved_by:
            return {
                "status": "REQUIRES_APPROVAL",
                "message": f"Refund of ${params.amount} exceeds $50 threshold. Approval ticket created.",
                "action_required": True
            }
        
        # Execute refund transaction call to Stripe / Billing API
        # ... API call logic ...
        return {
            "status": "SUCCESS",
            "transaction_id": f"tx_refund_{uuid.uuid4().hex[:8]}",
            "amount": params.amount
        }
```

---

## 6. Agent Memory Architecture

### 6.1 Multi-Layered Memory Structure

1. **Short-Term Working Memory:** Stored in Redis (`session:{ticket_id}:state`) managing active multi-turn dialogue state.
2. **Episodic Case Memory:** Stored in PostgreSQL `resolved_cases` vector embeddings to find similar historical resolutions.
3. **Semantic Customer Memory:** Stored in PostgreSQL `customers.metadata` maintaining customer preferences, product usage, and historical interaction trends.

```python
async def recall_similar_cases(tenant_id: str, issue_embedding: List[float], limit: int = 3, db_session = None):
    """Retrieves historically resolved cases matching current issue vector."""
    query = """
        SELECT case_id, issue_summary, root_cause, resolution_steps, 
               1 - (embedding <=> :vector::vector) as similarity
        FROM resolved_cases
        WHERE tenant_id = :tenant_id
        ORDER BY embedding <=> :vector::vector ASC
        LIMIT :limit;
    """
    result = await db_session.execute(query, {
        "tenant_id": tenant_id,
        "vector": str(issue_embedding),
        "limit": limit
    })
    return result.fetchall()
```

---

## 7. Frontend Architecture (Next.js/React)

### 7.1 Dashboard Component Structure

```
src/
├── app/
│   ├── (auth)/login/page.tsx
│   ├── dashboard/
│   │   ├── page.tsx (Overview KPIs)
│   │   ├── tickets/
│   │   │   ├── page.tsx (Ticket Queue Grid)
│   │   │   └── [ticketId]/page.tsx (Agent Assist & Real-time Handoff)
│   │   └── approvals/page.tsx (Human-in-the-loop Queue)
├── components/
│   ├── agent-assist/
│   │   ├── ConversationThread.tsx
│   │   ├── AISuggestionPanel.tsx
│   │   ├── KnowledgeCitations.tsx
│   │   └── ActionApprovalCard.tsx
│   └── ui/ (shadcn components)
```

### 7.2 Real-Time Event Streaming (WebSocket Client Hook)

```typescript
import { useEffect, useState } from 'react';

export function useTicketStream(ticketId: string) {
  const [messages, setMessages] = useState<any[]>([]);
  const [agentState, setAgentState] = useState<any>(null);

  useEffect(() => {
    const ws = new WebSocket(`${process.env.NEXT_PUBLIC_WS_URL}/api/v1/ws/tickets/${ticketId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'NEW_MESSAGE') {
        setMessages((prev) => [...prev, data.payload]);
      } else if (data.type === 'STATE_UPDATE') {
        setAgentState(data.payload);
      }
    };

    return () => ws.close();
  }, [ticketId]);

  return { messages, agentState };
}
```

---

## 8. Production Engineering, Guardrails & Security

### 8.1 Guardrail Pipeline Architecture

```
User Input -> Toxicity & PII Scrubbing -> Input Prompt Injection Detector -> Agent Execution -> Output Hallucination & Fact Checker -> Client Delivery
```

```python
import re

class SafetyGuardrail:
    PII_REGEX = {
        "email": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
        "credit_card": r'\b(?:\d[ -]*?){13,16}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b'
    }

    @classmethod
    def sanitize_input(cls, text: str) -> str:
        """Redacts sensitive PII from incoming customer input."""
        sanitized = text
        for pii_type, pattern in cls.PII_REGEX.items():
            sanitized = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", sanitized)
        return sanitized

    @classmethod
    def detect_prompt_injection(cls, text: str) -> bool:
        """Detects malicious system prompt override attempts."""
        injection_keywords = ["ignore previous instructions", "system prompt", "you are now DAN", "disregard safety rules"]
        return any(keyword in text.lower() for keyword in injection_keywords)
```

---

## 9. Evaluation & Observability Engine

### 9.1 LangSmith Tracing & Quality Metrics

```python
import os
from langsmith import trace

@trace(name="KnowledgeAgent_Execution", run_type="chain")
async def trace_knowledge_agent(query: str, tenant_id: str):
    # LangSmith automatic capture of spans, latencies, tokens, and inputs/outputs
    results = await run_hybrid_search(query, tenant_id)
    return results
```

---

## 10. Multi-Cloud Infrastructure Mapping

### 10.1 Multi-Cloud Service Abstract Grid

| Component | AWS Cloud | Azure Cloud | GCP Cloud | Local Docker Dev |
|-----------|-----------|-------------|-----------|------------------|
| **Kubernetes Compute** | AWS EKS | Azure AKS | GCP GKE | Docker Desktop / K3s |
| **Relational Database** | Amazon RDS PostgreSQL | Azure DB for PostgreSQL | Cloud SQL for PostgreSQL | PostgreSQL 16 Container |
| **Caching Layer** | ElastiCache Redis | Azure Cache for Redis | Memorystore for Redis | Redis 7 Container |
| **Vector Database** | Pinecone / OpenSearch | Azure AI Search | Vertex AI Vector Search | Qdrant / Weaviate Container |
| **Event Bus** | Amazon MSK (Kafka) | Azure Event Hubs | GCP Pub/Sub | Apache Kafka Container |
| **Object Storage** | Amazon S3 | Azure Blob Storage | Google Cloud Storage | MinIO Container |
| **Secrets Manager** | AWS Secrets Manager | Azure Key Vault | GCP Secret Manager | HashiCorp Vault / .env |

---

**Document Control**
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-11-27 | Engineering Team | Initial LLD Draft |

---

*End of Low-Level Design (LLD) Document*