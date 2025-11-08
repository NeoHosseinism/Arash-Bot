# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Arash External API Service v1.1 - Enterprise-ready AI chatbot service with integrated Telegram bot, team-based access control, and multi-platform support. Built with FastAPI and PostgreSQL, supporting multiple AI models (GPT-5, Claude, Gemini, Grok, DeepSeek).

## Development Commands

### Setup
```bash
# Install dependencies (requires Poetry)
make install

# Configure environment
cp .env.example .env
# Edit .env with your configuration (DB credentials, bot tokens, etc.)

# Run database migrations
make migrate-up
```

### Running the Service
```bash
# Development mode (auto-reload, port 3000)
make run

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 3000
```

### Testing
```bash
# Run all tests
make test

# Run specific test file
poetry run pytest tests/test_api.py -v

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run only unit tests (skip integration)
poetry run pytest -m "not integration"
```

### Code Quality
```bash
# Check code quality
make lint

# Format code (Black)
make format

# Clean cache files
make clean
```

### Database Management
```bash
# Apply migrations
make migrate-up

# Create new migration
poetry run alembic revision --autogenerate -m "Description"

# Rollback last migration
poetry run alembic downgrade -1

# Check migration status
poetry run alembic current

# Create team
make db-team-create NAME="Engineering" DAILY=1000 MONTHLY=30000

# Create API key
make db-key-create TEAM=1 NAME="Admin Key" LEVEL=admin

# List teams and keys
make db-teams
make db-keys
```

## Architecture Overview

### Core Architecture Layers

**Entry Points:**
- `app/main.py` - FastAPI application with integrated Telegram bot (single container deployment)
- `run_service.py` - Minimal service runner (API only)
- `run_bot.py` - Minimal bot runner (Telegram only)

**API Layer (`app/api/`):**
- `routes.py` - Public API endpoints (message processing, sessions)
- `admin_routes.py` - Admin endpoints (teams, API keys, usage stats)
- `dependencies.py` - Authentication middleware (API key validation)

**Service Layer (`app/services/`):**
- `message_processor.py` - Core message processing logic
- `command_processor.py` - Command handling (/start, /help, /model, etc.)
- `session_manager.py` - Chat session management with rate limiting and team isolation
- `platform_manager.py` - Platform-specific configurations (Telegram vs Internal)
- `ai_client.py` - AI service communication (httpx-based)
- `api_key_manager.py` - Database-backed API key authentication (SHA256 hashing)
- `usage_tracker.py` - Usage logging and quota enforcement

**Core Layer (`app/core/`):**
- `config.py` - Pydantic Settings V2 configuration (environment-based)
- `constants.py` - System constants (models, platforms, rate limits)
- `name_mapping.py` - Model ID to friendly name mapping
- `database_init.py` - Database initialization with Alembic

**Data Layer (`app/models/`):**
- `database.py` - SQLAlchemy models (Team, APIKey, UsageLog)
- `schemas.py` - Pydantic request/response schemas
- `session.py` - In-memory session model (not persisted)

**Telegram Bot (`telegram_bot/`):**
- `bot.py` - python-telegram-bot integration, forwards requests to FastAPI

**Database Migrations (`alembic/versions/`):**
- Managed by Alembic, run migrations with `make migrate-up`

### Key Design Patterns

**Team-Based Isolation:**
- Session keys include team_id to prevent collision: `platform:team_id:chat_id`
- All database queries filter by team_id for complete data isolation
- API keys are team-scoped with hierarchical access levels (User, Team Lead, Admin)

**Platform-Specific Configuration:**
- Telegram (Public): Gemini 2.0 Flash default, 20 msg/min, 10 msg history
- Internal (Private): GPT-5 Chat default, 60 msg/min, 30 msg history, requires API key auth

**API Versioning:**
- All endpoints prefixed with `/api/v1/` for future compatibility
- Health check at `/health` (unversioned for monitoring)

**Security Architecture:**
- API keys hashed with SHA256 (never stored in plain text)
- Database-only authentication (no legacy fallback)
- Session key isolation prevents team data leakage
- Input validation via Pydantic models

**Environment Configuration:**
- Generic variables set by DevOps per deployment (not per-environment duplicates)
- `ENVIRONMENT` (dev/stage/prod) - used for logging/monitoring only
- Application behavior controlled by specific variables: `LOG_LEVEL`, `ENABLE_API_DOCS`, `CORS_ORIGINS`
- Each deployment gets only the credentials it needs (security)

## Important Implementation Details

### Session Management
- Sessions are in-memory (not persisted to database)
- Session key format: `platform:team_id:chat_id` (team_id ensures isolation)
- Rate limiting tracked per session with sliding window (in `session_manager.py:61`)
- Periodic cleanup every 5 minutes (see `app/main.py:169`)

