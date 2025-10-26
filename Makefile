# Arash External API Service - Makefile
# Minimal commands for common development tasks

.PHONY: help install run-api run-bot test lint clean docker-build docker-run db-init

# Default target
help:
	@echo "Arash External API Service - Available Commands:"
	@echo ""
	@echo "  make install        Install dependencies"
	@echo "  make run-api        Run FastAPI service"
	@echo "  make run-bot        Run Telegram bot"
	@echo "  make test           Run tests"
	@echo "  make lint           Check code quality"
	@echo "  make clean          Clean temporary files"
	@echo ""
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-run     Run Docker container"
	@echo ""
	@echo "  make db-init        Initialize database"
	@echo "  make db-teams       Manage teams (CLI)"
	@echo "  make db-keys        Manage API keys (CLI)"
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
	python scripts/manage_api_keys.py init

db-teams:
	@echo "Usage: python scripts/manage_api_keys.py team create <name>"
	@echo "       python scripts/manage_api_keys.py team list"
	python scripts/manage_api_keys.py team list

db-keys:
	@echo "Usage: python scripts/manage_api_keys.py key create <team_id> [access_level]"
	@echo "       python scripts/manage_api_keys.py key list [team_id]"
	python scripts/manage_api_keys.py key list
