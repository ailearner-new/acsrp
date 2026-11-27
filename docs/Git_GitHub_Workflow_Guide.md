# Git & GitHub Workflow Guide

## Branching Strategy

### Branch Types
| Prefix | Purpose | Base | Merge Target |
|--------|---------|------|--------------|
| `feature/` | New functionality | `development` | `development` |
| `fix/` | Bug fixes | `development` | `development` |
| `docs/` | Documentation only | `development` | `development` |
| `refactor/` | Code restructuring | `development` | `development` |
| `chore/` | Maintenance, deps, config | `development` | `development` |
| `release/` | Release preparation | `development` | `main` + `development` |
| `hotfix/` | Production critical fixes | `main` | `main` + `development` |

### Protected Branches
- `main` - Production-ready code only
- `development` - Integration branch for features

## Commit Convention

Follow Conventional Commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `refactor` - Code restructuring
- `perf` - Performance improvement
- `test` - Tests
- `chore` - Maintenance
- `ci` - CI/CD changes
- `security` - Security fix

### Scopes (from CLAUDE.md layering)
- `api` - HTTP, auth, RBAC
- `services` - Orchestration, repositories
- `repos` - SQL, data access
- `core` - Config, security, logging, Redis, guardrails, DB
- `tools` - ToolRegistry, MCP tools
- `agents` - State, graph, nodes, specialists, prompts
- `rag` - Chunking, retrieval
- `memory` - Short/long-term notes
- `frontend` - Next.js console
- `infra` - Terraform, K8s
- `deps` - Dependencies

### Examples
```
feat(agents): add hypothesis ranking to troubleshooting agent

Implement probability-based hypothesis generation using
correlation with known incidents database.

Closes #123
```

```
fix(core): prevent severity lowering in policy rules

Severity rules now only raise, never lower the model's
assessed severity. Added test case for critical floor.

Fixes #456
```

```
refactor(api): extract validation middleware

Move request validation from route handlers to shared
middleware. Reduces duplication across 12 endpoints.
```

## Pull Request Process

### PR Requirements
1. **Branch name** matches `TASKS.md` row exactly
2. **Single sub-task** per PR (one `TASKS.md` row)
3. **Predecessor merged** - check `TASKS.md` predecessor status
4. **Tests pass** - `make test` in offline mode
5. **Type check passes** - `mypy`/`pyright`
6. **Lint passes** - `ruff`
7. **Format passes** - `black`
7. **Linked issue** - reference `TASKS.md` row and any GitHub issue

### PR Template
```markdown
## Summary
Brief description of changes.

## TASKS.md Row
- Row: `1.3` (or `feature/branch-name`)
- Predecessor: `1.2` ✅ Completed

## Changes
- `backend/agents/troubleshooting/agent.py`: hypothesis ranking
- `backend/agents/troubleshooting/prompts.py`: updated prompt
- `tests/agents/test_troubleshooting.py`: new test cases

## Testing
- [ ] Unit tests pass (`make test`)
- [ ] Type check passes
- [ ] Lint passes
- [ ] Manual verification: `make demo TICKET=CD-1002`

## Checklist
- [ ] No secrets in code
- [ ] No PII in logs/tests
- [ ] Layering respected (no reverse imports)
- [ ] Ticket text wrapped with `wrap_untrusted`
- [ ] Policy decisions in `agents/rules.py` or `backend/app/tools/policy.py`
```

### Review Process
1. **Author** creates PR from feature branch to `development`
2. **Automated checks** run: type check, lint, tests, security scan
3. **Reviewer** (assigned by area):
   - `api/*` → backend lead
   - `agents/*` → ML lead
   - `rag/*` → ML lead
   - `memory/*` → backend lead
   - `frontend/*` → frontend lead
   - `infra/*` → DevOps lead
4. **Approval required**: 1 approval + all checks green
5. **Merge**: Squash and merge to `development`
6. **Update `TASKS.md`**: Set row to `Completed ✅` after merge

