# ADR-003: PostgreSQL as Primary Store

## Status
Accepted

## Context
Need a primary transactional database with:
- ACID transactions for ticket state, actions, audit logs
- JSONB flexibility for semi-structured data (metadata, config)
- Row-level security (RLS) for multi-tenancy
- Vector embeddings via pgvector for episodic memory
- Mature ecosystem and tooling
- Cloud-managed options on all three clouds

Evaluated options:
1. **PostgreSQL 16** - ACID, JSONB, RLS, pgvector, mature, cloud-managed everywhere
2. **MySQL 8** - No native RLS, limited JSON, no pgvector equivalent
3. **MongoDB** - No ACID transactions across documents, no RLS
4. **DynamoDB** - Cloud-specific, no SQL, no RLS, expensive at scale
5. **CockroachDB** - Distributed SQL, but adds complexity, no pgvector

## Decision
Use **PostgreSQL 16** as the primary transactional database.

## Consequences

### Positive
- ACID compliance for critical data (tickets, actions, audit)
- Row-level security enforces tenant isolation at database level
- pgvector extension for vector embeddings (episodic memory)
- JSONB for flexible metadata, config, message content
- Cloud-managed on all providers (RDS, Azure Database, Cloud SQL)
- Rich ecosystem: Alembic, SQLAlchemy, asyncpg, pgvector
- Mature tooling for backup, PITR, read replicas

### Negative
- Vertical scaling limits (mitigated by read replicas)
- Connection pooling required at scale (PgBouncer)
- pgvector HNSW indexes require memory
- No horizontal sharding built-in

## Implementation Notes
- All tables include `tenant_id` with RLS policy
- `CREATE POLICY tenant_isolation_policy ON <table> USING (tenant_id = current_setting('app.current_tenant_id')::uuid)`
- Connection pooling via PgBouncer in front of managed instances
- Read replicas for analytics queries
- Alembic for migrations (additive only)

## Related
- ADR-004: Multi-Cloud from Day One
- ADR-005: Hybrid Retrieval (pgvector for episodic memory)