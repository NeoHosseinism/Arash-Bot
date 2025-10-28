# Arash External API Service v1.1

Enterprise-ready AI chatbot service with integrated Telegram bot, team-based access control, and multi-platform support.

## Features

- **Multi-Platform Support**: Telegram (public) and Internal (private) messaging platforms
- **Multiple AI Models**: GPT-5, Claude, Gemini, Grok, DeepSeek, and more
- **Team-Based Access Control**: Organize users with hierarchical permissions (User, Team Lead, Admin)
- **Usage Tracking & Quotas**: Comprehensive logging with daily/monthly quota management
- **Database Migrations**: Alembic-powered schema migrations
- **Single Container Deployment**: API + Telegram bot in one container for K8s

## Quick Start

### 1. Install Dependencies

```bash
# Install Poetry (if not installed)
make install-poetry

# Install project dependencies
make install
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
- `INTERNAL_API_KEY`: Secure random key (min 32 characters)
- `AI_SERVICE_URL`: Your AI service endpoint

### 3. Run Database Migrations

```bash
# Apply all pending migrations
make migrate-up

# Check migration status
make migrate-status
```

### 4. Start the Service

```bash
# Run with auto-reload (development)
make run-dev

# Run in production mode
make run
```

The service will be available at:
- API: `http://localhost:3000`
- Docs: `http://localhost:3000/docs`

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
make install                    # Install dependencies
make install-dev                # Install with dev dependencies

# Run application
make run                        # Run on port 3000
make run-dev                    # Run with auto-reload

# Code quality
make test                       # Run pytest tests
make lint                       # Check code with ruff
make format                     # Format code with black
make clean                      # Remove cache files

# Docker
make docker-build               # Build Docker image
make docker-run                 # Run Docker container
make docker-push                # Push to registry

# Kubernetes deployment
make k8s-deploy-dev             # Deploy to dev
make k8s-deploy-stage           # Deploy to staging
make k8s-deploy-prod            # Deploy to production
```

## API Documentation

### Core Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health status
- `POST /message` - Process a message

### Admin Endpoints (Requires Authentication)

**Team Management:**
- `POST /admin/teams` - Create team (Admin only)
- `GET /admin/teams` - List teams
- `PATCH /admin/teams/{id}` - Update team (Admin only)

**API Key Management:**
- `POST /admin/api-keys` - Create API key (Admin only)
- `GET /admin/api-keys` - List API keys (Team Lead+)
- `DELETE /admin/api-keys/{id}` - Revoke key (Admin only)

**Usage Tracking:**
- `GET /admin/usage/team/{id}` - Team usage stats (Team Lead+)
- `GET /admin/usage/api-key/{id}` - Key usage stats (Team Lead+)

Full API documentation available at `http://localhost:3000/docs`

## Telegram Bot Commands

- `/start` - Welcome message
- `/help` - Show available commands
- `/status` - Show session status
- `/clear` - Clear conversation history
- `/model` - Switch AI model
- `/models` - List available models

## Configuration

### Comprehensive Environment-Based Configuration

The application uses the `ENVIRONMENT` variable as a **master switch** that controls ALL configuration settings. Every configurable parameter can be different per environment:

```bash
# Switch entire application configuration with ONE variable
ENVIRONMENT=dev      # Development configuration
ENVIRONMENT=stage    # Staging configuration
ENVIRONMENT=prod     # Production configuration
```

**What's controlled per environment:**
- **Database**: Host, port, user, password, database name
- **Logging**: Log level (DEBUG/INFO/WARNING)
- **API Docs**: Enable/disable Swagger UI
- **CORS**: Allowed origins
- **Redis**: Connection URLs
- **Features**: Debug mode, optimizations
- **More**: Easy to add new per-environment settings

### Database Configuration

**ALL database parameters** are environment-specific - each environment can use completely different databases:

```bash
# Development Database (localhost)
DB_HOST_DEV=localhost
DB_PORT_DEV=5432
DB_USER_DEV=arash_dev_user
DB_PASSWORD_DEV=dev_password
DB_NAME_DEV=arash_dev

# Staging Database (separate server)
DB_HOST_STAGE=staging-db.example.com
DB_PORT_STAGE=5432
DB_USER_STAGE=arash_stage_user
DB_PASSWORD_STAGE=stage_password
DB_NAME_STAGE=arash_stage

# Production Database (different server, different credentials)
DB_HOST_PROD=prod-db.example.com
DB_PORT_PROD=5432
DB_USER_PROD=arash_prod_user
DB_PASSWORD_PROD=prod_password
DB_NAME_PROD=arash_prod

# Switch databases by changing ENVIRONMENT
ENVIRONMENT=prod  # Automatically uses all prod settings
```

