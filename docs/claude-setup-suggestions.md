# Claude Code Setup Suggestions

## Protected Files Found

| Path | Line Count | Location |
|------|------------|----------|
| `CLAUDE.md` | 653 lines | Root |

**Note:** No `SKILLS.md` files found. The project uses `.claude/skills/<name>/SKILL.md` format which is correct.

## Suggested Changes to `CLAUDE.md`

The current `CLAUDE.md` is comprehensive (653 lines) and exceeds the recommended 150-line limit for a root CLAUDE.md. Consider:

1. **Extract to scoped rules**: Move section-specific content to `.claude/rules/`:
   - Architecture Summary → `.claude/rules/architecture.md`
   - Technology Stack → `.claude/rules/tech-stack.md`
   - Database Schema → `.claude/rules/database.md`
   - LangGraph Implementation → `.claude/rules/langgraph.md`
   - Advanced RAG Pipeline → `.claude/rules/rag.md`
   - MCP Tool System → `.claude/rules/mcp-tools.md`
   - Memory Architecture → `.claude/rules/memory.md`
   - Frontend Architecture → `.claude/rules/frontend.md`
   - Guardrails & Security → `.claude/rules/guardrails.md`
   - Observability & Evaluation → `.claude/rules/observability.md`
   - Development Conventions → `.claude/rules/dev-conventions.md`
   - Key API Endpoints → `.claude/rules/api-endpoints.md`
   - Deployment & Environments → `.claude/rules/deployment.md`
   - ADRs → `.claude/rules/adrs.md`
   - Success Metrics → `.claude/rules/metrics.md`
   - Risk Register → `.claude/rules/risks.md`
   - Commands & Workflows → `.claude/rules/workflows.md`

2. **Keep in root CLAUDE.md** (target < 150 lines):
   - Project Overview
   - Cost and Delegation (copy from `.claude/rules/cost-and-delegation.md`)
   - Cache rule: "Do not edit CLAUDE.md, rules, agents, skills or settings during a session"
   - Links to scoped rules

3. **Conflicts with cost plan**: None found. The existing cost-and-delegation rules align with the plan.

## Suggested Changes to Other Markdown

- **Agent descriptions**: All agents have "Delegate here" triggers ✓
- **Rules over 30 lines**: `cost-and-delegation.md` is 11 lines ✓, `backend.md` is 15 lines ✓, `tests.md` is 13 lines ✓
- **READMEs**: No existing READMEs describing old setup

## Per-Run Budgets for Each Agent Type

| Agent Type | Max Tool Calls/Run | Return Limit |
|------------|-------------------|--------------|
| Explore | 10 | 150 words: file paths and line numbers |
| log-triage | 10 | 30 lines: result, failing items with file:line, first error |
| opus-consultant | 10 | 300 words |
| code-reviewer | 30 | Ranked findings list, no preamble |
| planner | 40 | Plan file path only |
| architect | 40 | ADR path plus 50-word summary |
| test-engineer | 80 | 100 words: pass/fail plus digest |
| implementer | 120 | 150 words: changed files and open issues |

## Skipped Agents and Skills

| Item | Reason | Would Add When |
|------|--------|----------------|
| None | All core agents created | N/A |
| `fix-issue` skill | Created but requires issue tracker reference | When issue tracker (GitHub/GitLab) is referenced |
| `pr-review` skill | Created but requires `gh` or `glab` | When `gh` or `glab` is installed and authenticated |

## Placeholders to Fill

| Placeholder | Location | Notes |
|-------------|----------|-------|
| `<PIN: ...>` | Model IDs in settings.json | Currently uses `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5` - verify these are correct for your platform |
| `<DECIDE: probe result>` | TTL setting | Cache TTL probe not yet run |
| `<TODO: command>` | pre-commit.sh type check | No type check command configured (pyproject.toml not found) |
| `<TODO: command>` | pre-commit.sh lint | Uses ruff if available |
| `per-agent breakdown unavailable` | cost-report skill | Usage data may not include agent identity on this version |

## Items to Verify on Pinned Version

- [ ] Each `env` key in settings.json is documented for this version
- [ ] TTL key support (if any)
- [ ] Spawn-depth limit support (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`)
- [ ] CLAUDE.md-skip field on log-triage (`omitClaudeMd: true`)
- [ ] `Agent(...)` tool syntax (currently `Agent(opus-consultant)`)
- [ ] `effort` field support
- [ ] Hook JSON format (PreToolUse with matcher and hooks array)
- [ ] Whether unscoped rules (cost-and-delegation.md) load every session
- [ ] Whether agent identity appears in usage data for per-agent cost tracking

## Next Steps

1. Fill in model ID placeholders with verified IDs for your platform
2. Run the two-turn cache test (Phase 1d) and record results
3. Run one `/plan` → `/implement` → `/test` → `/review` cycle on a small task
4. Compare cost per accepted task, cache-read share, and per-agent cost against baseline