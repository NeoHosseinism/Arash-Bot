# Arash Bot - AI Chat Service

Enterprise AI chatbot service with Telegram bot, team-based access control, and multi-AI model support (GPT, Claude, Gemini, DeepSeek, Grok).

## Quick Start

```bash
# 1. Install dependencies
curl -sSL https://install.python-poetry.org | python3 -
poetry install

# 2. Configure environment
cp .env.example .env
nano .env  # Set DB credentials, bot token, AI service URL

# 3. Run migrations
make migrate-up

# 4. Start service
make run  # http://localhost:3000
```

**API Docs:** http://localhost:3000/docs
**Health Check:** http://localhost:3000/health

---

## Features

- **Multi-AI Models**: GPT-5, Claude 4.5, Gemini 2.5, Grok 4, DeepSeek v3
- **Dual Platform**: Telegram (public) + Internal API (private)
- **Team Isolation**: Complete data separation between teams
- **Two-Path Auth**: Super admins (env vars) + Team keys (database)
- **Usage Tracking**: Requests, tokens, costs per team/key
- **Rate Limiting**: Per-user quotas (daily/monthly)
- **Single Container**: FastAPI + Telegram bot in one image
- **K8s Ready**: Health checks, secrets, ConfigMaps

---

## Architecture

```
┌─────────────────────────────────────┐
│     Nginx Ingress (K8s)             │
└────────────────┬────────────────────┘
                 │
         ┌───────┴───────┐
         │               │
    Telegram Users   Internal Apps
         │               │
         └───────┬───────┘
                 ▼
┌─────────────────────────────────────┐
│  Arash Bot Container (Port 3000)    │
│  ┌─────────────────────────────┐   │
│  │ FastAPI + Telegram Bot      │   │
│  └─────────────────────────────┘   │
└────────┬────────────┬───────────────┘
         │            │
         ▼            ▼
  PostgreSQL    AI Service
  (Teams,       (GPT/Claude/
   Keys,         Gemini/etc)
   Usage)
```

**Core Components:**
- `app/main.py` - FastAPI + integrated Telegram bot
- `app/api/routes.py` - Public API (chat)
- `app/api/admin_routes.py` - Admin API (teams, keys, usage)
- `app/api/dependencies.py` - Two-path authentication
- `app/services/session_manager.py` - In-memory sessions with team isolation
- `app/services/message_processor.py` - Message handling
- `app/models/database.py` - SQLAlchemy models (Team, APIKey, UsageLog)

**Session Key Format:** `platform:team_id:chat_id` (prevents team collision)

---

## Configuration

### Environment Variables

```bash
# Environment (for logging only)
ENVIRONMENT=dev                      # dev | stage | prod

# Database (required)
DB_HOST=localhost
DB_PORT=5432
DB_USER=arash_dev
DB_PASSWORD=your_password
DB_NAME=arash_dev

# AI Service (required)
AI_SERVICE_URL=https://ai-service.example.com

# Super Admin Keys (comma-separated, for /api/v1/admin/*)
SUPER_ADMIN_API_KEYS=key1,key2,key3

# Telegram Bot (required if RUN_TELEGRAM_BOT=true)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
RUN_TELEGRAM_BOT=true

# Application Behavior
LOG_LEVEL=DEBUG                      # DEBUG | INFO | WARNING | ERROR
LOG_TIMESTAMP=both                   # utc | ir | both
ENABLE_API_DOCS=true                 # true in dev/stage, false in prod
CORS_ORIGINS=*                       # * in dev, specific domains in prod
```

**Platform Configs:**
- **Telegram**: Gemini 2.0 Flash, 20 msg/min, 10 msg history
- **Internal**: GPT-5 Chat default, 60 msg/min, 30 msg history, API key required

---

## Authentication

### Two-Path System

**1. Super Admins (Environment-Based)**
```bash
# Set in environment/K8s Secrets
SUPER_ADMIN_API_KEYS="admin_key_1,admin_key_2"

# Use for /api/v1/admin/* endpoints
curl -H "Authorization: Bearer admin_key_1" \
  http://localhost:3000/api/v1/admin/teams
```

**2. Teams (Database-Based)**
```bash
# Created by super admins
make db-key-create TEAM=1 NAME="Production Key"

# Use for /api/v1/chat endpoint
curl -H "Authorization: Bearer sk_live_xxx" \
  http://localhost:3000/api/v1/chat -d '{...}'
```

**Access Matrix:**

| Endpoint | Super Admin | Team Key |
|----------|-------------|----------|
| `/api/v1/chat` | ✅ | ✅ |
| `/api/v1/admin/*` | ✅ | ❌ |

**Security:**
- Super admin keys NOT in database (environment only)
- Team keys hashed (SHA256), never stored plain
- Sessions tagged with `team_id` (complete isolation)
- Team A cannot see Team B's data

---

## API Reference

### Public Endpoints

