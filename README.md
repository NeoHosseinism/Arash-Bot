# Arash External API Service v1.0

Enterprise-ready AI chatbot service with integrated Telegram bot, team-based access control, and multi-platform support.

## Features

- **Multi-Platform Support**: Telegram (public) and Internal (private) messaging platforms
- **Multiple AI Models**: GPT-5, Claude, Gemini, Grok, DeepSeek, and more
- **Team-Based Access Control**: Organize users with hierarchical permissions (User, Team Lead, Admin)
- **Usage Tracking & Quotas**: Comprehensive logging with daily/monthly quota management
- **Database Migrations**: Alembic-powered schema migrations
- **Single Container Deployment**: API + Telegram bot in one container for K8s

## Quick Start

### 1. Install Poetry and Dependencies

```bash
# Install Poetry (Python dependency manager)
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
export PATH="$HOME/.local/bin:$PATH"

# Configure Poetry to use Python 3.11+
poetry env use python3.11

# Install project dependencies
poetry install
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Required environment variables:**
- `ENVIRONMENT`: Environment name (`dev`, `stage`, `prod`) - Controls database selection and optimizations
- `DB_USER`, `DB_PASSWORD`: PostgreSQL credentials
- `TELEGRAM_BOT_TOKEN`: Bot token from @BotFather
- `AI_SERVICE_URL`: Your AI service endpoint

### 3. Run Database Migrations

```bash
# Apply all pending migrations
poetry run alembic upgrade head
```

### 4. Start the Service

```bash
# Run with auto-reload (development)
make run

# Or run directly with Poetry
poetry run uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

The service will be available at:
- **API**: `http://localhost:3000/api/v1/`
- **Docs** (Swagger UI): `http://localhost:3000/docs`
- **ReDoc**: `http://localhost:3000/redoc`
- **Health Check**: `http://localhost:3000/health`

## Project Structure

```
Arash-Bot/
├── app/
│   ├── api/                    # API routes (main, admin)
│   ├── core/                   # Configuration, constants
│   ├── models/                 # Database models & schemas
│   ├── services/               # Business logic
│   └── main.py                 # FastAPI app + Telegram bot
├── alembic/                    # Database migrations
│   └── versions/               # Migration files
├── scripts/                    # CLI admin tools
├── telegram_bot/               # Telegram bot handlers
├── manifests/                  # Kubernetes deployment configs
│   ├── dev/
│   ├── stage/
│   └── prod/
├── .env.example                # Environment template
├── alembic.ini                 # Alembic configuration
├── pyproject.toml              # Poetry dependencies
├── Makefile                    # Development commands
└── README.md
```

## Database Management

### Migrations with Alembic

```bash
# Create a new migration (auto-generated)
make migrate-create MSG="Add new column to users table"

# Apply pending migrations
make migrate-up

# Rollback last migration
make migrate-down

# View migration status
make migrate-status
```

### Team & API Key Management

```bash
# Create a team
make db-team-create NAME="Engineering" DAILY=1000 MONTHLY=30000

# Create an admin API key
make db-key-create TEAM=1 NAME="Admin Key" LEVEL=admin

# List teams and keys
make db-teams
make db-keys
```

## Development Commands

```bash
# Install dependencies
make install                    # Install dependencies with Poetry

# Run application
make run                        # Run on port 3000

# Code quality
make test                       # Run pytest tests
make lint                       # Check code with ruff
make format                     # Format code with black
make clean                      # Remove cache files

# Database
make migrate-up                 # Apply migrations
make db-teams                   # List teams
make db-keys                    # List API keys
make db-team-create             # Create new team
make db-key-create              # Create new API key

# Docker
make docker-build               # Build Docker image
make docker-run                 # Run Docker container
```

## API Documentation

### API v1 Structure

All API endpoints are prefixed with `/api/v1/` for versioning support.

### Core Endpoints

