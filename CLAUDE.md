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
11. [Architecture Decision Records](#architecture-decision-records)

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
- uv (ultra-fast dependency management)
- Docker + Kubernetes (deployment)

---

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Entry Point                              │
│  • app/main.py          - Unified entry point               │
│    └─ RUN_TELEGRAM_BOT env controls integrated bot          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Application                        │
│  • app/main.py            - Application factory             │
│  • app/api/routes.py      - Public chat endpoint            │
│  • app/api/admin_routes.py - Team management (admin)        │
│  • Integrated Telegram Bot - Background asyncio task        │
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

The application has a **unified entry point** through `app/main.py`, which runs the FastAPI service with optional integrated Telegram bot (controlled by `RUN_TELEGRAM_BOT` environment variable).

### Running the Application

```bash
# Production mode
python -m app.main

# Development mode with auto-reload
python -m app.main --reload

# Or via Makefile (recommended)
make run          # Production mode
make run-dev      # Development with auto-reload
```

### Features

- FastAPI REST API (port 3000)
- Integrated Telegram bot (controlled by `RUN_TELEGRAM_BOT` environment variable)
- Database migrations on startup
- Health checks and periodic cleanup
- CORS middleware
- Global exception handling
- Auto-reload support for development

### Telegram Bot Control

The Telegram bot is controlled **automatically via environment variable**:

```bash
# In your .env file:
RUN_TELEGRAM_BOT=true     # Service with integrated bot
RUN_TELEGRAM_BOT=false    # Service only (no bot)

# Then run:
python -m app.main
```

The bot runs as an integrated background task within the FastAPI service when enabled. No separate process or command-line argument needed.

### Docker & Kubernetes

The Dockerfile and Kubernetes manifests use the same entry point:

```bash
# Dockerfile CMD
python -m uvicorn app.main:app --host 0.0.0.0 --port 3000
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
├── Dockerfile                   # Multi-stage Docker build
├── Makefile                     # Development automation
├── pyproject.toml               # uv dependencies
├── pytest.ini                   # Pytest configuration
└── README.md                    # Project documentation
```

---

## Development Setup

### Prerequisites

- Python 3.11+
- uv 0.8+
- PostgreSQL 14+
- Docker (for containerized deployment)

### Initial Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd Arash-Bot

# 2. Install dependencies
uv sync --all-extras

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
uv run pytest --cov=app --cov-report=html

# Run specific test file
uv run pytest tests/test_api.py -v

# Run tests with markers
uv run pytest -m "not slow"  # Skip slow tests
uv run pytest -m "integration"  # Run only integration tests
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

### Important Response Field Behaviors

#### total_message_count Field

The `total_message_count` field in `BotResponse` and session-related responses tracks the total number of **conversation messages** stored in the database.

**What is counted:**
- ✅ User chat messages (text sent to AI)
- ✅ AI assistant responses

**What is NOT counted:**
- ❌ Commands (e.g., `/model`, `/help`, `/clear`, `/status`)
- ❌ Command responses

**Key Characteristics:**
- **Persistence:** Survives `/clear` command (messages marked as cleared but remain in DB)
- **Purpose:** Analytics, conversation depth tracking, usage statistics
- **Calculation:** Direct count from `messages` table in database

**Implementation:**
```python
# In message_processor.py:176-185
session.total_message_count = (
    db.query(func.count(Message.id))
    .filter(
        Message.platform == platform_name,
        Message.user_id == user_id,
        Message.team_id == team_id if team_id else Message.team_id.is_(None),
    )
    .scalar()
    or 0
)
```

**Example Response:**
```json
{
  "success": true,
  "response": "مدل شما به GPT-4 تغییر کرد.",
  "model": "GPT-4",
  "total_message_count": 10  // Excludes the /model command just executed
}
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
uv run ruff check app/ tests/

# Manual formatting
uv run black app/ tests/
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

---

## Architecture Decision Records

### Overview

We maintain Architecture Decision Records (ADRs) to document significant architectural and design decisions made throughout the project lifecycle.

**Location:** [`docs/adr/`](docs/adr/)

### Why ADRs?

- **Historical Context:** Understand why decisions were made
- **Knowledge Transfer:** Onboard new team members faster
- **Avoid Repetition:** Don't revisit settled debates
- **Track Evolution:** See how architecture evolved over time

### Key Decisions

| ADR | Title | Status | Date | Impact |
|-----|-------|--------|------|--------|
| [001](docs/adr/001-dependency-management-uv.md) | Migration from Poetry to uv | Accepted | 2025-01-14 | High |
| [002](docs/adr/002-test-coverage-strategy.md) | Test Coverage Improvement Strategy | Accepted | 2025-01-14 | Medium |

### How to Use

- **Read ADRs:** Understand past decisions before proposing changes
- **Create ADRs:** Document significant architectural choices
- **Update ADRs:** Keep records current with implementation
- **Reference ADRs:** Link to ADRs in code comments and PRs

**Full documentation:** See [docs/adr/README.md](docs/adr/README.md)

---
