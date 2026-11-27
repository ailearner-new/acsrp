# CloudDesk Support - Makefile
# Usage: make <target>
# Run 'make help' to see available targets

.PHONY: help install install-dev test test-unit test-integration test-e2e test-cov lint format type-check check clean run run-dev demo migrate migrate-create db-shell db-reset

# Default target
help:
	@echo "CloudDesk Support - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install        Install production dependencies"
	@echo "  install-dev    Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test           Run all tests (unit + integration)"
	@echo "  test-unit      Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-e2e       Run end-to-end tests only"
	@echo "  test-cov       Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint           Run ruff linter"
	@echo "  format         Format code with black and isort"
	@echo "  type-check     Run mypy type checker"
	@echo "  check          Run lint, format, and type-check"
	@echo ""
	@echo "Development:"
	@echo "  run            Run production server"
	@echo "  run-dev        Run development server with hot reload"
	@echo "  demo           Run demo script (requires Phase 11)"
	@echo ""
	@echo "Database:"
	@echo "  migrate        Run database migrations"
	@echo "  migrate-create Create new migration (usage: make migrate-create MSG='description')"
	@echo "  db-shell       Open database shell"
	@echo "  db-reset       Reset database (drop all tables and re-run migrations)"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build   Build Docker images"
	@echo "  docker-up      Start Docker Compose stack"
	@echo "  docker-down    Stop Docker Compose stack"
	@echo "  docker-logs    View Docker Compose logs"
	@echo ""
	@echo "Utilities:"
	@echo "  clean          Remove build artifacts and cache"
	@echo "  generate-openapi Generate OpenAPI spec"
	@echo ""

# Variables
PYTHON := python
PIP := pip
UVICORN := uvicorn
PYTEST := pytest
RUFF := ruff
BLACK := black
ISORT := isort
MYPY := mypy
ALEMBIC := alembic

# Paths
BACKEND_DIR := backend
TEST_DIR := tests
SRC_DIR := $(BACKEND_DIR)/app

# Install targets
install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev]"

# Test targets
test:
	DEMO_MODE=true LLM_PROVIDER=fake VECTOR_STORE=memory USE_FAKE_REDIS=true \
	$(PYTEST) $(TEST_DIR) -v --tb=short

test-unit:
	DEMO_MODE=true LLM_PROVIDER=fake VECTOR_STORE=memory USE_FAKE_REDIS=true \
	$(PYTEST) $(TEST_DIR)/unit -v --tb=short

test-integration:
	DEMO_MODE=true LLM_PROVIDER=fake VECTOR_STORE=memory USE_FAKE_REDIS=true \
	$(PYTEST) $(TEST_DIR)/integration -v --tb=short

test-e2e:
	DEMO_MODE=true LLM_PROVIDER=fake VECTOR_STORE=memory USE_FAKE_REDIS=true \
	$(PYTEST) $(TEST_DIR)/e2e -v --tb=short

test-cov:
	DEMO_MODE=true LLM_PROVIDER=fake VECTOR_STORE=memory USE_FAKE_REDIS=true \
	$(PYTEST) $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html

# Code quality targets
lint:
	$(RUFF) check $(SRC_DIR) $(TEST_DIR)

format:
	$(BLACK) $(SRC_DIR) $(TEST_DIR)
	$(ISORT) $(SRC_DIR) $(TEST_DIR)

type-check:
	$(MYPY) $(SRC_DIR)

check: lint format type-check

# Development targets
run:
	$(UVICORN) backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1

run-dev:
	DEMO_MODE=true LLM_PROVIDER=fake VECTOR_STORE=memory USE_FAKE_REDIS=true \
	$(UVICORN) backend.app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir $(BACKEND_DIR)

demo:
	DEMO_MODE=true LLM_PROVIDER=fake VECTOR_STORE=memory USE_FAKE_REDIS=true \
	$(PYTHON) -m scripts.demo

# Database targets
migrate:
	$(ALEMBIC) upgrade head

migrate-create:
	@if [ -z "$(MSG)" ]; then echo "Usage: make migrate-create MSG='description'"; exit 1; fi
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"

db-shell:
	@echo "Opening database shell... (requires psql or sqlite3)"

db-reset:
	@echo "WARNING: This will drop all tables!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] && $(ALEMBIC) downgrade base && $(ALEMBIC) upgrade head

# Docker targets
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-ps:
	docker compose ps

# Utility targets
clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true

generate-openapi:
	$(PYTHON) -c "from backend.app.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > openapi.json
	@echo "OpenAPI spec written to openapi.json"

# CI targets
ci-test: test
ci-lint: lint
ci-type-check: type-check
ci-format-check:
	$(BLACK) --check $(SRC_DIR) $(TEST_DIR)
	$(ISORT) --check-only $(SRC_DIR) $(TEST_DIR)

ci: ci-lint ci-type-check ci-format-check ci-test