- `GET /health` - Health check (unversioned for backward compatibility)
- `POST /api/v1/message` - Process a message (Requires API key)
- `GET /api/v1/sessions` - List team's active sessions (Requires API key)
- `GET /api/v1/session/{id}` - Get session details (Requires API key)
- `DELETE /api/v1/session/{id}` - Delete session (Requires API key)

### Admin Endpoints (Requires Admin Access)

**Platform Information:**
- `GET /api/v1/admin/` - Platform details and service info (Admin only)
- `GET /api/v1/admin/platforms` - Full platform configurations (Admin only)
- `GET /api/v1/admin/stats` - Cross-team statistics (Admin only)

**Team Management:**
- `POST /api/v1/admin/teams` - Create team (Admin only)
- `GET /api/v1/admin/teams` - List teams (Admin only)
- `PATCH /api/v1/admin/teams/{id}` - Update team (Admin only)

**API Key Management:**
- `POST /api/v1/admin/api-keys` - Create API key (Admin only)
- `GET /api/v1/admin/api-keys` - List API keys (Team Lead+)
- `DELETE /api/v1/admin/api-keys/{id}` - Revoke key (Admin only)

**Usage Tracking:**
- `GET /api/v1/admin/usage/team/{id}` - Team usage stats (Team Lead+)
- `GET /api/v1/admin/usage/api-key/{id}` - Key usage stats (Team Lead+)

Full API documentation available at:
- Swagger UI: `http://localhost:3000/docs`
- ReDoc: `http://localhost:3000/redoc`
- OpenAPI JSON: `http://localhost:3000/openapi.json`

## Telegram Bot Commands

- `/start` - Welcome message
- `/help` - Show available commands
- `/status` - Show session status
- `/clear` - Clear conversation history
- `/model` - Switch AI model
- `/models` - List available models

## Logging Configuration

The service uses a comprehensive logging system with dual timestamp support (UTC + Iranian/Jalali calendar), color-coded output, and structured key-value logging.

### Quick Configuration

```bash
# In your .env file:
LOG_LEVEL=DEBUG                # DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_TIMESTAMP=both             # utc | ir | both
LOG_COLOR=auto                 # auto | true | false
LOG_TIMESTAMP_PRECISION=6      # 3 (ms) | 6 (μs)
```

### Timestamp Modes

**UTC Only (`LOG_TIMESTAMP=utc`):**
```
[2025-11-08 11:04:40.401000 UTC][info] server_started port=8080
```

**Iranian Only (`LOG_TIMESTAMP=ir`):**
```
[1404-08-17 14:34:40.403000 IR][info] server_started port=8080
```

**Both (`LOG_TIMESTAMP=both`):**
```
[2025-11-08 11:04:40.404000 UTC][1404-08-17 14:34:40.404000 IR][info] server_started port=8080
```

### Demo and Testing

```bash
# Run interactive timestamp mode demo
python3 demo_timestamp_modes.py

# Run comprehensive logging tests
python3 tests/test_logging.py

# Or use make command
make demo-logging
```

For complete logging documentation, see [LOGGING.md](LOGGING.md)

## Configuration

### Environment-Based Configuration (DevOps-Friendly)

**All configuration uses generic variables set by DevOps per deployment:**

**Application Behavior Settings:**
- Log level: `LOG_LEVEL` (DEBUG/INFO/WARNING)
- API documentation: `ENABLE_API_DOCS` (true/false)
- CORS settings: `CORS_ORIGINS` (*/domains)

**Infrastructure Settings:**
- Database: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- Redis: `REDIS_URL`
- Service endpoints: `AI_SERVICE_URL`

**Environment Identifier:**
- `ENVIRONMENT` (dev/stage/prod) - Used only for logging/monitoring

```bash
# DevOps sets ALL parameters per deployment in K8s ConfigMap/Secret:
ENVIRONMENT=dev   # For logging/monitoring only

# Application behavior (DevOps sets per deployment)
LOG_LEVEL=DEBUG   # DevOps sets: DEBUG/INFO/WARNING
ENABLE_API_DOCS=true   # DevOps sets: true for dev/stage, false for prod
CORS_ORIGINS=*   # DevOps sets: "*" for dev/stage, domains for prod

# Infrastructure (DevOps sets per deployment)
DB_HOST=dev-db.cluster.local
DB_PORT=5432
DB_USER=arash_dev
DB_PASSWORD=<from-k8s-secret>
DB_NAME=arash_dev
```

