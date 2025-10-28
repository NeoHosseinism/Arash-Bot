# Arash External API Service - Makefile v1.1
# Commands for development, deployment, and database management

.PHONY: help install install-poetry run test lint clean format \
        docker-build docker-run docker-push \
        migrate-create migrate-up migrate-down migrate-status \
        db-init db-teams db-keys db-usage db-team-create db-team-delete \
        db-key-create db-key-revoke \
        k8s-deploy-dev k8s-deploy-stage k8s-deploy-prod

# Default target
help:
	@echo "================================================================================"
	@echo "Arash External API Service v1.1 - Available Commands"
	@echo "================================================================================"
	@echo ""
	@echo "[Poetry & Dependencies]"
	@echo "  make install-poetry Install Poetry package manager"
	@echo "  make install        Install dependencies with Poetry"
	@echo "  make install-dev    Install with dev dependencies"
	@echo "  make lock           Update poetry.lock file"
	@echo "  make export         Export requirements.txt from Poetry"
	@echo ""
	@echo "[Development - Single Container: API + Telegram Bot]"
	@echo "  make run            Run application on port 3000"
	@echo "  make run-dev        Run with auto-reload for development"
	@echo "  make test           Run pytest test suite"
	@echo "  make lint           Check code quality with ruff"
	@echo "  make format         Format code with black"
	@echo "  make clean          Remove Python cache and temp files"
	@echo ""
	@echo "[Docker - Single Container Deployment]"
	@echo "  make docker-build   Build Docker image with Poetry"
	@echo "  make docker-run     Run Docker container on port 3000"
	@echo "  make docker-push    Push to registry"
	@echo ""
	@echo "[Kubernetes Deployment]"
	@echo "  make k8s-deploy-dev     Deploy to dev (arash-api-dev.irisaprime.ir)"
	@echo "  make k8s-deploy-stage   Deploy to stage (arash-api-stage.irisaprime.ir)"
	@echo "  make k8s-deploy-prod    Deploy to prod (arash-api.irisaprime.ir)"
	@echo ""
	@echo "[Database Migrations - Alembic]"
	@echo "  make migrate-create MSG=\"message\"  Create new migration"
	@echo "  make migrate-up                     Apply all pending migrations"
	@echo "  make migrate-down                   Rollback one migration"
	@echo "  make migrate-status                 Show migration status"
	@echo ""
	@echo "[Database Management - PostgreSQL]"
	@echo "  make db-init        Initialize database tables"
	@echo "  make db-teams       List all teams"
	@echo "  make db-keys        List all API keys"
	@echo "  make db-usage       Show usage statistics"
	@echo ""
	@echo "[Quick Database Commands]"
	@echo "  make db-team-create NAME=\"TeamName\" [DESC=\"...\"] [DAILY=100] [MONTHLY=3000]"
	@echo "  make db-team-delete ID=<team_id> [FORCE=yes]"
	@echo "  make db-key-create TEAM=<id> NAME=\"KeyName\" [LEVEL=user|team_lead|admin]"
	@echo "  make db-key-revoke ID=<key_id> [PERMANENT=yes]"
	@echo ""
	@echo "Examples:"
	@echo "  make install"
	@echo "  make migrate-up"
	@echo "  make run"
	@echo "  make db-team-create NAME=\"Engineering\" DAILY=500 MONTHLY=15000"
	@echo "  make db-key-create TEAM=1 NAME=\"Production Key\" LEVEL=admin"
	@echo "  make docker-build"
	@echo "  make k8s-deploy-dev"
	@echo ""

# ============================================================================
# Poetry & Dependencies
# ============================================================================

install-poetry:
	@echo "[Poetry] Installing Poetry package manager..."
	curl -sSL https://install.python-poetry.org | python3 -
	@echo "[OK] Poetry installed. Add to PATH: export PATH=\"\$$HOME/.local/bin:\$$PATH\""

install:
	@echo "[Poetry] Installing dependencies..."
	poetry install --no-root
	@echo "[OK] Dependencies installed"

install-dev:
	@echo "[Poetry] Installing dependencies with dev tools..."
	poetry install --no-root
	@echo "[OK] All dependencies installed (including dev)"

lock:
	@echo "[Poetry] Updating poetry.lock..."
	poetry lock
	@echo "[OK] Lock file updated"

export:
	@echo "[Poetry] Exporting requirements.txt..."
	poetry export -f requirements.txt --output requirements.txt --without-hashes
	@echo "[OK] requirements.txt exported"

# ============================================================================
# Development (Single Container - Runs API + Telegram Bot)
# ============================================================================

run:
	@echo "[START] Starting Arash API Service (includes integrated Telegram bot)..."
	@echo "        API: http://localhost:3000"
	@echo "        Docs: http://localhost:3000/docs"
	@echo ""
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 3000

run-dev:
	@echo "[START] Starting in development mode with auto-reload..."
	@echo "        API: http://localhost:3000"
	@echo "        Docs: http://localhost:3000/docs"
	@echo ""
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload

test:
	@echo "[TEST] Running test suite..."
	poetry run pytest -v

lint:
	@echo "[LINT] Checking code quality with ruff..."
	poetry run ruff check app/ tests/
	@echo "[OK] Code quality check complete"

format:
	@echo "[FORMAT] Formatting code with black..."
	poetry run black app/ tests/
	@echo "[OK] Code formatted"

clean:
	@echo "[CLEAN] Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "[OK] Cleaned temporary files"

# ============================================================================
# Docker (Single Container with Poetry)
# ============================================================================

