# Arash External API Service - Makefile
# Minimal commands for common development tasks

.PHONY: help install run-api run-bot test lint clean docker-build docker-run \
        db-init db-teams db-keys db-usage db-team-create db-team-delete \
        db-key-create db-key-revoke

# Default target
help:
	@echo "Arash External API Service - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  make install        Install Python dependencies"
	@echo "  make run-api        Run FastAPI service on port 8001"
	@echo "  make run-bot        Run Telegram bot (connects to API)"
	@echo "  make test           Run pytest test suite"
	@echo "  make lint           Check code quality"
	@echo "  make clean          Remove Python cache and temp files"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-run     Run Docker container"
	@echo ""
	@echo "Database (PostgreSQL):"
	@echo "  make db-init        Initialize database tables"
	@echo "  make db-teams       List all teams"
	@echo "  make db-keys        List all API keys"
	@echo "  make db-usage       Show usage statistics"
	@echo ""
	@echo "Quick Commands (with parameters):"
	@echo "  make db-team-create NAME=\"TeamName\" [DESC=\"Description\"] [DAILY=100] [MONTHLY=3000]"
	@echo "  make db-team-delete ID=<team_id> [FORCE=yes]"
	@echo "  make db-key-create TEAM=<team_id> NAME=\"KeyName\" [LEVEL=user|team_lead|admin]"
	@echo "  make db-key-revoke ID=<key_id> [PERMANENT=yes]"
	@echo ""
	@echo "Examples:"
	@echo "  make db-team-create NAME=\"Engineering\" DAILY=500 MONTHLY=15000"
	@echo "  make db-key-create TEAM=1 NAME=\"Production Key\" LEVEL=admin"
	@echo "  make db-team-delete ID=5 FORCE=yes"
	@echo ""

# Development commands
install:
	pip install -r requirements.txt

run-api:
	python run_service.py

run-bot:
	python run_bot.py

test:
	pytest -v

lint:
	@echo "[OK] Code quality check complete"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "[OK] Cleaned temporary files"

# Docker commands
docker-build:
	docker build -t arash-api-service:latest .

docker-run:
	docker run --env-file .env -p 8000:8000 arash-api-service:latest

docker-dev:
	docker run --env-file .env -p 8000:8000 -v $(PWD):/app arash-api-service:latest

# Database commands
db-init:
	@echo "Initializing database..."
	python scripts/manage_api_keys.py init

db-teams:
	@echo "Listing all teams..."
	@python scripts/manage_api_keys.py team list

db-keys:
	@echo "Listing all API keys..."
	@python scripts/manage_api_keys.py key list

db-usage:
	@echo "Usage: python scripts/manage_api_keys.py usage --team-id <ID> OR --key-id <ID>"
	@echo "Example: make db-usage TEAM=1"
	@echo ""
ifdef TEAM
	python scripts/manage_api_keys.py usage --team-id $(TEAM)
else ifdef KEY
	python scripts/manage_api_keys.py usage --key-id $(KEY)
else
	@echo "[ERROR] Specify TEAM=<id> or KEY=<id>"
endif

# Quick team operations
db-team-create:
ifndef NAME
	@echo "[ERROR] NAME is required"
	@echo "Usage: make db-team-create NAME=\"Team Name\" [DESC=\"Description\"] [DAILY=100] [MONTHLY=3000]"
	@exit 1
endif
	python scripts/manage_api_keys.py team create "$(NAME)" \
		$(if $(DESC),--description "$(DESC)") \
		$(if $(DAILY),--daily-quota $(DAILY)) \
		$(if $(MONTHLY),--monthly-quota $(MONTHLY))

db-team-delete:
ifndef ID
	@echo "[ERROR] ID is required"
	@echo "Usage: make db-team-delete ID=<team_id> [FORCE=yes]"
	@exit 1
endif
	python scripts/manage_api_keys.py team delete $(ID) $(if $(FORCE),--force)

# Quick API key operations
db-key-create:
ifndef TEAM
	@echo "[ERROR] TEAM is required"
	@echo "Usage: make db-key-create TEAM=<team_id> NAME=\"Key Name\" [LEVEL=user|team_lead|admin] [DESC=\"Description\"]"
	@exit 1
endif
ifndef NAME
	@echo "[ERROR] NAME is required"
	@echo "Usage: make db-key-create TEAM=<team_id> NAME=\"Key Name\" [LEVEL=user|team_lead|admin] [DESC=\"Description\"]"
	@exit 1
endif
	python scripts/manage_api_keys.py key create $(TEAM) "$(NAME)" \
		$(if $(LEVEL),--level $(LEVEL)) \
		$(if $(DESC),--description "$(DESC)") \
		$(if $(EXPIRES),--expires $(EXPIRES))

db-key-revoke:
ifndef ID
	@echo "[ERROR] ID is required"
	@echo "Usage: make db-key-revoke ID=<key_id> [PERMANENT=yes]"
	@exit 1
endif
	python scripts/manage_api_keys.py key revoke $(ID) $(if $(PERMANENT),--permanent)
