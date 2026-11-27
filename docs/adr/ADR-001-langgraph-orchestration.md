# ADR-001: LangGraph for Agent Orchestration

## Status
Accepted

## Context
We need a multi-agent orchestration framework that supports:
- Stateful workflows with checkpointing
- Human-in-the-loop (HITL) approvals
- Complex conditional routing between agents
- Observability and debugging of agent decisions
- Streaming responses for real-time UX

Evaluated options:
1. **LangGraph** - Purpose-built for stateful multi-agent graphs, native HITL, checkpointing
2. **LangChain Agents** - Legacy, less suited for complex graphs, limited HITL
3. **Custom State Machine** - Full control but high implementation cost
4. **AutoGen** - Good for multi-agent but less mature workflow orchestration
5. **CrewAI** - Higher-level, less control over graph structure

## Decision
Use **LangGraph** as the agent orchestration framework.

## Consequences

### Positive
- Built-in HITL with `interrupt()` / `Command(resume=...)` pattern
- State persistence via checkpointers (Redis, PostgreSQL)
- Streaming support for real-time agent updates
- Visual debugging with LangGraph Studio
- First-class LangSmith integration for tracing
- Conditional edges enable complex routing logic
- Active development and community

### Negative
- Relatively new (0.2+), smaller community than LangChain
- Learning curve for graph-based thinking
- Potential breaking changes in minor versions
- Less documentation for advanced patterns

## Implementation Notes
- State schema: `SupportState` TypedDict in `services/orchestration-service/graph/state.py`
- Compiled graph in `services/orchestration-service/graph/workflow.py`
- Redis checkpointer for workflow state persistence
- All agent nodes as async functions returning partial state dicts

## Related
- ADR-002: Event-Driven Architecture (Kafka for async communication)
- ADR-006: Human-in-the-Loop for All Write Actions