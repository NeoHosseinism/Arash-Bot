# Makefile for Arash Messenger Bot v3.0
# Provides convenient commands for development and deployment

.PHONY: help install dev test clean run-service run-bot run-all stop docker-build docker-up docker-down logs format lint security check deploy

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
VENV := venv
VENV_BIN := $(VENV)/bin
PYTHON_VENV := $(VENV_BIN)/python
PIP_VENV := $(VENV_BIN)/pip

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

## help: Show this help message
help:
	@echo "$(GREEN)╔══════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║     Arash Messenger Bot v3.0 - Makefile Commands         ║$(NC)"
	@echo "$(GREEN)╚══════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Setup Commands:$(NC)"
	@echo "  $(BLUE)make install$(NC)        - Complete installation (venv + dependencies)"
	@echo "  $(BLUE)make setup$(NC)          - Run setup script"
	@echo "  $(BLUE)make env$(NC)            - Copy .env.example to .env"
	@echo ""
	@echo "$(YELLOW)Development Commands:$(NC)"
	@echo "  $(BLUE)make dev$(NC)            - Install dev dependencies"
	@echo "  $(BLUE)make run-service$(NC)    - Run FastAPI service"
	@echo "  $(BLUE)make run-bot$(NC)        - Run Telegram bot"
	@echo "  $(BLUE)make run-all$(NC)        - Run both service and bot (tmux/screen)"
	@echo "  $(BLUE)make stop$(NC)           - Stop all running services"
	@echo ""
	@echo "$(YELLOW)Code Quality:$(NC)"
	@echo "  $(BLUE)make format$(NC)         - Format code with black"
	@echo "  $(BLUE)make lint$(NC)           - Lint code with flake8 and mypy"
	@echo "  $(BLUE)make security$(NC)       - Run security checks with bandit"
	@echo "  $(BLUE)make check$(NC)          - Run all checks (format, lint, security)"
	@echo ""
	@echo "$(YELLOW)Testing:$(NC)"
	@echo "  $(BLUE)make test$(NC)           - Run all tests"
	@echo "  $(BLUE)make test-cov$(NC)       - Run tests with coverage report"
	@echo "  $(BLUE)make test-watch$(NC)     - Run tests in watch mode"
	@echo ""
	@echo "$(YELLOW)Docker:$(NC)"
	@echo "  $(BLUE)make docker-build$(NC)   - Build Docker images"
	@echo "  $(BLUE)make docker-up$(NC)      - Start services with Docker Compose"
	@echo "  $(BLUE)make docker-down$(NC)    - Stop Docker containers"
	@echo "  $(BLUE)make docker-logs$(NC)    - View Docker logs"
	@echo ""
	@echo "$(YELLOW)Maintenance:$(NC)"
	@echo "  $(BLUE)make clean$(NC)          - Clean temporary files and cache"
	@echo "  $(BLUE)make clean-all$(NC)      - Deep clean (including venv)"
	@echo "  $(BLUE)make logs$(NC)           - View application logs"
	@echo "  $(BLUE)make stats$(NC)          - Show service statistics"
	@echo ""
	@echo "$(YELLOW)Deployment:$(NC)"
	@echo "  $(BLUE)make deploy-check$(NC)   - Pre-deployment checks"
	@echo "  $(BLUE)make deploy$(NC)         - Deploy to production"
	@echo ""

## install: Complete installation with venv and dependencies
install: check-python
	@echo "$(GREEN)Installing Arash Messenger Bot...$(NC)"
	@$(PYTHON) -m venv $(VENV)
	@$(PIP_VENV) install --upgrade pip setuptools wheel
	@$(PIP_VENV) install -r requirements.txt
	@echo "$(GREEN)✓ Installation complete!$(NC)"
	@echo "$(YELLOW)Run 'make env' to create .env file$(NC)"

## check-python: Check if Python 3.9+ is installed
check-python:
	@which $(PYTHON) > /dev/null || (echo "$(RED)Python 3 not found!$(NC)" && exit 1)
	@$(PYTHON) -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" || \
		(echo "$(RED)Python 3.9+ required!$(NC)" && exit 1)
	@echo "$(GREEN)✓ Python version OK$(NC)"

## setup: Run setup script
setup:
	@chmod +x setup.sh
	@./setup.sh

## env: Copy .env.example to .env
env:
	@if [ -f .env ]; then \
		echo "$(YELLOW)⚠ .env already exists$(NC)"; \
	else \
		cp .env.example .env; \
		echo "$(GREEN)✓ .env created from template$(NC)"; \
		echo "$(YELLOW)⚠ Edit .env and set your tokens!$(NC)"; \
	fi

## dev: Install development dependencies
dev: install
	@$(PIP_VENV) install pytest pytest-asyncio pytest-cov black flake8 mypy bandit
	@echo "$(GREEN)✓ Dev dependencies installed$(NC)"

## run-service: Run FastAPI service
run-service:
	@echo "$(GREEN)Starting FastAPI service...$(NC)"
	@$(PYTHON_VENV) run_service.py