### Authentication Flow
1. API request arrives with `X-API-Key` header
2. `dependencies.py:verify_api_key()` validates against database
3. Key hash is computed (SHA256) and matched in `api_keys` table
4. Team, access level, and quota checked
5. Request context includes `team_id`, `api_key_id`, `access_level`

### Database Schema
- `teams` - Team info with daily/monthly quotas
- `api_keys` - API keys with SHA256 hashes, team association, access levels
- `usage_logs` - Usage tracking (timestamp, team_id, api_key_id, model, tokens, cost)

### AI Service Integration
- AI requests handled by `ai_client.py` using httpx
- Model name mapping in `name_mapping.py` (internal ID to friendly name)
- Supports multiple AI providers via unified interface

### Telegram Bot Integration
- Single container deployment: bot runs as asyncio task inside FastAPI (see `app/main.py:34`)
- Bot forwards requests to local FastAPI endpoint (`http://localhost:3000`)
- Commands handled by `command_processor.py`, messages by `message_processor.py`

## Common Development Scenarios

### Adding a New API Endpoint
1. Define Pydantic schema in `app/models/schemas.py`
2. Add route to `app/api/routes.py` (public) or `app/api/admin_routes.py` (admin)
3. Use `get_api_key_info()` dependency for authentication
4. Add business logic in appropriate service (`app/services/`)
5. Update tests in `tests/test_api.py`

### Adding a New Database Model
1. Add SQLAlchemy model to `app/models/database.py`
2. Create migration: `poetry run alembic revision --autogenerate -m "Add new table"`
3. Review generated migration in `alembic/versions/`
4. Apply migration: `make migrate-up`
5. Update schemas in `app/models/schemas.py` if needed

### Adding a New Command
1. Add command logic to `app/services/command_processor.py`
2. Update platform config in `app/core/config.py` (add to TELEGRAM_COMMANDS or INTERNAL_COMMANDS)
3. Add command handler in `telegram_bot/bot.py` if Telegram-specific
4. Update tests in `tests/test_commands.py`

### Changing AI Model Configuration
1. Update model list in `.env` (TELEGRAM_MODELS, INTERNAL_MODELS)
2. Update default model if needed (TELEGRAM_DEFAULT_MODEL, INTERNAL_DEFAULT_MODEL)
3. Add name mapping in `app/core/name_mapping.py` if new provider
4. Test with `/models` command to verify availability

## Testing Notes

- Pytest configuration in `pytest.ini` and `pyproject.toml`
- Test markers: `unit`, `integration`, `slow`, `ai_service`, `telegram`
- Mock fixtures in `tests/conftest.py`
- Run single test: `poetry run pytest tests/test_api.py::test_message_endpoint -v`
- Async tests automatically handled with `asyncio_mode = auto`

## Deployment

### Docker
```bash
# Build image
make docker-build

# Run container (requires .env file)
make docker-run
```

### Kubernetes
- Manifests in `manifests/{dev,stage,prod}/`
- Deployment includes ConfigMap (non-sensitive config) and Secret (credentials)
- Single container runs both API and Telegram bot (`RUN_TELEGRAM_BOT=true`)
- Apply with: `kubectl apply -f manifests/dev/`

## Configuration Management

All configuration uses generic variables set by DevOps per deployment:

**Application Behavior:**
- `LOG_LEVEL` - DEBUG/INFO/WARNING (set per deployment)
- `ENABLE_API_DOCS` - true/false (typically false in prod)
- `CORS_ORIGINS` - "*" or specific domains

**Infrastructure:**
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- `REDIS_URL` (optional)
- `AI_SERVICE_URL`
- `TELEGRAM_BOT_TOKEN`, `INTERNAL_API_KEY`

**Environment Identifier:**
- `ENVIRONMENT` (dev/stage/prod) - Used only for logging/monitoring
- Code can check `settings.is_production`, `settings.is_development`, `settings.is_staging`

Each deployment only has credentials it needs (no prod credentials in dev).

## Code Style

- Line length: 100 characters (enforced by Black)
- Python 3.11+ required
- Use type hints (checked by mypy, but not strictly enforced)
- Ruff for linting (pycodestyle, pyflakes, isort, flake8-bugbear)
- Async/await for all I/O operations
- SQLAlchemy for database, Pydantic for validation

## Security Considerations

- Never log API keys or tokens (use masking functions in `name_mapping.py`)
- All API endpoints require authentication except `/health`
- Team isolation enforced at session and database levels
- Input validation via Pydantic prevents injection attacks
- Rate limiting prevents abuse
- CORS configured per environment (strict in production)
- Database migrations should never contain sensitive data