**Why this design?**
1. **Less work**: DevOps sets ~8 core params per deployment (not ~24 with per-environment duplicates)
2. **More secure**: Each environment only has credentials it needs
3. **K8s-friendly**: Works perfectly with ConfigMaps/Secrets
4. **Simpler**: Same variable names everywhere, just different VALUES per deployment
5. **Flexible**: Easy to add new environments without code changes

### Database Configuration

**Generic parameters** (set by DevOps per deployment):

```bash
# These are the SAME variable names in all environments
# DevOps sets different VALUES per deployment

# In dev K8s deployment:
DB_HOST=localhost
DB_USER=arash_dev
DB_PASSWORD=dev_pass
DB_NAME=arash_dev

# In stage K8s deployment:
DB_HOST=stage-db.cluster.local
DB_USER=arash_stage
DB_PASSWORD=stage_pass
DB_NAME=arash_stage

# In prod K8s deployment:
DB_HOST=prod-db.cluster.local
DB_USER=arash_prod
DB_PASSWORD=prod_pass
DB_NAME=arash_prod
```

**Security**: Each environment only has the credentials it needs. No prod credentials in dev!

### Configuration Variables

**All settings are generic variables set by DevOps per deployment:**

| Setting | Variable | dev | stage | prod |
|---------|----------|-----|-------|------|
| **Log Level** | LOG_LEVEL | DEBUG | INFO | WARNING |
| **API Docs** | ENABLE_API_DOCS | true | true | false |
| **CORS** | CORS_ORIGINS | * | * | Specific domains |
| **DB Host** | DB_HOST | localhost / dev-db.local | stage-db.cluster.local | prod-db.cluster.local |
| **DB User** | DB_USER | arash_dev | arash_stage | arash_prod |
| **DB Password** | DB_PASSWORD | From K8s Secret | From K8s Secret | From K8s Secret |
| **DB Name** | DB_NAME | arash_dev | arash_stage | arash_prod |

**ENVIRONMENT variable:**
- Used only for logging/monitoring to identify which environment is running
- Does NOT control application behavior (use specific variables above)
- Code can check `settings.is_production`, `settings.is_development`, `settings.is_staging`

### Benefits

1. **DevOps-Friendly** ✅
   - ~8 core parameters per deployment (not ~24 with duplicates)
   - Same variable names across all environments
   - Works perfectly with K8s ConfigMaps/Secrets
   - Easy to add new environments (just different VALUES)

2. **More Secure** ✅
   - Each environment only has credentials it needs
   - No prod credentials in dev environment
   - No dev credentials in prod environment

3. **Kubernetes-Ready** ✅
   - Works with cluster service names
   - ConfigMap for non-sensitive config (LOG_LEVEL, CORS_ORIGINS, etc.)
   - Secrets for passwords (DB_PASSWORD, API keys)

4. **Simpler for Everyone** ✅
   - Less configuration to manage
   - Less chance of errors
   - Easier to understand and maintain

### Using Settings in Code

Developers can write environment-aware code:

```python
from app.core.config import settings

# Access database settings (DevOps sets these)
db_host = settings.DB_HOST        # Generic variable
db_user = settings.DB_USER        # Generic variable
db_name = settings.DB_NAME        # Generic variable

# Environment checks (application behavior)
if settings.is_production:
    # Production-only logic
    setup_production_monitoring()
elif settings.is_development:
    # Development-only features
    enable_debug_toolbar()

# Access application settings (DevOps sets these per deployment)
log_level = settings.LOG_LEVEL            # Generic variable (DEBUG/INFO/WARNING)
api_docs_enabled = settings.ENABLE_API_DOCS  # Generic variable (true/false)
cors = settings.cors_origins_list         # Parsed from CORS_ORIGINS

# Debug features
if settings.enable_debug_features:
    # Only runs in development
    log_detailed_metrics()
```