## run-bot: Run Telegram bot
run-bot:
	@echo "$(GREEN)Starting Telegram bot...$(NC)"
	@$(PYTHON_VENV) run_telegram_bot.py

## run-all: Run both service and bot (requires tmux or screen)
run-all:
	@if command -v tmux > /dev/null; then \
		echo "$(GREEN)Starting services with tmux...$(NC)"; \
		tmux new-session -d -s arash-bot "$(PYTHON_VENV) run_service.py"; \
		tmux split-window -h -t arash-bot "$(PYTHON_VENV) run_telegram_bot.py"; \
		tmux attach -t arash-bot; \
	elif command -v screen > /dev/null; then \
		echo "$(GREEN)Starting services with screen...$(NC)"; \
		screen -dmS arash-service bash -c "$(PYTHON_VENV) run_service.py"; \
		screen -dmS arash-bot bash -c "$(PYTHON_VENV) run_telegram_bot.py"; \
		echo "$(GREEN)Services started!$(NC)"; \
		echo "$(YELLOW)Attach with: screen -r arash-service$(NC)"; \
	else \
		echo "$(RED)Error: tmux or screen required for run-all$(NC)"; \
		echo "$(YELLOW)Install with: sudo apt install tmux$(NC)"; \
		exit 1; \
	fi

## stop: Stop all running services
stop:
	@echo "$(YELLOW)Stopping services...$(NC)"
	@pkill -f "run_service.py" || true
	@pkill -f "run_telegram_bot.py" || true
	@if command -v tmux > /dev/null; then \
		tmux kill-session -t arash-bot 2>/dev/null || true; \
	fi
	@if command -v screen > /dev/null; then \
		screen -S arash-service -X quit 2>/dev/null || true; \
		screen -S arash-bot -X quit 2>/dev/null || true; \
	fi
	@echo "$(GREEN)✓ Services stopped$(NC)"

## test: Run all tests
test:
	@echo "$(GREEN)Running tests...$(NC)"
	@$(PYTHON_VENV) -m pytest tests/ -v

## test-cov: Run tests with coverage
test-cov:
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	@$(PYTHON_VENV) -m pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report: htmlcov/index.html$(NC)"

## test-watch: Run tests in watch mode
test-watch:
	@echo "$(GREEN)Running tests in watch mode...$(NC)"
	@$(PYTHON_VENV) -m pytest tests/ -v -f

## format: Format code with black
format:
	@echo "$(GREEN)Formatting code...$(NC)"
	@$(PYTHON_VENV) -m black app/ telegram/ tests/ --line-length 100
	@echo "$(GREEN)✓ Code formatted$(NC)"

## lint: Lint code with flake8 and mypy
lint:
	@echo "$(GREEN)Linting code...$(NC)"
	@$(PYTHON_VENV) -m flake8 app/ telegram/ --max-line-length=100 --exclude=venv || true
	@$(PYTHON_VENV) -m mypy app/ --ignore-missing-imports || true
	@echo "$(GREEN)✓ Linting complete$(NC)"

## security: Run security checks
security:
	@echo "$(GREEN)Running security checks...$(NC)"
	@$(PYTHON_VENV) -m bandit -r app/ telegram/ -ll || true
	@echo "$(GREEN)✓ Security check complete$(NC)"

## check: Run all checks (format, lint, security)
check: format lint security
	@echo "$(GREEN)✓ All checks complete!$(NC)"

## clean: Clean temporary files and cache
clean:
	@echo "$(YELLOW)Cleaning temporary files...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "$(GREEN)✓ Cleaned$(NC)"

