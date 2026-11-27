# ADR-005: Hybrid Retrieval (Vector + BM25 + Graph + RRF)

## Status
Accepted

## Context
Pure vector search misses exact keyword matches; pure keyword search misses semantic similarity. We need high recall AND precision for knowledge retrieval.

Evaluated options:
1. **Vector only** - Good semantic, poor exact match
2. **BM25 only** - Good exact match, poor semantic
3. **Vector + BM25 (RRF)** - Better recall, good balance
4. **Vector + BM25 + Graph + RRF + Rerank** - Best recall + precision

## Decision
Combine **vector (semantic), BM25 (keyword), and graph (relationships)** retrieval, fused via **Reciprocal Rank Fusion (RRF, k=60)**, then **cross-encoder reranked**.

## Consequences

### Positive
- Highest recall: catches semantic, exact, and relational matches
- Highest precision: reranker filters noise
- Citations from multiple sources increase trust
- Tenant-scoped namespaces prevent leakage

### Negative
- More complex pipeline (3 retrieval paths + fusion + rerank)
- Higher latency (~200-500ms vs ~50ms for single)
- More infrastructure (vector DB, OpenSearch, graph DB)
- Cross-encoder reranker adds cost

## Implementation Notes
- Vector: Pinecone/Weaviate/Qdrant (HNSW, cosine)
- BM25: OpenSearch or PostgreSQL full-text
- Graph: Relationships between docs, tickets, issues
- RRF: `score = 1/(k + rank_vector) + 1/(k + rank_bm25) + 1/(k + rank_graph)`
- Rerank: Cohere Rerank or BGE cross-encoder on top-50 → top-10
- Cache: Query embeddings, frequent queries

## Related
- ADR-001: LangGraph Orchestration (Knowledge Agent uses this)
- ADR-003: PostgreSQL Primary Store (BM25 + pgvector for episodic)