### Review Focus Areas
| Area | What to Check |
|------|---------------|
| Correctness | Logic matches requirements, edge cases handled |
| Layering | No reverse imports (core → services → repos → api) |
| Security | No secrets, PII scrubbed, ticket text wrapped |
| Policy | Rules only raise severity, approvals for money/actions |
| Tests | Offline mode, one feature = one test, auth fixtures used |
| Performance | No N+1 queries, proper caching, latency budgets |

## Release Process

### Versioning
Semantic Versioning: `MAJOR.MINOR.PATCH`
- `MAJOR` - Breaking API changes
- `MINOR` - New features, backward compatible
- `PATCH` - Bug fixes, backward compatible

### Release Branches
1. Create `release/vX.Y.0` from `development`
2. Only bug fixes and version bumps allowed
3. Run full test suite including integration/E2E
4. Deploy to staging, run `make demo` gates
5. Tag `vX.Y.0` on `main`
6. Merge `release/vX.Y.0` → `main` and `development`
7. Deploy to production

### Hotfix Process
1. Create `hotfix/vX.Y.Z` from `main`
2. Fix critical production issue
2. Test thoroughly
3. Tag `vX.Y.Z` on `main`
4. Merge `hotfix/vX.Y.Z` → `main` and `development`

## Git Commands Reference

### Daily Workflow
```bash
# Start new sub-task (check TASKS.md predecessor first)
git checkout development
git pull origin development
git checkout -b feature/my-sub-task

# Work on changes...
git add -A
git commit -m "feat(scope): subject"

# Push and create PR
git push origin feature/my-sub-task
gh pr create --base development --title "feat(scope): subject"

# After review and merge
git checkout development
git pull origin development
# Update TASKS.md row to Completed ✅
```

### Syncing with Development
```bash
# Rebase feature branch on latest development
git checkout feature/my-sub-task
git fetch origin
git rebase origin/development

# If conflicts, resolve and continue
git rebase --continue
```

### Viewing History
```bash
# Recent commits on development
git log --oneline -20 development

# Commits in feature branch not in development
git log origin/development..HEAD --oneline

# Files changed in PR
gh pr diff --name-only
```

## GitHub Configuration

### Required Status Checks (Branch Protection)
- `ci/type-check`
- `ci/lint`
- `ci/test`
- `ci/security-scan`
- `ci/build`

### Required Reviews
- 1 approval from code owner
- Dismiss stale reviews on new commits

### Auto-merge
Enable for PRs that pass all checks and have approval.

## Secrets Management

### Never Commit
- `.env` files
- `*.pem`, `*.key`, `*.crt`
- `terraform.tfvars`
- `backend.hcl`
- `tfplan`
- `data/`
- `*.db`
- Any file with `secret`, `password`, `key`, `token` in name

### Use Instead
- GitHub Environments for deployment secrets
- HashiCorp Vault for runtime secrets
- External Secrets Operator for K8s

## Local Development Setup

### Git Config
```bash
# Required for commit signing
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global commit.gpgsign true

# Helpful aliases
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'
git config --global alias.visual '!gitk'
```

### Pre-commit Hooks
The project uses `.claude/hooks/pre-commit.sh` which runs on `git commit`:
- Type check (when configured)
- Lint on staged Python files (`ruff`)
- Tests (`pytest`)

```bash
# Install pre-commit (optional, for local runs)
pip install pre-commit
pre-commit install
```

## Monorepo Considerations

This project is currently a **single repo** (not a monorepo). If it becomes a monorepo:

1. **Package-scoped rules** in `.claude/rules/<package>.md`
2. **Per-package CI** - only test changed packages
3. **Independent versioning** per package
4. **Shared tooling** in root, package-specific in subdirs

---

*Follow this guide for all Git/GitHub interactions. Update when workflow changes.*