### Platform Configurations

**Telegram (Public):**
- Default Model: Gemini 2.0 Flash
- Rate Limit: 20 messages/minute
- History: 10 messages max

**Internal (Private):**
- Default Model: GPT-5 Chat
- Rate Limit: 60 messages/minute
- History: 30 messages max
- Requires API key authentication

## Deployment

### Docker Deployment

```bash
# Build image
make docker-build

# Run container
docker run --rm --env-file .env -p 3000:3000 arash-external-api:latest
```

### Kubernetes Deployment

K8s manifests are provided for dev/stage/prod environments:

```bash
# Deploy to development
kubectl apply -f manifests/dev/

# Deploy to staging
kubectl apply -f manifests/stage/

# Deploy to production
kubectl apply -f manifests/prod/
```

**Deployment URLs:**
- Dev: https://arash-api-dev.irisaprime.ir
- Stage: https://arash-api-stage.irisaprime.ir
- Prod: https://arash-api.irisaprime.ir

### Production Checklist

**Application Configuration (in code/ConfigMap):**
- [ ] Set `ENVIRONMENT=prod` in K8s deployment
- [ ] Set `LOG_LEVEL_PROD=WARNING` (or ERROR)
- [ ] Set `ENABLE_API_DOCS_PROD=false`
- [ ] Set `CORS_ORIGINS_PROD` to specific domains (no `*`)

**Infrastructure (DevOps - K8s ConfigMap/Secret):**
- [ ] Set `DB_HOST` to production database server
- [ ] Set `DB_PORT` (usually 5432)
- [ ] Set `DB_USER` with production database user
- [ ] Set `DB_PASSWORD` from K8s Secret
- [ ] Set `DB_NAME` (e.g., arash_prod)
- [ ] Set `REDIS_URL` if using Redis
- [ ] Set `TELEGRAM_BOT_TOKEN` from K8s Secret

**Database Setup:**
- [ ] Run migrations: `ENVIRONMENT=prod make migrate-up`
- [ ] Create initial teams and API keys
- [ ] Test quota enforcement

**Monitoring:**
- [ ] Set up log rotation
- [ ] Configure production monitoring
- [ ] Verify log level is WARNING or ERROR

**Testing:**
- [ ] Test locally with `ENVIRONMENT=prod` first
- [ ] Verify API docs are disabled
- [ ] Verify CORS restrictions work
- [ ] Test database connectivity

## Security

- **Database-Only API Keys**: All authentication uses database-backed API keys (no legacy fallback)
- **API Key Hashing**: SHA256, never stored in plain text
- **Team Isolation**: Complete session and data isolation between teams
- **Session Key Isolation**: Team ID included in session keys to prevent collision
- **Two-Tier Access Control**: ADMIN (super admins - full access) and TEAM (external clients - chat only)
- **Rate Limiting**: Per-user and per-team quota enforcement
- **Input Validation**: Pydantic models for all inputs
- **API Versioning**: All endpoints at `/api/v1/` for future compatibility
- **Environment Variables**: All secrets in `.env` file or K8s Secrets

For detailed security architecture, see [SECURITY.md](SECURITY.md)

## Troubleshooting

### Database Connection Issues

```bash
# Check database connection
make migrate-status

# Verify environment variables
cat .env | grep DB_
```

### Migration Issues

```bash
# View migration history
make migrate-status

# Rollback if needed
make migrate-down

# Reapply migrations
make migrate-up
```

### Application Issues

```bash
# View logs
tail -f logs/arash_api_service.log

# Run tests
make test

# Check configuration
curl http://localhost:3000/health
```

## License

MIT

## Acknowledgments

- FastAPI - Web framework
- python-telegram-bot - Telegram integration
- SQLAlchemy - Database ORM
- Alembic - Database migrations
- PostgreSQL - Production database
