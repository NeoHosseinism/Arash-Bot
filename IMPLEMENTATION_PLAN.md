# Arash External API Service - Comprehensive Implementation Plan

## Executive Summary

Build an enterprise-ready AI chatbot service that supports multiple platforms (Telegram public bot + Private API) with team-based access control, usage tracking, webhook notifications, and database-backed API key management.

**Tech Stack:**
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with Alembic migrations
- **Telegram**: python-telegram-bot
- **External AI**: HTTP API (model-agnostic)
- **Deployment**: Docker + Kubernetes

**Core Metrics:** ~4,500 lines of Python code across 27 modules

---

## 1. Project Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                  │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Integrated Services                  │  │
│  │  ┌─────────────────┐  ┌────────────────────────┐  │  │
│  │  │  Telegram Bot   │  │   REST API (v1)       │  │  │
│  │  │  (Public)       │  │   /api/v1/*           │  │  │
│  │  │  - Commands     │  │   - /chat             │  │  │
│  │  │  - Message      │  │   - /admin/*          │  │  │
│  │  │    handling     │  │   (Authentication     │  │  │
│  │  │                 │  │    required)          │  │  │
│  │  └────────┬────────┘  └──────────┬─────────────┘  │  │
│  │           │                       │                │  │
│  │           └───────┬───────────────┘                │  │
│  │                   │                                │  │
│  │         ┌─────────▼─────────────┐                  │  │
│  │         │  Message Processor    │                  │  │
│  │         │  - Platform detection │                  │  │
│  │         │  - Command routing    │                  │  │
│  │         │  - Session management │                  │  │
│  │         └─────────┬─────────────┘                  │  │
│  │                   │                                │  │
│  │         ┌─────────▼─────────────┐                  │  │
│  │         │   AI Service Client   │                  │  │
│  │         │   (HTTP)              │                  │  │
│  │         └─────────┬─────────────┘                  │  │
│  └───────────────────┼─────────────────────────────────┘  │
│                      │                                    │
│  ┌───────────────────▼─────────────────────────────────┐  │
│  │              Support Services                       │  │
│  │  - Session Manager (in-memory)                      │  │
│  │  - Platform Manager (telegram/internal configs)    │  │
│  │  - API Key Manager (DB-backed auth)                │  │
│  │  - Usage Tracker (DB logging)                      │  │
│  │  - Webhook Client (async notifications)            │  │
│  │  - Command Processor (special commands)            │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
      ┌───────▼────────┐      ┌────────▼──────────┐
      │   PostgreSQL   │      │   External AI     │
      │   - Teams      │      │   Service         │
      │   - API Keys   │      │   (HTTP API)      │
      │   - Usage Logs │      │                   │
      └────────────────┘      └───────────────────┘
```

### 1.2 Directory Structure

```
Arash-Bot/
├── app/
│   ├── api/                      # API routes
│   │   ├── routes.py             # Public endpoints (/chat, /sessions)
│   │   ├── admin_routes.py       # Admin endpoints (/admin/*)
│   │   └── dependencies.py       # Auth dependencies
│   ├── core/                     # Core configuration
│   │   ├── config.py             # Pydantic Settings
│   │   ├── constants.py          # Constants
│   │   ├── name_mapping.py       # Model name mappings
│   │   └── database_init.py      # DB initialization
│   ├── models/                   # Data models
│   │   ├── database.py           # SQLAlchemy models (Team, APIKey, UsageLog)
│   │   ├── schemas.py            # Pydantic models (request/response)
│   │   └── session.py            # Session model (in-memory)
│   ├── services/                 # Business logic
│   │   ├── ai_client.py          # AI service HTTP client
│   │   ├── api_key_manager.py    # API key CRUD + validation
│   │   ├── command_processor.py  # Special command handling
│   │   ├── message_processor.py  # Message routing + processing
│   │   ├── platform_manager.py   # Platform configs (telegram/internal)
│   │   ├── session_manager.py    # Session CRUD (in-memory)
│   │   ├── usage_tracker.py      # Usage logging + quota checks
│   │   └── webhook_client.py     # Webhook delivery (async)
│   ├── utils/                    # Utilities
│   │   ├── logger.py             # Logging setup
│   │   └── parsers.py            # Input parsers
│   └── main.py                   # FastAPI app + Telegram bot integration
├── telegram_bot/                 # Telegram bot
│   ├── bot.py                    # Bot setup
│   ├── handlers.py               # Command handlers
│   └── client.py                 # HTTP client to call own API
├── alembic/                      # Database migrations
│   ├── versions/                 # Migration files
│   │   ├── 0c855e0b81e0_initial_migration.py
│   │   └── 71521c6321dc_add_webhook_fields.py
│   └── env.py                    # Alembic config
├── scripts/                      # CLI tools
│   ├── create_team.py            # Create team via CLI
│   ├── create_api_key.py         # Create API key via CLI
│   └── list_teams.py             # List teams via CLI
├── tests/                        # Tests
│   ├── test_api.py               # API endpoint tests
│   ├── test_sessions.py          # Session management tests
│   └── test_ai_service.py        # AI service client tests
├── manifests/                    # Kubernetes configs
│   ├── dev/
│   ├── stage/
│   └── prod/
├── .env.example                  # Environment template
├── pyproject.toml                # Poetry dependencies
├── Dockerfile                    # Docker image
├── Makefile                      # Development commands
└── README.md
```

---

## 2. Database Schema Design

### 2.1 Tables

#### Table: `teams`
**Purpose:** Organize users into teams for access control and usage tracking

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| name | VARCHAR(255) | UNIQUE, NOT NULL | Team name |
| description | TEXT | NULL | Team description |
| monthly_quota | INTEGER | NULL | Monthly request limit (NULL = unlimited) |
| daily_quota | INTEGER | NULL | Daily request limit (NULL = unlimited) |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Team active status |
| webhook_url | VARCHAR(2048) | NULL | Webhook callback URL |
| webhook_secret | VARCHAR(255) | NULL | HMAC signing secret |
| webhook_enabled | BOOLEAN | NOT NULL, DEFAULT FALSE | Enable webhook |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- UNIQUE INDEX on `name`

**Relationships:**
- ONE team has MANY api_keys
- ONE team has MANY usage_logs

---

#### Table: `api_keys`
**Purpose:** Database-backed API keys for authentication and authorization

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| key_hash | VARCHAR(64) | UNIQUE, NOT NULL | SHA256 hash of API key |
| key_prefix | VARCHAR(16) | NOT NULL | First 8 chars (for display) |
| name | VARCHAR(255) | NOT NULL | Friendly name |
| team_id | INTEGER | FOREIGN KEY(teams.id), NOT NULL | Team association |
| access_level | VARCHAR(50) | NOT NULL, DEFAULT 'user' | Access level (user/team_lead/admin) |
| monthly_quota_override | INTEGER | NULL | Override team quota |
| daily_quota_override | INTEGER | NULL | Override team quota |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Key active status |
| created_by | VARCHAR(255) | NULL | Creator identifier |
| description | TEXT | NULL | Key description |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| last_used_at | TIMESTAMP | NULL | Last usage timestamp |
| expires_at | TIMESTAMP | NULL | Expiration (NULL = never) |

**Indexes:**
- PRIMARY KEY on `id`
- UNIQUE INDEX on `key_hash`
- INDEX on `team_id`

**Relationships:**
- MANY api_keys belong to ONE team
- ONE api_key has MANY usage_logs

---

#### Table: `usage_logs`
**Purpose:** Track API usage for billing, analytics, and quota enforcement

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| api_key_id | INTEGER | FOREIGN KEY(api_keys.id), NOT NULL | API key used |
| team_id | INTEGER | FOREIGN KEY(teams.id), NOT NULL | Team (denormalized) |
| session_id | VARCHAR(64) | NOT NULL | Session identifier |
| platform | VARCHAR(50) | NOT NULL | Platform (telegram/internal) |
| model_used | VARCHAR(255) | NOT NULL | AI model name |
| request_count | INTEGER | NOT NULL, DEFAULT 1 | Number of requests |
| tokens_used | INTEGER | NULL | Tokens consumed |
| estimated_cost | FLOAT | NULL | Estimated cost |
| success | BOOLEAN | NOT NULL | Request success status |
| response_time_ms | INTEGER | NULL | Response time in ms |
| error_message | TEXT | NULL | Error details |
| timestamp | TIMESTAMP | NOT NULL, DEFAULT NOW() | Request timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- INDEX on `api_key_id`
- INDEX on `team_id`
- INDEX on `session_id`
- INDEX on `timestamp`

**Relationships:**
- MANY usage_logs belong to ONE api_key
- MANY usage_logs belong to ONE team

---

### 2.2 Enumerations

#### AccessLevel (Enum)
```python
class AccessLevel(str, Enum):
    ADMIN = "admin"        # Full access - manage teams, keys, view all data
    TEAM_LEAD = "team_lead"  # Manage team members, view team usage
    USER = "user"          # Basic access - use the service only
```

**Access Level Hierarchy:**
- **ADMIN** (level 3): Can do everything
- **TEAM_LEAD** (level 2): Can manage own team + use service
- **USER** (level 1): Can only use the service

---

### 2.3 Database Migrations

**Migration Tool:** Alembic

**Migrations:**
1. **0c855e0b81e0_initial_migration.py**: Create tables (teams, api_keys, usage_logs)
2. **71521c6321dc_add_webhook_fields.py**: Add webhook fields to teams table

**Migration Commands:**
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# View status
alembic current
```

---

## 3. Configuration System

### 3.1 Environment Variables

**Configuration File:** `app/core/config.py`
**Framework:** Pydantic Settings V2

#### Core Configuration
```bash
ENVIRONMENT=dev                    # dev/stage/prod (logging identifier)
AI_SERVICE_URL=https://ai.example.com/v2/chat
SESSION_TIMEOUT_MINUTES=30
```

#### Telegram Platform
```bash
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_DEFAULT_MODEL=google/gemini-2.0-flash-001
TELEGRAM_MODELS=google/gemini-2.0-flash-001,google/gemini-2.5-flash,...
TELEGRAM_RATE_LIMIT=20             # messages/minute
TELEGRAM_MAX_HISTORY=10            # max messages in context
TELEGRAM_COMMANDS=start,help,status,clear,model,models
TELEGRAM_ADMIN_USERS=              # comma-separated user IDs
TELEGRAM_WEBHOOK_URL=              # optional webhook URL
```

#### Internal Platform (API)
```bash
INTERNAL_DEFAULT_MODEL=openai/gpt-5-chat
INTERNAL_MODELS=["openai/gpt-5-chat", "anthropic/claude-3.5-sonnet", ...]
INTERNAL_RATE_LIMIT=60             # messages/minute
INTERNAL_MAX_HISTORY=30            # max messages in context
INTERNAL_API_KEY=<legacy-key>      # backward compatibility only
INTERNAL_WEBHOOK_SECRET=           # optional webhook secret
INTERNAL_ADMIN_USERS=              # comma-separated
```

#### Database (Generic - DevOps sets per deployment)
```bash
DB_HOST=localhost                  # dev: localhost, prod: db.cluster.local
DB_PORT=5432
DB_USER=arash_user                 # dev: arash_dev, prod: arash_prod
DB_PASSWORD=<secret>
DB_NAME=arash_db                   # dev: arash_dev, prod: arash_prod
```

#### Application Behavior
```bash
LOG_LEVEL=DEBUG                    # DEBUG/INFO/WARNING (per environment)
LOG_FILE=logs/arash_api_service.log
ENABLE_API_DOCS=true               # true for dev/stage, false for prod
CORS_ORIGINS=*                     # "*" for dev, specific domains for prod
```

#### API Server
```bash
API_HOST=0.0.0.0
API_PORT=3000
RUN_TELEGRAM_BOT=true              # Enable/disable Telegram bot
```

#### Optional
```bash
REDIS_URL=                         # Optional Redis cache
ENABLE_IMAGE_PROCESSING=true       # Enable image attachments
MAX_IMAGE_SIZE_MB=20
```

### 3.2 Configuration Validation

**Validators:**
- `TELEGRAM_BOT_TOKEN`: Must contain ":" and not be placeholder
- `INTERNAL_API_KEY`: Must be >= 32 characters
- `INTERNAL_MODELS`: Must be valid JSON array or comma-separated list
- `LOG_FILE`: Auto-create parent directory

**Properties:**
```python
settings.is_production      # ENVIRONMENT in (prod, production)
settings.is_development     # ENVIRONMENT in (dev, development)
settings.is_staging         # ENVIRONMENT in (stage, staging)
settings.database_url       # Async PostgreSQL URL (asyncpg)
settings.sync_database_url  # Sync PostgreSQL URL (for Alembic)
settings.telegram_models_list  # Parsed list
settings.internal_models_list  # Parsed list
settings.cors_origins_list     # Parsed list
```

---

## 4. API Endpoints Specification

### 4.1 Public Endpoints

#### GET `/health`
**Purpose:** Health check (unversioned for monitoring)
**Authentication:** None
**Response:**
```json
{
  "status": "healthy" | "degraded",
  "service": "Arash External API Service",
  "version": "1.1.0",
  "timestamp": "2025-11-01T00:00:00"
}
```

---

### 4.2 API v1 Endpoints (Prefix: `/api/v1/`)

#### POST `/api/v1/chat`
**Purpose:** Process a chat message
**Authentication:** Required (Bearer token)
**Request Body:**
```json
{
  "platform": "internal",
  "user_id": "user123",
  "chat_id": "chat456",
  "message_id": "msg789",
  "text": "Hello, how are you?",
  "type": "text",
  "metadata": {}
}
```

**Response:**
```json
{
  "success": true,
  "response": "I'm doing well, thank you!",
  "data": {
    "session_id": "internal_100_chat456",
    "model": "GPT-5 Chat",
    "message_count": 5,
    "history_length": 10
  }
}
```

**Security:**
- API key validated against database
- Team ID extracted from API key
- Session tagged with team_id for isolation
- Metadata includes team_id (invisible to external teams)

#### GET `/api/v1/sessions`
**Purpose:** List active sessions for authenticated team
**Authentication:** Required
**Response:**
```json
{
  "total": 2,
  "authenticated": true,
  "sessions": [
    {
      "session_id": "internal_100_chat1",
      "platform": "internal",
      "current_model": "GPT-5 Chat",
      "message_count": 10,
      "last_activity": "2025-11-01T12:00:00",
      "user_id": "user1",
      "chat_id": "chat1",
      "history_length": 10
    }
  ]
}
```

**Security:**
- Only returns sessions for authenticated team (via team_id)
- Complete team isolation enforced

#### GET `/api/v1/session/{session_id}`
**Purpose:** Get specific session details
**Authentication:** Required
**Response:**
```json
{
  "session": {
    "session_id": "internal_100_chat1",
    "platform": "internal",
    "current_model": "gpt-5-chat",
    "user_id": "user1",
    "chat_id": "chat1",
    "team_id": 100,
    "uptime_seconds": 3600
  },
  "history_length": 10,
  "platform_config": {...}
}
```

**Security:**
- Verify session belongs to authenticated team
- Return 403 if accessing another team's session

#### DELETE `/api/v1/session/{session_id}`
**Purpose:** Delete a session
**Authentication:** Required
**Response:**
```json
{
  "success": true,
  "message": "Session deleted"
}
```

**Security:**
- Verify session belongs to authenticated team
- Return 403 if accessing another team's session

---

### 4.3 Admin Endpoints (Prefix: `/api/v1/admin/`)

**All admin endpoints require `access_level=admin`**

#### GET `/api/v1/admin/`
**Purpose:** Platform information (admin overview)
**Response:**
```json
{
  "service": "Arash External API Service",
  "version": "1.1.0",
  "status": "healthy",
  "platforms": {
    "telegram": {
      "type": "public",
      "model": "Gemini 2.0 Flash",
      "rate_limit": 20,
      "model_switching": false
    },
    "internal": {
      "type": "private",
      "models": ["GPT-5 Chat", "Claude 3.5 Sonnet", ...],
      "rate_limit": 60,
      "model_switching": true
    }
  },
  "active_sessions": 42,
  "timestamp": "2025-11-01T00:00:00"
}
```

#### GET `/api/v1/admin/platforms`
**Purpose:** Full platform configurations
**Response:**
```json
{
  "telegram": {
    "type": "public",
    "model": "Gemini 2.0 Flash",
    "rate_limit": 20,
    "commands": ["start", "help", ...],
    "max_history": 10,
    "features": {
      "model_switching": false,
      "requires_auth": false
    }
  },
  "internal": {
    "type": "private",
    "default_model": "GPT-5 Chat",
    "available_models": [...],
    "rate_limit": 60,
    "commands": [...],
    "max_history": 30,
    "features": {
      "model_switching": true,
      "requires_auth": true
    }
  }
}
```

#### GET `/api/v1/admin/stats`
**Purpose:** Cross-team statistics
**Response:**
```json
{
  "total_sessions": 100,
  "active_sessions": 42,
  "telegram": {
    "sessions": 60,
    "messages": 1200,
    "active": 25,
    "model": "Gemini 2.0 Flash"
  },
  "internal": {
    "sessions": 40,
    "messages": 800,
    "active": 17,
    "models_used": {
      "GPT-5 Chat": 25,
      "Claude 3.5 Sonnet": 15
    },
    "team_breakdown": [
      {
        "team_id": 100,
        "team_name": "Engineering",
        "sessions": 20,
        "messages": 400,
        "active": 10,
        "models_used": {...}
      }
    ]
  },
  "uptime_seconds": 0
}
```

#### POST `/api/v1/admin/teams`
**Purpose:** Create a new team
**Request:**
```json
{
  "name": "Engineering",
  "description": "Engineering team",
  "monthly_quota": 10000,
  "daily_quota": 500
}
```

#### GET `/api/v1/admin/teams`
**Purpose:** List all teams
**Query Params:** `?active_only=true`

#### GET `/api/v1/admin/teams/{team_id}`
**Purpose:** Get team details

#### PATCH `/api/v1/admin/teams/{team_id}`
**Purpose:** Update team settings

#### POST `/api/v1/admin/api-keys`
**Purpose:** Create API key
**Request:**
```json
{
  "team_id": 1,
  "name": "Production Key",
  "access_level": "user",
  "description": "Production environment",
  "monthly_quota": null,
  "daily_quota": null,
  "expires_in_days": 365
}
```

**Response:**
```json
{
  "api_key": "sk_live_abc123...",
  "key_info": {
    "id": 1,
    "key_prefix": "sk_live_",
    "name": "Production Key",
    "team_id": 1,
    "team_name": "Engineering",
    "access_level": "user",
    ...
  },
  "warning": "Save this API key securely. It will not be shown again."
}
```

**Security:**
- API key generated with `secrets.token_urlsafe(32)`
- Stored as SHA256 hash
- Only shown once during creation

#### GET `/api/v1/admin/api-keys`
**Purpose:** List API keys
**Query Params:** `?team_id=1`

#### DELETE `/api/v1/admin/api-keys/{key_id}`
**Purpose:** Revoke API key
**Query Params:** `?permanent=false`

#### GET `/api/v1/admin/usage/team/{team_id}`
**Purpose:** Get team usage statistics
**Query Params:** `?days=30`

#### GET `/api/v1/admin/usage/api-key/{api_key_id}`
**Purpose:** Get API key usage statistics

#### GET `/api/v1/admin/usage/quota/{api_key_id}`
**Purpose:** Check quota status
**Query Params:** `?period=daily` (daily|monthly)

#### GET `/api/v1/admin/usage/recent`
**Purpose:** Get recent usage logs
**Query Params:** `?team_id=1&api_key_id=1&limit=100`

#### PUT `/api/v1/admin/{team_id}/webhook`
**Purpose:** Configure team webhook
**Request:**
```json
{
  "webhook_url": "https://example.com/webhook",
  "webhook_secret": "secret123",
  "webhook_enabled": true
}
```

#### POST `/api/v1/admin/{team_id}/webhook/test`
**Purpose:** Test team webhook

#### GET `/api/v1/admin/{team_id}/webhook`
**Purpose:** Get webhook configuration (secret masked)

---

## 5. Service Layer Components

### 5.1 AIClient (`app/services/ai_client.py`)

**Purpose:** HTTP client for external AI service

**Methods:**
```python
async def health_check() -> bool
    # Checks if AI service is reachable

async def send_chat_request(
    history: List[Dict],
    model: str,
    files: List = None
) -> Dict
    # Sends chat request to AI service
    # Returns: {"Response": str, "Pipeline": str, "Status": str}
```

**Configuration:**
- Base URL: `settings.AI_SERVICE_URL`
- Timeout: 60 seconds
- Uses httpx.AsyncClient

**Request Format:**
```json
{
  "History": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi!"}
  ],
  "Pipeline": "openai/gpt-5-chat",
  "Files": [],
  "AudioFile": null
}
```

---

### 5.2 SessionManager (`app/services/session_manager.py`)

**Purpose:** In-memory session storage and management

**Session Key Format:**
```python
# With team (internal platform)
"{platform}_{team_id}_{chat_id}"
# Example: "internal_100_user123"

# Without team (telegram platform)
"{platform}_{chat_id}"
# Example: "telegram_user456"
```

**Methods:**
```python
def get_session_key(platform: str, chat_id: str, team_id: int = None) -> str
    # Generate unique session key

def get_or_create_session(
    platform: str,
    user_id: str,
    chat_id: str,
    team_id: int = None,
    api_key_id: int = None,
    api_key_prefix: str = None
) -> ChatSession
    # Get existing session or create new one

def get_session_by_id(session_id: str) -> ChatSession | None
    # Find session by session_id (searches all sessions)

def get_sessions_by_team(team_id: int) -> List[ChatSession]
    # Get all sessions for a specific team

def clear_old_sessions() -> int
    # Remove expired sessions (older than SESSION_TIMEOUT_MINUTES)

def get_session_count(platform: str = None) -> int
    # Count sessions by platform

def get_active_session_count(minutes: int = 5) -> int
    # Count sessions active in last N minutes

def clear_rate_limits()
    # Reset rate limit trackers
```

**Session Model:**
```python
class ChatSession(BaseModel):
    session_id: str
    platform: str
    platform_config: Dict[str, Any]
    user_id: str
    chat_id: str
    current_model: str
    history: List[Dict[str, str]]
    message_count: int
    last_activity: datetime
    created_at: datetime

    # Team isolation fields
    team_id: Optional[int]
    api_key_id: Optional[int]
    api_key_prefix: Optional[str]

    # Rate limiting
    user_rate_limit: Dict[str, Any]
```

---

### 5.3 APIKeyManager (`app/services/api_key_manager.py`)

**Purpose:** API key CRUD operations and validation

**Methods:**
```python
@staticmethod
def generate_api_key() -> str
    # Generate secure random API key (48 chars)
    # Format: sk_<type>_<random>

@staticmethod
def hash_api_key(api_key: str) -> str
    # SHA256 hash of API key

@staticmethod
def create_api_key(
    db, team_id, name, access_level,
    description, monthly_quota, daily_quota,
    expires_in_days, created_by
) -> Tuple[str, APIKey]
    # Create new API key
    # Returns: (api_key_string, api_key_object)

@staticmethod
def validate_api_key(db, api_key: str) -> APIKey | None
    # Validate API key and update last_used_at
    # Returns None if invalid/expired/inactive

@staticmethod
def create_team(db, name, description, monthly_quota, daily_quota) -> Team
    # Create new team

@staticmethod
def get_team_by_id(db, team_id: int) -> Team | None
    # Get team by ID

@staticmethod
def get_team_by_name(db, name: str) -> Team | None
    # Get team by name

@staticmethod
def list_all_teams(db, active_only: bool = True) -> List[Team]
    # List all teams

@staticmethod
def update_team(db, team_id, name, description, monthly_quota, daily_quota, is_active) -> Team | None
    # Update team settings

@staticmethod
def list_team_api_keys(db, team_id: int) -> List[APIKey]
    # List all API keys for a team

@staticmethod
def revoke_api_key(db, key_id: int) -> bool
    # Deactivate API key (soft delete)

@staticmethod
def delete_api_key(db, key_id: int) -> bool
    # Permanently delete API key (hard delete)
```

**API Key Format:**
- Prefix: `sk_<type>_` (e.g., `sk_live_`, `sk_test_`)
- Length: 48 characters
- Generation: `secrets.token_urlsafe(32)`
- Storage: SHA256 hash only

---

### 5.4 PlatformManager (`app/services/platform_manager.py`)

**Purpose:** Platform configuration management

**Platforms:**
1. **Telegram** (Public)
2. **Internal** (Private API)

**Configuration Structure:**
```python
class PlatformConfig(BaseModel):
    platform: str
    type: str                        # "public" | "private"
    model: str                       # Default model
    available_models: List[str]      # Available models
    rate_limit: int                  # Messages per minute
    max_history: int                 # Max messages in context
    commands: List[str]              # Available commands
    requires_auth: bool              # Authentication required
```

**Methods:**
```python
def get_config(platform: str) -> PlatformConfig
    # Get platform configuration

def is_valid_platform(platform: str) -> bool
    # Check if platform exists

def get_available_models(platform: str) -> List[str]
    # Get models for platform

def validate_model(platform: str, model: str) -> bool
    # Check if model is available for platform

def get_default_model(platform: str) -> str
    # Get default model for platform
```

---

### 5.5 MessageProcessor (`app/services/message_processor.py`)

**Purpose:** Central message processing and routing

**Flow:**
```
Incoming Message → Platform Detection → Command Detection
                                             ↓
                            ┌────────────────┴────────────────┐
                            │                                 │
                      Command Handler                  AI Processing
                      (/help, /clear, ...)             (AI Service)
                            │                                 │
                            └────────────────┬────────────────┘
                                             ↓
                                    Update Session
                                             ↓
                                    Log Usage
                                             ↓
                                Send Webhook (async)
                                             ↓
                                    Return Response
```

**Methods:**
```python
async def process_message(message: IncomingMessage) -> BotResponse
    # Main entry point for message processing
    # 1. Get/create session
    # 2. Check rate limits
    # 3. Process command or AI request
    # 4. Update session
    # 5. Log usage
    # 6. Send webhook (background)
    # 7. Return response

async def _process_ai_request(session, message) -> BotResponse
    # Process message through AI service

async def _send_webhook(team_id, message, response)
    # Send webhook notification (background task)
```

---

### 5.6 CommandProcessor (`app/services/command_processor.py`)

**Purpose:** Handle special commands (/help, /clear, /model, etc.)

**Commands:**
- `/help` - Show available commands
- `/status` - Show session status
- `/clear` - Clear conversation history
- `/model <name>` - Switch AI model
- `/models` - List available models

**Methods:**
```python
def is_command(text: str) -> bool
    # Check if text is a command

async def process_command(command: str, session: ChatSession, platform_config) -> BotResponse
    # Process command and return response

def _handle_help(session, platform_config) -> BotResponse
def _handle_status(session, platform_config) -> BotResponse
def _handle_clear(session) -> BotResponse
def _handle_model(session, model_name, platform_config) -> BotResponse
def _handle_models(session, platform_config) -> BotResponse
```

---

### 5.7 UsageTracker (`app/services/usage_tracker.py`)

**Purpose:** Log API usage and enforce quotas

**Methods:**
```python
@staticmethod
def log_request(
    db,
    api_key_id: int,
    team_id: int,
    session_id: str,
    platform: str,
    model_used: str,
    success: bool,
    response_time_ms: int = None,
    error_message: str = None
) -> UsageLog
    # Log API request

@staticmethod
def get_team_usage_stats(db, team_id: int, start_date: datetime) -> Dict
    # Get usage statistics for team

@staticmethod
def get_api_key_usage_stats(db, api_key_id: int, start_date: datetime) -> Dict
    # Get usage statistics for API key

@staticmethod
def check_quota(db, api_key: APIKey, period: str) -> Dict
    # Check if quota exceeded
    # Returns: {
    #   "quota": <limit>,
    #   "used": <count>,
    #   "remaining": <remaining>,
    #   "exceeded": <bool>
    # }

@staticmethod
def get_recent_usage(db, team_id: int = None, api_key_id: int = None, limit: int = 100) -> List[UsageLog]
    # Get recent usage logs
```

**Quota Enforcement:**
1. Check daily quota (past 24 hours)
2. Check monthly quota (past 30 days)
3. Return 429 if exceeded

---

### 5.8 WebhookClient (`app/services/webhook_client.py`)

**Purpose:** Send webhook notifications to team endpoints

**Webhook Payload:**
```json
{
  "event": "message.completed",
  "timestamp": "2025-11-01T12:00:00Z",
  "team_id": 100,
  "session_id": "internal_100_chat1",
  "message": {
    "user_id": "user1",
    "chat_id": "chat1",
    "text": "Hello",
    "type": "text"
  },
  "response": {
    "success": true,
    "response": "Hi there!",
    "model": "GPT-5 Chat"
  }
}
```

**Signature:**
- Header: `X-Webhook-Signature: sha256=<hash>`
- Algorithm: HMAC-SHA256
- Key: `team.webhook_secret`

**Methods:**
```python
async def send_message_callback(team: Team, message_data: Dict, response_data: Dict) -> bool
    # Send webhook notification
    # Returns: True if successful

async def test_webhook(team: Team) -> Dict
    # Send test webhook
    # Returns: {
    #   "success": bool,
    #   "status_code": int,
    #   "response_time_ms": int,
    #   "error": str | None
    # }

def _generate_signature(payload: str, secret: str) -> str
    # Generate HMAC-SHA256 signature
```

**Behavior:**
- Async fire-and-forget (doesn't block response)
- 10 second timeout
- Uses `asyncio.create_task()`

---

## 6. Authentication & Authorization

### 6.1 Authentication Flow

```
1. Client sends request with Authorization header
   Authorization: Bearer sk_live_abc123...

2. FastAPI dependency extracts token
   authorization: HTTPAuthorizationCredentials = Depends(security)

3. APIKeyManager.validate_api_key(db, token)
   - Hash token with SHA256
   - Query database for matching key_hash
   - Check is_active, is_expired
   - Update last_used_at
   - Return APIKey object or None

4. Dependency checks access level
   - verify_api_key(authorization, min_access_level)
   - Compare key's access_level with required level
   - Return 403 if insufficient

5. Request proceeds with authenticated APIKey object
```

### 6.2 Dependencies (`app/api/dependencies.py`)

```python
# Security scheme
security = HTTPBearer(auto_error=False)

def verify_api_key(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    min_access_level: AccessLevel = AccessLevel.USER,
) -> APIKey:
    """
    Verify API key and check access level
    Returns validated API key object
    """
    # Validate API key
    # Check access level hierarchy
    # Return APIKey or raise HTTPException

def require_admin_access(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> APIKey:
    """Require admin-level access"""
    return verify_api_key(authorization, AccessLevel.ADMIN)

def require_team_lead_access(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> APIKey:
    """Require team-lead or admin-level access"""
    return verify_api_key(authorization, AccessLevel.TEAM_LEAD)
```

### 6.3 Team Isolation

**Session Key Isolation:**
```python
# Internal platform (with team)
session_key = f"internal_{team_id}_{chat_id}"

# Telegram platform (without team)
session_key = f"telegram_{chat_id}"
```

**Endpoint Isolation:**
- `/api/v1/sessions` - Only returns sessions for authenticated team
- `/api/v1/session/{id}` - Verifies session.team_id matches api_key.team_id
- `DELETE /api/v1/session/{id}` - Verifies ownership before deletion

**Admin Access:**
- Admin users see all teams/sessions (no filtering)
- Used for monitoring and management

---

## 7. Telegram Bot Integration

### 7.1 Architecture

**Integration:** Runs inside FastAPI app (not separate process)

```python
# app/main.py
if settings.RUN_TELEGRAM_BOT:
    from telegram_bot.bot import TelegramBot

    telegram_bot = TelegramBot(service_url=f"http://localhost:{settings.API_PORT}")
    telegram_bot.setup()
    telegram_task = asyncio.create_task(run_telegram_bot())
```

### 7.2 Bot Structure

**Files:**
- `telegram_bot/bot.py` - Bot setup and initialization
- `telegram_bot/handlers.py` - Command and message handlers
- `telegram_bot/client.py` - HTTP client to call own API

**Flow:**
```
Telegram User → python-telegram-bot → Handler
                                         ↓
                             Call own API (HTTP)
                             POST /api/v1/message
                                         ↓
                             MessageProcessor
                                         ↓
                             Response → Telegram User
```

### 7.3 Handlers

```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming message"""
    # 1. Extract message details
    # 2. Call POST /api/v1/message via HTTP client
    # 3. Send response back to user

async def handle_start(update, context):
    """Handle /start command"""

async def handle_help(update, context):
    """Handle /help command"""
```

### 7.4 HTTP Client (`telegram_bot/client.py`)

```python
class TelegramBotClient:
    """HTTP client to call own API"""

    async def send_message(
        self,
        user_id: str,
        chat_id: str,
        message_id: str,
        text: str,
        message_type: str = "text"
    ) -> Dict:
        """Send message to API"""
        # POST to /api/v1/message
        # No authentication (telegram platform doesn't require it)
```

---

## 8. Deployment

### 8.1 Docker

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install Poetry
RUN pip install poetry

# Copy dependencies
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-dev

# Copy application
COPY . .

# Run migrations and start app
CMD ["sh", "-c", "poetry run alembic upgrade head && poetry run uvicorn app.main:app --host 0.0.0.0 --port 3000"]
```

**Build:**
```bash
docker build -t arash-external-api:latest .
```

**Run:**
```bash
docker run --rm --env-file .env -p 3000:3000 arash-external-api:latest
```

### 8.2 Kubernetes

**Structure:**
```
manifests/
├── dev/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── secret.yaml
├── stage/
│   └── (same structure)
└── prod/
    └── (same structure)
```

**ConfigMap Example:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: arash-api-config
data:
  ENVIRONMENT: "dev"
  LOG_LEVEL: "DEBUG"
  ENABLE_API_DOCS: "true"
  CORS_ORIGINS: "*"
  DB_HOST: "postgres-service"
  DB_PORT: "5432"
  DB_NAME: "arash_dev"
  API_PORT: "3000"
```

**Secret Example:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: arash-api-secrets
type: Opaque
data:
  DB_PASSWORD: <base64>
  TELEGRAM_BOT_TOKEN: <base64>
  INTERNAL_API_KEY: <base64>
```

**Deployment:**
```bash
kubectl apply -f manifests/dev/
```

---

## 9. Testing Strategy

### 9.1 Test Structure

```
tests/
├── test_api.py              # API endpoint tests (FastAPI TestClient)
├── test_sessions.py         # Session management tests
└── test_ai_service.py       # AI service client tests
```

### 9.2 Test Coverage

**API Tests:**
- Health endpoint
- Authentication (valid/invalid/missing keys)
- Message processing
- Session listing/retrieval/deletion
- Team isolation
- Admin endpoints
- API versioning

**Session Tests:**
- Session creation
- Session key generation (with/without team)
- Session isolation
- Session retrieval
- Session expiration
- History management

**AI Service Tests:**
- Connectivity
- Health check
- Chat request format

### 9.3 Mocking

**Mock API Keys:**
```python
@pytest.fixture
def mock_api_key_user():
    key = Mock()
    key.id = 1
    key.team_id = 100
    key.access_level = AccessLevel.USER.value
    return key

@pytest.fixture
def mock_api_key_admin():
    key = Mock()
    key.id = 2
    key.team_id = 200
    key.access_level = AccessLevel.ADMIN.value
    return key
```

**Mock Dependencies:**
```python
@patch("app.api.dependencies.APIKeyManager")
@patch("app.api.routes.message_processor")
def test_valid_api_key(mock_processor, mock_key_mgr, client, mock_api_key_user):
    mock_key_mgr.validate_api_key.return_value = mock_api_key_user
    mock_processor.process_message = AsyncMock(return_value=BotResponse(...))

    response = client.post("/api/v1/chat", headers={"Authorization": "Bearer test"}, json={...})
    assert response.status_code == 200
```

---

## 10. Implementation Steps

### Phase 1: Core Setup (Week 1)

1. **Project Initialization**
   - Create directory structure
   - Setup Poetry (`pyproject.toml`)
   - Install dependencies: FastAPI, SQLAlchemy, Alembic, Pydantic, httpx
   - Create `.env.example`

2. **Configuration System**
   - Implement `app/core/config.py` with Pydantic Settings V2
   - Add validators
   - Create helper properties

3. **Database Models**
   - Implement `app/models/database.py` (Team, APIKey, UsageLog)
   - Setup Alembic
   - Create initial migration

4. **Basic FastAPI App**
   - Create `app/main.py`
   - Add health endpoint
   - Setup CORS middleware
   - Setup logging

### Phase 2: Authentication & Services (Week 2)

5. **API Key Management**
   - Implement `APIKeyManager` service
   - Key generation, hashing, validation
   - Team CRUD operations

6. **Authentication System**
   - Implement `app/api/dependencies.py`
   - Create security dependencies
   - Add access level checks

7. **Session Management**
   - Implement `SessionManager` service
   - Session CRUD operations
   - Team isolation logic

8. **Platform Configuration**
   - Implement `PlatformManager`
   - Define platform configs (telegram/internal)

### Phase 3: Core Functionality (Week 3)

9. **AI Service Client**
   - Implement `AIClient`
   - Health check
   - Chat request handling

10. **Message Processing**
    - Implement `MessageProcessor`
    - Command detection
    - AI request routing
    - Session updates

11. **Command Processor**
    - Implement `CommandProcessor`
    - Handle /help, /status, /clear, /model, /models

12. **Usage Tracking**
    - Implement `UsageTracker`
    - Log requests
    - Quota checking
    - Usage statistics

### Phase 4: API Endpoints (Week 4)

13. **Public Endpoints**
    - Implement `app/api/routes.py`
    - POST /api/v1/chat
    - GET /api/v1/sessions
    - GET /api/v1/session/{id}
    - DELETE /api/v1/session/{id}

14. **Admin Endpoints**
    - Implement `app/api/admin_routes.py`
    - Platform information
    - Team management
    - API key management
    - Usage tracking endpoints

### Phase 5: Telegram Integration (Week 5)

15. **Telegram Bot**
    - Implement `telegram_bot/bot.py`
    - Setup handlers (`telegram_bot/handlers.py`)
    - Implement HTTP client (`telegram_bot/client.py`)
    - Integrate with FastAPI app

### Phase 6: Advanced Features (Week 6)

16. **Webhook System**
    - Implement `WebhookClient`
    - Add webhook fields to Team model (migration)
    - Implement webhook endpoints
    - Add HMAC signature validation

17. **Rate Limiting**
    - Add rate limiting to SessionManager
    - Implement quota enforcement
    - Add 429 responses

### Phase 7: Testing & Documentation (Week 7)

18. **Tests**
    - Write API tests (`tests/test_api.py`)
    - Write session tests (`tests/test_sessions.py`)
    - Write AI service tests (`tests/test_ai_service.py`)
    - Achieve >80% coverage

19. **Documentation**
    - Complete README.md
    - API documentation (OpenAPI/Swagger)
    - Deployment guides
    - Security documentation

### Phase 8: Deployment (Week 8)

20. **Docker**
    - Create Dockerfile
    - Test local Docker build
    - Create docker-compose.yml

21. **Kubernetes**
    - Create K8s manifests (dev/stage/prod)
    - ConfigMaps and Secrets
    - Deployment, Service, Ingress

22. **CI/CD**
    - Setup GitHub Actions
    - Automated testing
    - Docker image builds
    - Deployment pipelines

---

## 11. Dependencies

### 11.1 Python Dependencies

**Core:**
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
sqlalchemy = "^2.0.23"
alembic = "^1.13.0"
asyncpg = "^0.29.0"  # Async PostgreSQL driver
psycopg2-binary = "^2.9.9"  # Sync PostgreSQL driver (for Alembic)
httpx = "^0.25.0"
python-telegram-bot = "^20.7"
```

**Development:**
```toml
[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
pytest-cov = "^4.1.0"
black = "^23.11.0"
ruff = "^0.1.6"
```

### 11.2 External Services

**Required:**
- PostgreSQL 14+
- External AI Service (HTTP API)

**Optional:**
- Redis (for caching/rate limiting)
- Monitoring (Prometheus/Grafana)

---

## 12. Security Considerations

### 12.1 API Key Security

- API keys never stored in plain text (SHA256 hash only)
- Minimum 32 character length
- Secure random generation (`secrets.token_urlsafe`)
- Only shown once at creation
- Expiration dates supported

### 12.2 Team Isolation

- Session keys include team_id
- All team-scoped endpoints verify ownership
- Database queries filtered by team_id
- Admin bypass for monitoring

### 12.3 Rate Limiting

- Per-user rate limiting (messages per minute)
- Per-team quotas (daily/monthly)
- Quota enforcement at request time
- 429 responses when exceeded

### 12.4 Input Validation

- All inputs validated with Pydantic models
- SQL injection prevention (SQLAlchemy ORM)
- XSS prevention (no HTML rendering)

### 12.5 Webhook Security

- HMAC-SHA256 signatures
- Secret per team
- 10 second timeout
- HTTPS validation

---

## 13. Monitoring & Logging

### 13.1 Logging

**Configuration:** `app/utils/logger.py`

**Levels:**
- DEBUG: Development
- INFO: Staging
- WARNING: Production

**Outputs:**
- Console (stdout)
- File (`logs/arash_api_service.log`)

**Format:**
```
2025-11-01 12:00:00 - app.api.routes - INFO - Processing message for session internal_100_chat1
```

### 13.2 Metrics

**Health Endpoint:** `/health`
```json
{
  "status": "healthy",
  "components": {
    "api": "healthy",
    "ai_service": "healthy",
    "database": "healthy"
  }
}
```

**Admin Stats:** `/api/v1/admin/stats`
- Total sessions
- Active sessions
- Platform breakdown
- Team breakdown

---

## 14. Performance Optimization

### 14.1 In-Memory Session Storage

- Fast session lookup (O(1))
- No database overhead for sessions
- Automatic cleanup of old sessions

### 14.2 Database Connection Pooling

- SQLAlchemy connection pool
- Reuse connections across requests
- Configurable pool size

### 14.3 Async Operations

- Async database queries (asyncpg)
- Async HTTP requests (httpx)
- Async webhook delivery (fire-and-forget)

### 14.4 Caching

**Optional Redis Integration:**
- Cache team configurations
- Cache platform configurations
- Cache usage quotas

---

## 15. Error Handling

### 15.1 HTTP Error Codes

- **200 OK**: Successful request
- **401 Unauthorized**: Missing/invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **429 Too Many Requests**: Quota exceeded
- **500 Internal Server Error**: Server error

### 15.2 Error Response Format

```json
{
  "detail": "Error message",
  "success": false,
  "error": "error_code"
}
```

### 15.3 Global Exception Handler

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "internal_server_error",
            "detail": "An internal error occurred" if is_production else str(exc)
        }
    )
```

---

## 16. Development Workflow

### 16.1 Local Development

```bash
# Install dependencies
poetry install

# Setup database
createdb arash_db
poetry run alembic upgrade head

# Create .env file
cp .env.example .env
# Edit .env with your settings

# Run development server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
```

### 16.2 Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/test_api.py -v
```

### 16.3 Code Quality

```bash
# Format code
poetry run black app/ tests/

# Lint code
poetry run ruff check app/ tests/

# Type checking (optional)
poetry run mypy app/
```

### 16.4 Database Migrations

```bash
# Create migration
poetry run alembic revision --autogenerate -m "Add new column"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1

# View migration history
poetry run alembic history
```

---

## 17. Production Checklist

### 17.1 Pre-Deployment

- [ ] Set `ENVIRONMENT=prod`
- [ ] Set `LOG_LEVEL=WARNING` or `ERROR`
- [ ] Set `ENABLE_API_DOCS=false`
- [ ] Configure production database credentials
- [ ] Set strong `DB_PASSWORD`
- [ ] Configure `CORS_ORIGINS` to specific domains (not `*`)
- [ ] Generate production `TELEGRAM_BOT_TOKEN`
- [ ] Generate production `INTERNAL_API_KEY` (>32 chars)

### 17.2 Database Setup

- [ ] Create production PostgreSQL database
- [ ] Run migrations: `alembic upgrade head`
- [ ] Create initial admin team
- [ ] Create admin API key
- [ ] Test database connection

### 17.3 Security

- [ ] Enable HTTPS/TLS
- [ ] Setup firewall rules
- [ ] Configure rate limiting
- [ ] Enable request logging
- [ ] Setup monitoring alerts

### 17.4 Monitoring

- [ ] Configure log rotation
- [ ] Setup health check monitoring
- [ ] Configure error alerting
- [ ] Setup performance monitoring
- [ ] Test backup/restore procedures

---

## 18. Known Limitations

1. **Session Storage:** In-memory only (lost on restart)
   - **Solution:** Implement Redis or database-backed sessions

2. **Rate Limiting:** In-memory only (not distributed)
   - **Solution:** Use Redis for distributed rate limiting

3. **No Authentication for Telegram:** Telegram platform doesn't require API keys
   - **Rationale:** Public bot, users authenticated by Telegram

4. **Webhook Delivery:** Best-effort, no retry mechanism
   - **Solution:** Implement retry queue with exponential backoff

5. **No Admin UI:** Administration via API only
   - **Solution:** Build React/Vue admin panel

---

## 19. Future Enhancements

### Priority 1 (High)
- [ ] Redis integration for distributed sessions
- [ ] Webhook retry mechanism
- [ ] Admin web UI
- [ ] API versioning support (v2)
- [ ] Multi-language support

### Priority 2 (Medium)
- [ ] Advanced analytics dashboard
- [ ] Cost tracking and billing
- [ ] Model performance metrics
- [ ] Custom model configurations per team
- [ ] Scheduled message cleanup

### Priority 3 (Low)
- [ ] GraphQL API
- [ ] WebSocket support for real-time updates
- [ ] Plugin system for custom commands
- [ ] Multi-region deployment
- [ ] Advanced caching strategies

---

## 20. Conclusion

This implementation plan provides a comprehensive blueprint for building the Arash External API Service. The system is designed to be:

✅ **Scalable**: Async architecture, database connection pooling
✅ **Secure**: Database-backed API keys, team isolation, HMAC webhooks
✅ **Maintainable**: Clean architecture, comprehensive tests, type hints
✅ **Production-Ready**: Docker/K8s deployment, monitoring, logging
✅ **Enterprise-Grade**: Multi-tenant, usage tracking, quota management

**Total Estimated Development Time:** 8 weeks (1 developer)

**Lines of Code:** ~4,500 Python lines across 27 modules

**Key Technologies:**
- FastAPI (web framework)
- PostgreSQL (database)
- SQLAlchemy (ORM)
- Alembic (migrations)
- python-telegram-bot (Telegram integration)
- Pydantic (validation)
- httpx (async HTTP)
