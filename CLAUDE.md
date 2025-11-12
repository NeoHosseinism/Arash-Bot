# Arash Bot - Development Guide

**Comprehensive development documentation for Arash External API Service v1.1**

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Entry Points](#entry-points)
4. [Project Structure](#project-structure)
5. [Development Setup](#development-setup)
6. [Testing Best Practices](#testing-best-practices)
7. [Database Management](#database-management)
8. [API Development](#api-development)
9. [Code Quality](#code-quality)
10. [Deployment](#deployment)

---

## Project Overview

Arash Bot is a multi-platform AI chatbot service with team-based access control, supporting:
- **Telegram Bot Integration** - Public users with rate limiting
- **REST API** - Team-based access with API keys
- **Multi-Model AI Support** - GPT, Claude, Gemini, Grok, DeepSeek
- **Session Management** - Conversation history and context tracking
- **Usage Tracking** - Quota management and analytics

**Tech Stack:**
- FastAPI (async web framework)
- PostgreSQL (teams, API keys, usage logs)
- SQLAlchemy + Alembic (ORM and migrations)
- Python Telegram Bot (Telegram integration)
- Poetry (dependency management)
- Docker + Kubernetes (deployment)

---

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Entry Points                             │
│  • run_telegram_bot.py  - Standalone Telegram bot           │
│  • run_service.py       - FastAPI service (API + bot)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Application                        │
│  • app/main.py            - Application factory             │
│  • app/api/routes.py      - Public chat endpoint            │
│  • app/api/admin_routes.py - Team management (admin)        │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│   Core Services          │   │   External Services      │
│  • MessageProcessor      │   │  • AI Service (HTTP)     │
│  • SessionManager        │   │  • PostgreSQL DB         │
│  • PlatformManager       │   │                          │
│  • UsageTracker          │   │                          │
└──────────────────────────┘   └──────────────────────────┘
```

### Data Flow

```
Client Request
    → Authentication (API Key or Telegram Token)
    → Platform Detection (team.platform_name)
    → Session Lookup/Creation
    → Message Processing
    → AI Service Call (with conversation history)
    → Response Generation
    → Usage Logging
    → Response to Client
```

---

## Entry Points

### 1. `run_telegram_bot.py` (Standalone Telegram Bot)

**Purpose:** Run the Telegram bot independently without the FastAPI service.

```python
# Usage
python run_telegram_bot.py
```

**When to use:**
- Development/testing of Telegram bot features only
- Running bot separately from API service
- Legacy mode (before integration into main app)

**Note:** In production, the bot runs integrated within `app/main.py` when `RUN_TELEGRAM_BOT=true`.

### 2. `run_service.py` (FastAPI Service)

**Purpose:** Primary entry point for production - runs FastAPI service with optional integrated Telegram bot.

```python
# Usage
python run_service.py

# Or via Makefile
make run
make run-dev  # With auto-reload
```

**Features:**
- FastAPI REST API (port 3000)
- Integrated Telegram bot (background asyncio task)
- Database migrations on startup
- Health checks and periodic cleanup
- CORS middleware
- Global exception handling

**Environment Control:**
```bash
RUN_TELEGRAM_BOT=true   # Run bot integrated with API
RUN_TELEGRAM_BOT=false  # API only (no bot)
```

---

## Project Structure

```
Arash-Bot/
├── app/                          # Main application package
│   ├── api/                      # API routes
│   │   ├── routes.py            # Public chat endpoint
│   │   ├── admin_routes.py      # Admin team management
│   │   └── dependencies.py      # Auth dependencies
│   ├── core/                     # Core configuration
│   │   ├── config.py            # Settings (Pydantic)
│   │   ├── constants.py         # Constants and enums
│   │   ├── database.py          # Database initialization
│   │   └── name_mapping.py      # AI model name mappings
│   ├── models/                   # Data models
│   │   ├── database.py          # SQLAlchemy models
│   │   └── schemas.py           # Pydantic schemas
│   ├── services/                 # Business logic
│   │   ├── ai_service.py        # AI service integration
│   │   ├── api_key_manager.py   # API key management
│   │   ├── message_processor.py # Message handling
│   │   ├── platform_manager.py  # Platform configuration
│   │   ├── session_manager.py   # Session state management
│   │   └── usage_tracker.py     # Usage logging
│   ├── utils/                    # Utilities
│   │   ├── logging_setup.py     # Logging configuration
│   │   └── parsers.py           # Text parsing utilities
│   └── main.py                   # FastAPI app factory
│
├── telegram_bot/                 # Telegram bot implementation
│   ├── bot.py                   # Main bot logic
│   └── handlers.py              # Message/command handlers
│
├── tests/                        # Test suite
│   ├── conftest.py              # Pytest fixtures
│   ├── test_api.py              # API endpoint tests
│   ├── test_comprehensive.py   # Integration tests
│   ├── test_sessions.py         # Session management tests
│   ├── test_ai_service.py       # AI service tests
│   └── test_logging.py          # Logging tests
│
├── scripts/                      # Utility scripts
│   └── manage_api_keys.py       # CLI for API key management
│
├── alembic/                      # Database migrations
│   ├── versions/                # Migration files
│   └── env.py                   # Migration environment
│
├── manifests/                    # Kubernetes manifests
│   ├── dev/                     # Development environment
│   ├── stage/                   # Staging environment
│   └── prod/                    # Production environment
│
├── run_telegram_bot.py           # Telegram bot entry point
├── run_service.py               # FastAPI service entry point
├── Dockerfile                   # Multi-stage Docker build
├── Makefile                     # Development automation
├── pyproject.toml               # Poetry dependencies
├── pytest.ini                   # Pytest configuration
└── README.md                    # Project documentation
```

---

## Development Setup

### Prerequisites

- Python 3.11+
- Poetry 1.8+
- PostgreSQL 14+
- Docker (for containerized deployment)

### Initial Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd Arash-Bot

# 2. Install dependencies
poetry install

# 3. Configure environment
cp .env.example .env
# Edit .env with your database, AI service URL, and API keys

# 4. Initialize database
make migrate-up

# 5. Create admin API key (set in .env)
export SUPER_ADMIN_API_KEYS="your-admin-key-here"

# 6. Create first team
make db-team-create NAME="Internal-BI" DAILY=5000 MONTHLY=100000

# 7. Start development server
make run-dev
```

### Environment Variables

**Required:**
```bash
DB_HOST=localhost
DB_PORT=5432
DB_USER=arash
DB_PASSWORD=***
DB_NAME=arash_db
AI_SERVICE_URL=https://your-ai-service.com
SUPER_ADMIN_API_KEYS=admin_key_1,admin_key_2
```

**Telegram (Optional):**
```bash
TELEGRAM_BOT_TOKEN=***
TELEGRAM_SERVICE_KEY=***
RUN_TELEGRAM_BOT=true
```

**Runtime:**
```bash
ENVIRONMENT=development
LOG_LEVEL=INFO
LOG_TIMESTAMP=iran  # iran, utc, none
ENABLE_API_DOCS=true
API_HOST=0.0.0.0
API_PORT=3000
```

---

## Testing Best Practices

### Test Organization

**Good Test Structure:**
- `test_api.py` - API endpoint tests (378 lines)
- `test_sessions.py` - Session management tests (414 lines)
- `test_comprehensive.py` - Integration tests (448 lines)
- `test_ai_service.py` - AI service integration tests (278 lines)
- `test_logging.py` - Logging functionality tests (206 lines)

**Avoid:**
- Empty test files (removed `test_commands.py` with 0 lines)
- "Island" tests (small isolated files with 1-2 tests)
- Tests without clear purpose or scope

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/test_api.py -v

# Run tests with markers
poetry run pytest -m "not slow"  # Skip slow tests
poetry run pytest -m "integration"  # Run only integration tests
```

### Test Fixtures

Located in `tests/conftest.py`:
- `test_client` - FastAPI test client
- `test_db` - Test database session
- `mock_ai_service` - Mocked AI service responses

---

## Database Management

### Migrations with Alembic

```bash
# Create new migration
make migrate-create MSG="Add new column to teams table"

# Apply migrations
make migrate-up

# Rollback last migration
make migrate-down

# Check migration status
make migrate-status
```

### Manual Database Operations

```bash
# PostgreSQL connection
psql -h localhost -U arash -d arash_db

# List all tables
\dt

# View teams
SELECT * FROM teams;

# View API keys (hashed)
SELECT id, key_prefix, team_id, is_active FROM api_keys;
```

### Team and API Key Management

```bash
# List all teams
make db-teams

# Create team
make db-team-create NAME="External-Marketing" DAILY=2000 MONTHLY=50000

# List all API keys
make db-keys

# Create API key for team
make db-key-create TEAM=1 NAME="Production Key" LEVEL=user
```

---

## API Development

### Adding New Endpoints

**Public Endpoints** (all valid API keys):
- Add to `app/api/routes.py`
- Use `require_chat_access` dependency
- Return `BotResponse` schema

**Admin Endpoints** (super admin only):
- Add to `app/api/admin_routes.py`
- Use `require_admin_access` dependency
- Create custom response schemas

### Request/Response Schemas

All schemas defined in `app/models/schemas.py`:

**Best Practices:**
- Use `Field(...)` for required fields
- Use `Optional[T] = Field(None)` for optional fields
- Add `examples` for OpenAPI docs
- Add clear descriptions for all fields

**Example:**
```python
class MyRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"field": "value"}]
        }
    )

    required_field: str = Field(
        ...,
        description="This field is required",
        examples=["example_value"]
    )
    optional_field: Optional[int] = Field(
        None,
        description="This field is optional",
        examples=[42, None]
    )
```

### Authentication

**Two-tier access control:**

1. **Super Admin** (environment-based):
   - Defined in `SUPER_ADMIN_API_KEYS` env var
   - NOT stored in database
   - Full access to admin endpoints

2. **Team API Keys** (database-based):
   - Stored in `api_keys` table (hashed)
   - Linked to teams
   - Access to public chat endpoints only

---

## Code Quality

### Linting and Formatting

```bash
# Check code quality
make lint

# Auto-format code
make format

# Manual linting
poetry run ruff check app/ tests/

# Manual formatting
poetry run black app/ tests/
```

### Code Style Guidelines

- **Line length:** 100 characters (black + ruff)
- **Import order:** stdlib → third-party → local (ruff isort)
- **Type hints:** Use where beneficial, not required everywhere
- **Docstrings:** Required for public functions/classes
- **Comments:** Explain "why", not "what"

### Pre-commit Checklist

Before committing:
1. ✅ Run `make lint` (no errors)
2. ✅ Run `make test` (all tests pass)
3. ✅ Run `make format` (code formatted)
4. ✅ Update tests if adding new features
5. ✅ Update docs if changing APIs

---

## Deployment

### Docker Build

```bash
# Build image
make docker-build

# Run container
make docker-run

# Build with custom tags
docker build -t arash-bot:v1.1.0 .
docker build -t arash-bot:latest .
```

### Kubernetes Deployment

```bash
# Development
kubectl apply -f manifests/dev/

# Staging
kubectl apply -f manifests/stage/

# Production
kubectl apply -f manifests/prod/

# Check deployment status
kubectl get pods -n arash-bot
kubectl logs -f deployment/arash-bot -n arash-bot
```

### Environment-Specific Configuration

Each environment (dev/stage/prod) has separate:
- ConfigMap for environment variables
- Secret for sensitive data
- Ingress for external access
- Resource limits (CPU/memory)

---

## Additional Resources

- **API Documentation:** http://localhost:3000/docs (when running locally)
- **Project Roadmap:** See README.md
- **Issue Tracker:** GitHub Issues
- **Architecture Diagrams:** See README.md (Mermaid diagrams)

---

**Last Updated:** January 2025 | **Version:** 1.1.0