```bash
# Health Check (no auth)
GET /health

# Chat (team API key required)
POST /api/v1/chat
Authorization: Bearer sk_live_xxx
{
  "platform": "internal",
  "user_id": "user123",
  "chat_id": "chat456",
  "message_id": "msg789",
  "text": "Hello"
}
```

### Admin Endpoints (Super Admin Only)

```bash
# Create Team
POST /api/v1/admin/teams
Authorization: Bearer <super_admin_key>
{
  "name": "Engineering",
  "monthly_quota": 10000,
  "daily_quota": 500
}

# Create API Key for Team
POST /api/v1/admin/api-keys
Authorization: Bearer <super_admin_key>
{
  "team_id": 1,
  "name": "Production Key",
  "expires_in_days": 365
}

# Team Usage Stats
GET /api/v1/admin/usage/team/1?days=30
Authorization: Bearer <super_admin_key>

# Platform Stats
GET /api/v1/admin/stats
Authorization: Bearer <super_admin_key>
```

**Full API docs:** See [API.md](API.md) or http://localhost:3000/docs

---

## Database Management

```bash
# Teams
make db-team-create NAME="Engineering" DAILY=1000 MONTHLY=30000
make db-teams                        # List all teams

# API Keys
make db-key-create TEAM=1 NAME="Admin Key"
make db-keys                         # List all keys

# Migrations
make migrate-create MSG="Add new column"
make migrate-up                      # Apply pending
make migrate-down                    # Rollback last
make migrate-status                  # Show current
```

**Schema:**
- `teams` - Team info with quotas
- `api_keys` - Hashed keys (SHA256) with team association
- `usage_logs` - Requests, tokens, costs per team/key

---

## Development

### Commands

```bash
make install          # Install dependencies (Poetry)
make run              # Run with auto-reload (port 3000)
make test             # Run pytest tests
make lint             # Check code (Ruff)
make format           # Format code (Black)
make clean            # Remove cache files

make docker-build     # Build image
make docker-run       # Run container
```

### Project Structure

```
app/
├── api/
│   ├── routes.py              # Public endpoints
│   ├── admin_routes.py        # Admin endpoints
│   └── dependencies.py        # Two-path authentication
├── core/
│   ├── config.py              # Settings (Pydantic)
│   ├── constants.py           # System constants
│   └── name_mapping.py        # Model ID → friendly names
├── models/
│   ├── database.py            # SQLAlchemy models
│   ├── schemas.py             # Pydantic schemas
│   └── session.py             # In-memory session model
├── services/
│   ├── message_processor.py  # Core message logic
│   ├── command_processor.py  # Bot commands
│   ├── session_manager.py    # Session management
│   ├── ai_client.py           # AI service communication
│   ├── api_key_manager.py    # Key CRUD operations
│   └── usage_tracker.py      # Usage logging
└── main.py                    # FastAPI + Telegram bot

telegram_bot/
└── bot.py                     # Telegram bot handlers

alembic/versions/              # Database migrations
manifests/                     # Kubernetes configs
  ├── dev/
  ├── stage/
  └── prod/
```

---

## Deployment

### Docker

```bash
# Build
docker build -t arash-bot .

# Run
docker run --rm --env-file .env -p 3000:3000 arash-bot
```

**Dockerfile includes:**
- Python 3.11
- Poetry dependencies
- Health check (`/health` endpoint)
- Single container (API + Telegram bot)

### Kubernetes

```bash
# Deploy to environment
kubectl apply -f manifests/dev/      # Development
kubectl apply -f manifests/stage/    # Staging
kubectl apply -f manifests/prod/     # Production

# Check status
kubectl get pods -n arash
kubectl get svc -n arash
kubectl logs -f deployment/arash-external-api -n arash
```

**K8s Resources:**
- Deployment: Single container, health probes (liveness/readiness)
- Service: ClusterIP on port 3000
- Ingress: Nginx with TLS
- ConfigMap: Non-sensitive config (LOG_LEVEL, etc.)
- Secret: Sensitive data (DB_PASSWORD, bot token, super admin keys)

**URLs:**
- Dev: https://arash-api-dev.irisaprime.ir
- Stage: https://arash-api-stage.irisaprime.ir
- Prod: https://arash-api.irisaprime.ir

**Health Probes:**
```yaml
livenessProbe:
  httpGet: {path: /health, port: 3000}
  initialDelaySeconds: 40
  periodSeconds: 30
readinessProbe:
  httpGet: {path: /health, port: 3000}
  initialDelaySeconds: 10
  periodSeconds: 10
```

### Production Checklist

- [ ] Set `SUPER_ADMIN_API_KEYS` in K8s Secret
- [ ] Set `DB_PASSWORD` in K8s Secret
- [ ] Set `TELEGRAM_BOT_TOKEN` in K8s Secret
- [ ] Set `LOG_LEVEL=WARNING` (or ERROR)
- [ ] Set `ENABLE_API_DOCS=false`
- [ ] Set `CORS_ORIGINS` to specific domains (no `*`)
- [ ] Run migrations: `make migrate-up`
- [ ] Create initial teams and API keys
- [ ] Test health check: `curl https://arash-api.irisaprime.ir/health`