docker-build:
	@echo "[Docker] Building Docker image with Poetry..."
	docker build -t arash-external-api:latest .
	@echo "[OK] Docker image built: arash-external-api:latest"

docker-run:
	@echo "[Docker] Running Docker container on port 3000..."
	docker run --rm --env-file .env -p 3000:3000 arash-external-api:latest

docker-push:
	@echo "[Docker] Pushing to registry..."
	docker tag arash-external-api:latest repo3.lucidfirm.ir/primebot/arash-external-api:latest
	docker push repo3.lucidfirm.ir/primebot/arash-external-api:latest
	@echo "[OK] Image pushed to registry"

# ============================================================================
# Kubernetes Deployment
# ============================================================================

k8s-deploy-dev:
	@echo "[K8s] Deploying to development environment..."
	kubectl apply -f manifests/dev/
	@echo "[OK] Deployed to dev: https://arash-api-dev.irisaprime.ir"

k8s-deploy-stage:
	@echo "[K8s] Deploying to staging environment..."
	kubectl apply -f manifests/stage/
	@echo "[OK] Deployed to stage: https://arash-api-stage.irisaprime.ir"

k8s-deploy-prod:
	@echo "[K8s] Deploying to production environment..."
	@echo "[WARNING] This will deploy to PRODUCTION!"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] || (echo "[ABORT] Deployment cancelled" && exit 1)
	kubectl apply -f manifests/prod/
	@echo "[OK] Deployed to production: https://arash-api.irisaprime.ir"

# ============================================================================
# Database Migrations (Alembic)
# ============================================================================

migrate-create:
ifndef MSG
	@echo "[ERROR] MSG is required"
	@echo "Usage: make migrate-create MSG=\"description of changes\""
	@exit 1
endif
	@echo "[Migration] Creating new migration: $(MSG)"
	poetry run alembic revision --autogenerate -m "$(MSG)"
	@echo "[OK] Migration created"

migrate-up:
	@echo "[Migration] Applying pending migrations..."
	poetry run alembic upgrade head
	@echo "[OK] Migrations applied"

migrate-down:
	@echo "[Migration] Rolling back last migration..."
	poetry run alembic downgrade -1
	@echo "[OK] Migration rolled back"

migrate-status:
	@echo "[Migration] Current migration status:"
	poetry run alembic current
	@echo ""
	@echo "Migration history:"
	poetry run alembic history

# ============================================================================
# Database Management (API Keys & Teams)
# ============================================================================

db-init:
	@echo "[Database] Initializing database tables..."
	poetry run python scripts/manage_api_keys.py init
	@echo "[OK] Database initialized"

db-teams:
	@echo "[Database] Listing all teams..."
	@poetry run python scripts/manage_api_keys.py team list

db-keys:
	@echo "[Database] Listing all API keys..."
	@poetry run python scripts/manage_api_keys.py key list

db-usage:
	@echo "Usage: python scripts/manage_api_keys.py usage --team-id <ID> OR --key-id <ID>"
	@echo "Example: make db-usage TEAM=1"
	@echo ""
ifdef TEAM
	poetry run python scripts/manage_api_keys.py usage --team-id $(TEAM)
else ifdef KEY
	poetry run python scripts/manage_api_keys.py usage --key-id $(KEY)
else
	@echo "[ERROR] Specify TEAM=<id> or KEY=<id>"
endif

# ============================================================================
# Quick Database Operations
# ============================================================================

db-team-create:
ifndef NAME
	@echo "[ERROR] NAME is required"
	@echo "Usage: make db-team-create NAME=\"Team Name\" [DESC=\"...\"] [DAILY=100] [MONTHLY=3000]"
	@exit 1
endif
	@echo "[Database] Creating team: $(NAME)"
	poetry run python scripts/manage_api_keys.py team create "$(NAME)" \
		$(if $(DESC),--description "$(DESC)") \
		$(if $(DAILY),--daily-quota $(DAILY)) \
		$(if $(MONTHLY),--monthly-quota $(MONTHLY))

db-team-delete:
ifndef ID
	@echo "[ERROR] ID is required"
	@echo "Usage: make db-team-delete ID=<team_id> [FORCE=yes]"
	@exit 1
endif
	@echo "[Database] Deleting team ID: $(ID)"
	poetry run python scripts/manage_api_keys.py team delete $(ID) $(if $(FORCE),--force)

db-key-create:
ifndef TEAM
	@echo "[ERROR] TEAM is required"
	@echo "Usage: make db-key-create TEAM=<id> NAME=\"Key Name\" [LEVEL=user|team_lead|admin]"
	@exit 1
endif
ifndef NAME
	@echo "[ERROR] NAME is required"
	@echo "Usage: make db-key-create TEAM=<id> NAME=\"Key Name\" [LEVEL=user|team_lead|admin]"
	@exit 1
endif
	@echo "[Database] Creating API key: $(NAME) for team $(TEAM)"
	poetry run python scripts/manage_api_keys.py key create $(TEAM) "$(NAME)" \
		$(if $(LEVEL),--level $(LEVEL)) \
		$(if $(DESC),--description "$(DESC)") \
		$(if $(EXPIRES),--expires $(EXPIRES))

db-key-revoke:
ifndef ID
	@echo "[ERROR] ID is required"
	@echo "Usage: make db-key-revoke ID=<key_id> [PERMANENT=yes]"
	@exit 1
endif
	@echo "[Database] Revoking API key ID: $(ID)"
	poetry run python scripts/manage_api_keys.py key revoke $(ID) $(if $(PERMANENT),--permanent)
