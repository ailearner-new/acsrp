# API_CONTRACT.md - Routes and Payload Types

## Overview
All APIs are versioned under `/api/v1/`. OpenAPI 3.1 spec is the source of truth.

## Authentication
- All endpoints require `Authorization: Bearer <JWT>` header
- JWT contains: `tenant_id`, `user_id`, `role`, `exp`
- Roles: `SUPER_ADMIN`, `TENANT_ADMIN`, `SUPPORT_MANAGER`, `TIER1_AGENT`, `TIER2_ENGINEER`, `READ_ONLY`

---

## Ingestion Endpoints

### POST /api/v1/tickets/ingest
Ingest a support request from any channel.

**Request:**
```json
{
  "tenant_id": "uuid",
  "channel": "EMAIL|CHAT|TICKET_ZENDESK|TICKET_INTERCOM|IN_APP",
  "external_ref_id": "string (optional)",
  "customer_email": "string (email)",
  "customer_name": "string (optional)",
  "subject": "string (max 500)",
  "body": "string",
  "attachments": [{"name": "string", "url": "string", "content_type": "string"}],
  "metadata": {}
}
```

**Response (202):**
```json
{
  "ticket_id": "uuid",
  "status": "queued",
  "message": "Request accepted for processing",
  "queued_at": "ISO8601"
}
```

### GET /api/v1/tickets/{ticket_id}
Get ticket details.