**Complete isolation**: Dev, staging, and prod can have entirely different infrastructure.

### Environment-Aware Features

The application automatically configures everything based on `ENVIRONMENT`:

| Setting | dev | stage | prod |
|---------|-----|-------|------|
| **DB Host** | localhost | staging-db.example.com | prod-db.example.com |
| **DB User** | arash_dev_user | arash_stage_user | arash_prod_user |
| **DB Password** | dev_password | stage_password | prod_password |
| **DB Name** | arash_dev | arash_stage | arash_prod |
| **Log Level** | DEBUG | INFO | WARNING |
| **API Docs** | Enabled | Enabled | Disabled |
| **CORS** | * (all) | * (all) | Specific domains |
| **Redis** | None | staging-redis | prod-redis |
| **Debug Features** | Enabled | Disabled | Disabled |

### Benefits

1. **Maximum Flexibility** ✅
   - Every setting can be different per environment
   - Easy to add new per-environment configurations
   - Complete infrastructure isolation

2. **Simple to Use** ✅
   - Change ONE variable (`ENVIRONMENT`) to switch everything
   - No manual configuration management
   - Less error-prone than multiple variables

3. **Enterprise-Ready** ✅
   - Dev uses local database
   - Stage uses staging server with staging credentials
   - Prod uses production server with prod credentials
   - Each environment completely isolated

4. **Developer-Friendly** ✅
   - Code can check `settings.is_production`, `settings.is_development`
   - Auto-optimizations based on environment
   - Properties like `settings.db_host`, `settings.log_level` return correct values

### Using Environment Settings in Code

Developers can write environment-aware code:

```python
from app.core.config import settings

# Access environment-specific database settings
db_host = settings.db_host        # Returns correct host based on ENVIRONMENT
db_user = settings.db_user        # Returns correct user based on ENVIRONMENT
db_name = settings.db_name        # Returns correct database name

# Environment checks
if settings.is_production:
    # Production-only logic
    setup_production_monitoring()
elif settings.is_development:
    # Development-only features
    enable_debug_toolbar()

# Get environment-aware settings
log_level = settings.log_level            # DEBUG/INFO/WARNING based on env
api_docs_enabled = settings.enable_api_docs  # true/false based on env
cors = settings.cors_origins_list         # Different origins per env

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

- [ ] **Set ENVIRONMENT**: Set `ENVIRONMENT=prod` in `.env` or K8s config
- [ ] **Database Configuration**:
  - [ ] Configure `DB_HOST_PROD` to production database server
  - [ ] Set `DB_USER_PROD` with production database user
  - [ ] Set `DB_PASSWORD_PROD` with secure production password
  - [ ] Verify `DB_NAME_PROD` points to production database
- [ ] **Security Settings**:
  - [ ] Generate secure `INTERNAL_API_KEY` (32+ characters)
  - [ ] Set `CORS_ORIGINS_PROD` to specific allowed domains (no `*`)
  - [ ] Verify `ENABLE_API_DOCS_PROD=false` (disabled for security)
  - [ ] Configure production Redis URL if using (`REDIS_URL_PROD`)
- [ ] **Database Setup**:
  - [ ] Run database migrations with `ENVIRONMENT=prod make migrate-up`
  - [ ] Create initial teams and API keys
  - [ ] Test quota enforcement
- [ ] **Monitoring**:
  - [ ] Verify `LOG_LEVEL_PROD=WARNING` or `ERROR`
  - [ ] Set up log rotation
  - [ ] Configure production monitoring
- [ ] **Testing**:
  - [ ] Test with `ENVIRONMENT=prod` locally first
  - [ ] Verify all prod settings are correct
  - [ ] Check API docs are disabled
  - [ ] Verify CORS restrictions work

## Security

- **API Key Hashing**: SHA256, never stored in plain text
- **Access Levels**: Hierarchical permissions (User → Team Lead → Admin)
- **Rate Limiting**: Per-user and per-team quota enforcement
- **Input Validation**: Pydantic models for all inputs
- **Environment Variables**: All secrets in `.env` file

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
