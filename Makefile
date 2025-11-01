# Arash External API Service - Makefile
# Essential commands for development and deployment

.PHONY: help check-poetry install run test lint format clean \
        docker-build docker-run migrate-up \
        db-teams db-keys db-team-create db-key-create

# Detect poetry location (allow override with POETRY=/path/to/poetry)
POETRY ?= $(shell which poetry 2>/dev/null || echo "$$HOME/.local/bin/poetry")

# Check if poetry is available
check-poetry:
	@if ! command -v $(POETRY) >/dev/null 2>&1; then \
		echo "[ERROR] Poetry not found!"; \
		echo ""; \
		echo "Please install Poetry or add it to your PATH:"; \
		echo "  export PATH=\"\$$HOME/.local/bin:\$$PATH\""; \
		echo ""; \
		echo "Or override poetry location:"; \
		echo "  make test POETRY=/path/to/poetry"; \
		exit 1; \
	fi

# Default target
help:
	@echo "========================================================================"
	@echo "Arash External API Service - Essential Commands"
	@echo "========================================================================"
	@echo ""
	@echo "NOTE: Requires Poetry (detected at: $(POETRY))"
	@echo ""
	@echo "[Development]"
	@echo "  make install     Install dependencies"
	@echo "  make run         Run application (port 3000)"
	@echo "  make test        Run test suite"
	@echo "  make lint        Check code quality"
	@echo "  make format      Format code"
	@echo "  make clean       Remove cache files"
	@echo ""
	@echo "[Docker]"
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-run     Run Docker container"
	@echo ""
	@echo "[Database]"
	@echo "  make migrate-up     Apply migrations"
	@echo "  make db-teams       List teams"
	@echo "  make db-keys        List API keys"
	@echo "  make db-team-create NAME=\"Team\" [DAILY=100] [MONTHLY=3000]"
	@echo "  make db-key-create  TEAM=<id> NAME=\"Key\" [LEVEL=user]"
	@echo ""

# ============================================================================
# Development
# ============================================================================

install: check-poetry
	@echo "[Installing dependencies...]"
	$(POETRY) install --no-root

run: check-poetry
	@echo "[Starting Arash API Service...]"
	@echo "API: http://localhost:3000"
	$(POETRY) run uvicorn app.main:app --host 0.0.0.0 --port 3000

test: check-poetry
	@echo "[Running tests...]"
	$(POETRY) run pytest -v

lint: check-poetry
	@echo "[Checking code quality...]"
	$(POETRY) run ruff check app/ tests/

format: check-poetry
	@echo "[Formatting code...]"
	$(POETRY) run black app/ tests/

clean:
	@echo "[Cleaning cache...]"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# ============================================================================
# Docker
# ============================================================================

docker-build:
	@echo "[Building Docker image...]"
	docker build -t arash-external-api:latest .

docker-run:
	@echo "[Running Docker container...]"
	docker run --rm --env-file .env -p 3000:3000 arash-external-api:latest

# ============================================================================
# Database
# ============================================================================

migrate-up: check-poetry
	@echo "[Applying migrations...]"
	$(POETRY) run alembic upgrade head

db-teams: check-poetry
	@$(POETRY) run python scripts/manage_api_keys.py team list

db-keys: check-poetry
	@$(POETRY) run python scripts/manage_api_keys.py key list

db-team-create: check-poetry
ifndef NAME
	@echo "[ERROR] NAME is required"
	@echo "Usage: make db-team-create NAME=\"Team\" [DAILY=100] [MONTHLY=3000]"
	@exit 1
endif
	$(POETRY) run python scripts/manage_api_keys.py team create "$(NAME)" \
		$(if $(DAILY),--daily-quota $(DAILY)) \
		$(if $(MONTHLY),--monthly-quota $(MONTHLY))

db-key-create: check-poetry
ifndef TEAM
	@echo "[ERROR] TEAM and NAME are required"
	@echo "Usage: make db-key-create TEAM=<id> NAME=\"Key\" [LEVEL=user]"
	@exit 1
endif
ifndef NAME
	@echo "[ERROR] NAME is required"
	@echo "Usage: make db-key-create TEAM=<id> NAME=\"Key\" [LEVEL=user]"
	@exit 1
endif
	$(POETRY) run python scripts/manage_api_keys.py key create $(TEAM) "$(NAME)" \
		$(if $(LEVEL),--level $(LEVEL))