**Response (200):**
```json
{
  "ticket_id": "uuid",
  "tenant_id": "uuid",
  "customer_id": "uuid",
  "assigned_agent_id": "uuid|null",
  "channel": "CHAT",
  "external_ref_id": "string|null",
  "subject": "string",
  "status": "NEW|PROCESSING|AWAITING_CUSTOMER|AWAITING_APPROVAL|RESOLVED|ESCALATED|CLOSED",
  "severity": "LOW_P3|MEDIUM_P2|HIGH_P1|CRITICAL_P0",
  "category": "string",
  "subcategory": "string|null",
  "sentiment_score": -0.5,
  "confidence_score": 0.85,
  "is_autonomous_resolved": false,
  "resolution_summary": "string|null",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

### GET /api/v1/tickets/{ticket_id}/messages
Get conversation history.

**Response (200):**
```json
[
  {
    "message_id": "uuid",
    "sender_type": "CUSTOMER|AI_AGENT|HUMAN_AGENT|SYSTEM",
    "sender_id": "string",
    "content": "string",
    "cleaned_content": "string|null",
    "attachments": [],
    "metadata": {},
    "created_at": "ISO8601"
  }
]
```

---

## Customer API

### POST /api/v1/customers
Create a new customer in the system.

**Request:**
```json
{
  "external_id": "string (optional)",
  "email": "string (email)",
  "full_name": "string (optional)",
  "organization": "string (optional)",
  "tier": "STANDARD|PREMIUM|ENTERPRISE",
  "metadata": {}
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "external_id": "string|null",
  "email": "string",
  "full_name": "string|null",
  "organization": "string|null",
  "tier": "STANDARD|PREMIUM|ENTERPRISE",
  "metadata": {},
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

### GET /api/v1/customers/{customer_id}
Get customer details by ID.

**Response (200):**
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "external_id": "string|null",
  "email": "string",
  "full_name": "string|null",
  "organization": "string|null",
  "tier": "STANDARD|PREMIUM|ENTERPRISE",
  "metadata": {},
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

**Errors:**
- `404` - Customer not found

### PATCH /api/v1/customers/{customer_id}
Update customer details (partial update).

**Request:**
```json
{
  "external_id": "string (optional)",
  "full_name": "string (optional)",
  "organization": "string (optional)",
  "tier": "STANDARD|PREMIUM|ENTERPRISE (optional)",
  "metadata": {} (optional)
}
```

**Response (200):**
Same as GET response (CustomerResponse).

**Errors:**
- `404` - Customer not found

### GET /api/v1/customers/
List customers with filtering and pagination.

**Query Parameters:**
- `email` (optional) - Filter by email (partial match)
- `tier` (optional) - Filter by tier
- `organization` (optional) - Filter by organization
- `limit` (optional, default 50) - Number of results per page
- `offset` (optional, default 0) - Pagination offset

**Response (200):**
```json
{
  "customers": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "external_id": "string|null",
      "email": "string",
      "full_name": "string|null",
      "organization": "string|null",
      "tier": "STANDARD|PREMIUM|ENTERPRISE",
      "metadata": {},
      "created_at": "ISO8601",
      "updated_at": "ISO8601"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

**Errors:**
- `401` - Unauthorized
- `403` - Forbidden

---

## Knowledge Article API

### POST /api/v1/articles
Create a new knowledge article.

**Request:**
```json
{
  "title": "string (max 500)",
  "content": "string",
  "source_url": "string (optional)",
  "category": "ACCOUNT_ACCESS|BILLING_SUBSCRIPTION|FEATURE_HOW_TO|BASIC_TROUBLESHOOTING|ORDER_STATUS|TECHNICAL_BUG|API_ISSUE|INTEGRATION_PROBLEM|COMPLEX_BILLING_DISPUTE|FEATURE_REQUEST",
  "access_level": "internal|public",
  "metadata": {}
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "title": "string",
  "content": "string",
  "source_url": "string|null",
  "category": "string|null",
  "access_level": "string",
  "is_active": true,
  "chunk_count": 0,
  "metadata": {},
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

**Roles:** `SUPER_ADMIN`, `TENANT_ADMIN`, `SUPPORT_MANAGER`

### GET /api/v1/articles/{article_id}
Get a knowledge article by ID.

**Response (200):**
Same as POST response (KnowledgeArticleResponse).

**Errors:**
- `404` - Knowledge article not found

**Roles:** `SUPER_ADMIN`, `TENANT_ADMIN`, `SUPPORT_MANAGER`, `TIER1_AGENT`, `TIER2_ENGINEER`, `READ_ONLY`

### PATCH /api/v1/articles/{article_id}
Update a knowledge article.

**Request:**
```json
{
  "title": "string (optional)",
  "content": "string (optional)",
  "source_url": "string (optional)",
  "category": "string (optional)",
  "access_level": "internal|public (optional)",
  "is_active": true,
  "metadata": {} (optional)
}
```

**Response (200):**
Same as GET response (KnowledgeArticleResponse).

**Roles:** `SUPER_ADMIN`, `TENANT_ADMIN`, `SUPPORT_MANAGER`

### DELETE /api/v1/articles/{article_id}
Delete a knowledge article.

**Response:** `204 No Content`

**Roles:** `SUPER_ADMIN`, `TENANT_ADMIN`, `SUPPORT_MANAGER`

### GET /api/v1/articles/
List knowledge articles with optional filters.

**Query Parameters:**
- `category` (optional) - Filter by category
- `limit` (optional, default 50) - Number of results per page
- `offset` (optional, default 0) - Pagination offset
- `active_only` (optional, default true) - Show only active articles

**Response (200):**
```json
{
  "articles": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "title": "string",
      "source_url": "string|null",
      "category": "string|null",
      "chunk_count": 12,
      "updated_at": "ISO8601"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

**Roles:** `SUPER_ADMIN`, `TENANT_ADMIN`, `SUPPORT_MANAGER`, `TIER1_AGENT`, `TIER2_ENGINEER`, `READ_ONLY`

---

## Agent Assist (Real-time)

### WS /api/v1/ws/tickets/{ticket_id}
WebSocket for real-time agent state updates.

**Client → Server:**
```json
{"type": "subscribe", "ticket_id": "uuid"}
```

**Server → Client (NEW_MESSAGE):**
```json
{
  "type": "NEW_MESSAGE",
  "payload": {
    "message_id": "uuid",
    "sender_type": "CUSTOMER",
    "content": "string",
    "created_at": "ISO8601"
  }
}
```

**Server → Client (STATE_UPDATE):**
```json
{
  "type": "STATE_UPDATE",
  "payload": {
    "intent": "billing.refund",
    "severity": "HIGH_P1",
    "confidence_score": 0.85,
    "retrieved_docs": [...],
    "proposed_actions": [...],
    "draft_response": "string",
    "next_node": "resolution_agent"
  }
}
```

### POST /api/v1/tickets/{ticket_id}/agent-action
Agent accepts/edits/rejects AI suggestion.

**Request:**
```json
{
  "action": "accept|edit|reject",
  "suggestion_id": "string",
  "edited_content": "string (optional)",
  "edited_actions": [{"tool_name": "string", "parameters": {}}] (optional)
}
```

**Response (200):**
```json
{
  "status": "applied|rejected",
  "message_id": "uuid|null"
}
```

---

## Human-in-the-Loop (Approvals)

### GET /api/v1/approvals/pending
Get pending approvals for current user/team.

**Query:** `?status=pending&limit=50&offset=0`

**Response (200):**
```json
{
  "approvals": [
    {
      "action_id": "uuid",
      "ticket_id": "uuid",
      "tool_name": "billing.refund",
      "risk_level": "HIGH",
      "parameters": {"amount": 75, "customer_id": "uuid", "reason": "..."},
      "requested_by": "resolution_agent",
      "created_at": "ISO8601",
      "context": {
        "customer": {...},
        "ticket_summary": "...",
        "confidence_score": 0.82
      }
    }
  ],
  "total": 1
}
```

### POST /api/v1/actions/{action_id}/approve
Approve or reject a high-risk action.

**Request:**
```json
{
  "approved": true,
  "approver_id": "uuid",
  "comment": "string (optional)",
  "override_parameters": {"amount": 50} (optional)
}
```

**Response (200):**
```json
{
  "action_id": "uuid",
  "status": "EXECUTING|REJECTED",
  "executed_at": "ISO8601|null",
  "result": {"transaction_id": "tx_refund_abc123", "amount": 50} | null
}
```

---

## Knowledge Management

### POST /api/v1/knowledge/search
Hybrid search across knowledge base.

**Request:**
```json
{
  "query": "string",
  "tenant_id": "uuid",
  "filters": {"category": "string", "access_level": "public|internal"},
  "limit": 10,
  "include_citations": true
}
```

**Response (200):**
```json
{
  "results": [
    {
      "doc_id": "string",
      "title": "string",
      "content": "string",
      "score": 0.92,
      "rrf_score": 0.015,
      "source_url": "string",
      "category": "string",
      "updated_at": "ISO8601"
    }
  ],
  "query_id": "uuid",
  "latency_ms": 120
}
```

### POST /api/v1/knowledge/index
Trigger reindex of a document or all documents.

**Request:**
```json
{
  "doc_ids": ["string"] | null,
  "tenant_id": "uuid",
  "force": false
}
```

**Response (202):**
```json
{
  "index_job_id": "uuid",
  "status": "started",
  "estimated_docs": 1500
}
```

### GET /api/v1/knowledge/documents
List documents with pagination.

**Query:** `?tenant_id=uuid&category=string&limit=50&offset=0`

**Response (200):**
```json
{
  "documents": [
    {
      "doc_id": "string",
      "title": "string",
      "category": "string",
      "source_url": "string",
      "updated_at": "ISO8601",
      "chunk_count": 12
    }
  ],
  "total": 1500
}
```

---

## Analytics

### GET /api/v1/analytics/overview
Dashboard KPIs.

**Query:** `?tenant_id=uuid&from=ISO8601&to=ISO8601`

**Response (200):**
```json
{
  "period": {"from": "ISO8601", "to": "ISO8601"},
  "kpis": {
    "total_tickets": 15420,
    "autonomous_resolution_rate": 0.72,
    "mttr_autonomous_minutes": 3.2,
    "mttr_assisted_hours": 1.8,
    "csat": 4.6,
    "escalation_rate": 0.28,
    "cost_per_ticket_auto": 1.85,
    "cost_per_ticket_assisted": 12.40,
    "first_contact_resolution": 0.87
  },
  "trends": {
    "tickets_per_day": [...],
    "arr_per_day": [...]
  }
}
```

### GET /api/v1/analytics/tickets
Ticket metrics with filters.

**Query:** `?tenant_id=uuid&channel=CHAT&category=billing&severity=HIGH_P1&from=ISO8601&to=ISO8601&group_by=day|channel|category|agent`

**Response (200):**
```json
{
  "metrics": [
    {"bucket": "2026-11-20", "count": 142, "arr": 0.71, "mttr_min": 4.1},
    {"bucket": "2026-11-21", "count": 156, "arr": 0.73, "mttr_min": 3.8}
  ],
  "total": 298
}
```

### GET /api/v1/analytics/agents
Agent performance metrics.

**Query:** `?tenant_id=uuid&from=ISO8601&to=ISO8601`

**Response (200):**
```json
{
  "agents": [
    {
      "agent_id": "uuid",
      "name": "string",
      "tickets_handled": 234,
      "avg_mttr_minutes": 12.5,
      "csat": 4.7,
      "acceptance_rate": 0.82,
      "escalation_rate": 0.15
    }
  ]
}
```

---

## Admin & Configuration

### GET /api/v1/admin/tenants
List tenants (SUPER_ADMIN only).

### POST /api/v1/admin/tenants
Create tenant.

### GET /api/v1/admin/tenants/{tenant_id}/config
Get tenant configuration.

### PUT /api/v1/admin/tenants/{tenant_id}/config
Update tenant configuration.

### GET /api/v1/admin/users
List users with pagination and filters.

### POST /api/v1/admin/users
Create user.

### PUT /api/v1/admin/users/{user_id}
Update user (role, skills, active status).

### GET /api/v1/admin/action-catalog
List all available actions with risk levels.

### POST /api/v1/admin/action-catalog
Register new action.

### PUT /api/v1/admin/action-catalog/{tool_name}
Update action risk level / approval requirements.

### GET /api/v1/admin/automation-rules
List automation rules.

### POST /api/v1/admin/automation-rules
Create automation rule (conditions → actions DSL).

---

## Error Responses

All errors follow RFC 7807 Problem Details:

```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "Request body failed validation",
  "instance": "/api/v1/tickets/ingest",
  "errors": [
    {"field": "customer_email", "message": "Invalid email format"}
  ]
}
```

Common status codes:
- `400` - Validation error
- `401` - Unauthorized (invalid/expired token)
- `403` - Forbidden (insufficient role)
- `404` - Not found
- `409` - Conflict (e.g., duplicate)
- `422` - Unprocessable entity (business rule violation)
- `429` - Rate limited
- `500` - Internal server error
- `503` - Service unavailable (degraded mode)

---

## Rate Limits

| Tier | Requests/Minute | Burst |
|------|-----------------|-------|
| TIER1_AGENT | 60 | 10 |
| TIER2_ENGINEER | 120 | 20 |
| SUPPORT_MANAGER | 300 | 50 |
| TENANT_ADMIN | 600 | 100 |
| API_ONLY | 1000 | 200 |

Exceeding limits returns `429` with `Retry-After` header.

---

## Webhook Events (Outbound)

Platform sends these events to registered webhook URLs:

### ticket.created
```json
{"event": "ticket.created", "ticket_id": "uuid", "tenant_id": "uuid", "timestamp": "ISO8601"}
```

### ticket.resolved
```json
{"event": "ticket.resolved", "ticket_id": "uuid", "resolution_type": "autonomous|assisted", "mttr_seconds": 180}
```

### ticket.escalated
```json
{"event": "ticket.escalated", "ticket_id": "uuid", "reason": "confidence_low", "assigned_to": "uuid"}
```

### action.approved / action.rejected / action.executed
```json
{"event": "action.executed", "action_id": "uuid", "tool_name": "billing.refund", "result": {...}}
```

---

*This contract is the source of truth. Route or payload changes update this file, `backend/app/schemas/`, and `frontend/lib/types.ts` in the same change.*