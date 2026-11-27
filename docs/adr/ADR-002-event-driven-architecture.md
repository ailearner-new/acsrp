# ADR-002: Event-Driven Architecture

## Status
Accepted

## Context
Multiple services need to communicate asynchronously:
- Ingestion service produces `SupportRequest` events
- Orchestration service consumes events and coordinates agents
- Agents produce results that trigger next steps
- Action executor emits audit events
- External systems (Zendesk, etc.) send webhooks
- Need audit trail and replay capability

Evaluated options:
1. **Kafka** - High throughput, durability, replay, exactly-once semantics
2. **RabbitMQ** - Lower throughput, less durable, no native replay
3. **AWS SQS/SNS** - Cloud-specific, no replay, limited ordering
4. **Redis Streams** - Lower durability, not designed for event sourcing
5. **Custom HTTP callbacks** - Tight coupling, no durability, no replay

## Decision
Adopt **event-driven architecture with Kafka** as the event backbone.

## Consequences

### Positive
- Loose coupling between services
- Horizontal scalability via consumer groups
- Event sourcing: immutable audit trail, replay for debugging
- Exactly-once semantics for critical operations
- Multi-cloud: MSK (AWS), Event Hubs (Azure), Pub/Sub (GCP)
- Schema registry for contract evolution

### Negative
- Eventual consistency complexity
- Operational overhead (brokers, topics, monitoring)
- Debugging distributed traces more complex
- Schema evolution requires discipline

## Implementation Notes
- Topic naming: `{domain}.{entity}.{action}` (e.g., `support.ticket.created`)
- Avro schemas in schema registry
- Consumer groups per service for scaling
- DLQ for failed processing
- Retention: 7 days, replication factor 3

## Related
- ADR-001: LangGraph Orchestration (consumes events)
- ADR-003: PostgreSQL as Primary Store (event sourcing complement)