## clean-all: Deep clean including venv
clean-all: clean
	@echo "$(YELLOW)Deep cleaning (including venv)...$(NC)"
	@rm -rf $(VENV) 2>/dev/null || true
	@rm -rf logs/*.log 2>/dev/null || true
	@echo "$(GREEN)✓ Deep clean complete$(NC)"

## logs: View application logs
logs:
	@if [ -f logs/bot_service.log ]; then \
		tail -f logs/bot_service.log; \
	else \
		echo "$(RED)No log file found$(NC)"; \
	fi

## stats: Show service statistics
stats:
	@echo "$(GREEN)Service Statistics:$(NC)"
	@curl -s http://localhost:8001/stats | python3 -m json.tool || \
		echo "$(RED)Service not running or not accessible$(NC)"

## docker-build: Build Docker images
docker-build:
	@echo "$(GREEN)Building Docker images...$(NC)"
	@docker-compose build
	@echo "$(GREEN)✓ Docker images built$(NC)"

## docker-up: Start services with Docker Compose
docker-up:
	@echo "$(GREEN)Starting services with Docker Compose...$(NC)"
	@docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "$(YELLOW)View logs: make docker-logs$(NC)"

## docker-down: Stop Docker containers
docker-down:
	@echo "$(YELLOW)Stopping Docker containers...$(NC)"
	@docker-compose down
	@echo "$(GREEN)✓ Containers stopped$(NC)"

## docker-logs: View Docker logs
docker-logs:
	@docker-compose logs -f

## deploy-check: Pre-deployment checks
deploy-check:
	@echo "$(GREEN)Running pre-deployment checks...$(NC)"
	@echo "$(YELLOW)1. Checking environment file...$(NC)"
	@test -f .env || (echo "$(RED)✗ .env file missing$(NC)" && exit 1)
	@echo "$(GREEN)✓ .env exists$(NC)"
	@echo ""
	@echo "$(YELLOW)2. Checking required variables...$(NC)"
	@grep -q "TELEGRAM_BOT_TOKEN=" .env || (echo "$(RED)✗ TELEGRAM_BOT_TOKEN not set$(NC)" && exit 1)
	@grep -q "INTERNAL_API_KEY=" .env || (echo "$(RED)✗ INTERNAL_API_KEY not set$(NC)" && exit 1)
	@echo "$(GREEN)✓ Required variables set$(NC)"
	@echo ""
	@echo "$(YELLOW)3. Checking ENVIRONMENT setting...$(NC)"
	@grep "ENVIRONMENT=production" .env > /dev/null || echo "$(YELLOW)⚠ Not set to production$(NC)"
	@echo ""
	@echo "$(YELLOW)4. Running tests...$(NC)"
	@$(PYTHON_VENV) -m pytest tests/ -q || (echo "$(RED)✗ Tests failed$(NC)" && exit 1)
	@echo "$(GREEN)✓ Tests passed$(NC)"
	@echo ""
	@echo "$(YELLOW)5. Running security checks...$(NC)"
	@$(PYTHON_VENV) -m bandit -r app/ telegram/ -ll -q || true
	@echo ""
	@echo "$(GREEN)✓ Pre-deployment checks complete!$(NC)"

## deploy: Deploy to production
deploy: deploy-check
	@echo "$(GREEN)Deploying to production...$(NC)"
	@echo "$(YELLOW)This would typically:$(NC)"
	@echo "  1. Pull latest code from git"
	@echo "  2. Install dependencies"
	@echo "  3. Run migrations (if any)"
	@echo "  4. Restart services"
	@echo ""
	@echo "$(YELLOW)Customize this target for your deployment strategy$(NC)"

## install-service: Install systemd service (Linux only)
install-service:
	@echo "$(GREEN)Installing systemd service...$(NC)"
	@if [ ! -f /etc/systemd/system/arash-bot-api.service ]; then \
		sudo cp deployment/arash-bot-api.service /etc/systemd/system/; \
		sudo cp deployment/arash-bot-telegram.service /etc/systemd/system/; \
		sudo systemctl daemon-reload; \
		sudo systemctl enable arash-bot-api arash-bot-telegram; \
		echo "$(GREEN)✓ Services installed$(NC)"; \
		echo "$(YELLOW)Start with: sudo systemctl start arash-bot-api arash-bot-telegram$(NC)"; \
	else \
		echo "$(YELLOW)⚠ Services already installed$(NC)"; \
	fi

## service-start: Start systemd services
service-start:
	@sudo systemctl start arash-bot-api arash-bot-telegram
	@echo "$(GREEN)✓ Services started$(NC)"

## service-stop: Stop systemd services
service-stop:
	@sudo systemctl stop arash-bot-api arash-bot-telegram
	@echo "$(GREEN)✓ Services stopped$(NC)"

## service-status: Check systemd services status
service-status:
	@sudo systemctl status arash-bot-api arash-bot-telegram

## backup: Backup important files
backup:
	@echo "$(GREEN)Creating backup...$(NC)"
	@mkdir -p backups
	@tar -czf backups/backup-$(shell date +%Y%m%d-%H%M%S).tar.gz \
		--exclude=venv \
		--exclude=__pycache__ \
		--exclude=*.pyc \
		--exclude=.git \
		--exclude=logs \
		.
	@echo "$(GREEN)✓ Backup created in backups/$(NC)"

## requirements: Update requirements.txt
requirements:
	@echo "$(GREEN)Updating requirements.txt...$(NC)"
	@$(PIP_VENV) freeze > requirements.txt
	@echo "$(GREEN)✓ requirements.txt updated$(NC)"

## upgrade: Upgrade all dependencies
upgrade:
	@echo "$(GREEN)Upgrading dependencies...$(NC)"
	@$(PIP_VENV) install --upgrade pip
	@$(PIP_VENV) list --outdated
	@echo "$(YELLOW)Run 'pip install --upgrade <package>' to upgrade specific packages$(NC)"

## info: Show project information
info:
	@echo "$(GREEN)Project Information:$(NC)"
	@echo "  Name: Arash Messenger Bot"
	@echo "  Version: 3.0.0"
	@echo "  Python: $(shell $(PYTHON) --version)"
	@echo "  Venv: $(if $(wildcard $(VENV)),$(GREEN)Active$(NC),$(RED)Not found$(NC))"
	@echo "  Services: $(if $(shell pgrep -f run_service.py),$(GREEN)Running$(NC),$(RED)Stopped$(NC))"
	@echo ""