---

## Logging

**Format:** `[timestamp][level] message [context] key=value...`

**Configuration:**
```bash
LOG_LEVEL=DEBUG                    # Verbosity
LOG_TIMESTAMP=both                 # utc | ir | both
LOG_COLOR=auto                     # auto | true | false
LOG_TIMESTAMP_PRECISION=6          # 3 (ms) | 6 (μs)
```

**Examples:**
```
# UTC only
[2025-11-08 11:04:40.401000 UTC][info] server_started port=3000

# Iranian only
[1404-08-17 14:34:40.403000 IR][info] server_started port=3000

# Both (default)
[2025-11-08 11:04:40.404000 UTC][1404-08-17 14:34:40.404000 IR][info] server_started port=3000
```

**Colors:**
- `[debug]` - Gray
- `[info]` - Green
- `[warn]` - Yellow
- `[error]` - Red

**Demo:**
```bash
python3 demo_timestamp_modes.py    # Interactive demo
make demo-logging                  # Or use make
```

---

## Security

### Team Isolation

**Session Keys Include Team ID:**
```python
# Team A, chat_id="user123" → Session: "internal:100:user123"
# Team B, chat_id="user123" → Session: "internal:200:user123"
# Different keys = Different sessions (no collision)
```

**Access Control:**
- Team A's API key can ONLY access Team A's sessions/data
- Super admins can see cross-team stats (admin endpoints)
- Regular teams CANNOT discover other teams or Telegram bot

**Authentication Flow:**
1. Request with `Authorization: Bearer <key>`
2. Super admin check: Is key in `SUPER_ADMIN_API_KEYS`? → Admin access
3. Database check: Hash key (SHA256), lookup in `api_keys` table → Team access
4. Extract `team_id` from validated key
5. Tag session/operation with `team_id`
6. Enforce team ownership checks

**Security Features:**
- API keys hashed (SHA256), never stored plain
- Session keys include `team_id` to prevent collision
- All admin endpoints require super admin key
- All team operations check `team_id` ownership
- Rate limiting per user/team
- Input validation (Pydantic)
- CORS configurable per environment

---

## Troubleshooting

### Database Connection

```bash
# Check connection
make migrate-status

# Verify env vars
grep DB_ .env

# Test connection
psql -h $DB_HOST -U $DB_USER -d $DB_NAME
```

### Migration Issues

```bash
# View history
make migrate-status

# Rollback if broken
make migrate-down

# Reapply
make migrate-up

# Create new migration
make migrate-create MSG="Description"
```

### Application Issues

```bash
# View logs
tail -f logs/arash_bot_service.log

# Run tests
make test

# Check health
curl http://localhost:3000/health

# Check config
make show-config
```

### Common Errors

**"Invalid API key"**
- Super admins: Check `SUPER_ADMIN_API_KEYS` environment variable
- Teams: Verify key exists in database (`make db-keys`)

**"Team isolation error"**
- Session keys include `team_id` - different teams can't collide
- Check session manager logs for team ownership

**"Database not found"**
- Run migrations: `make migrate-up`
- Check `DB_NAME` matches database name

---

## Telegram Bot

**Commands:**
- `/start` - Welcome message
- `/help` - Show commands
- `/status` - Session info
- `/clear` - Clear history
- `/models` - List models
- `/model <name>` - Switch model (if enabled)

**Setup:**
1. Create bot with @BotFather
2. Set `TELEGRAM_BOT_TOKEN` in `.env`
3. Set `RUN_TELEGRAM_BOT=true`
4. Run `make run`

**Configuration:**
- Default model: Gemini 2.0 Flash (configured in `.env`)
- Rate limit: 20 messages/minute
- History: 10 messages max
- Model switching: Disabled (fixed model for public)

---

## Infrastructure

**Running Components:**
- ✅ Python container (FastAPI + Telegram bot)
- ✅ PostgreSQL (teams, keys, usage logs)
- ✅ AI Service (external)
- ✅ Nginx Ingress (K8s)

**NOT Running (Dead Code):**
- ❌ Prometheus/Grafana (mentioned in old docs, not implemented)
- ❌ Flower (not using Celery)
- ❌ Redis (sessions are in-memory)

---

## License

MIT

---

## Quick Reference Card

```bash
# Setup
poetry install && cp .env.example .env && make migrate-up && make run

# Database
make db-team-create NAME="Team" DAILY=1000 MONTHLY=30000
make db-key-create TEAM=1 NAME="Key"
make migrate-up

# Development
make run            # Start server
make test           # Run tests
make lint           # Check code
make clean          # Clean cache

# Deployment
make docker-build   # Build image
kubectl apply -f manifests/prod/   # Deploy to K8s

# API
curl http://localhost:3000/health  # Health check
curl http://localhost:3000/docs    # API documentation

# Logs
tail -f logs/arash_bot_service.log
```

**Support:** Check health endpoint, logs, and API docs for issues.
