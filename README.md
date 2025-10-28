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

### Environment-Based Configuration

The application uses the `ENVIRONMENT` variable to automatically select the correct database and apply environment-specific optimizations:

```bash
# Switch between environments by changing one variable
ENVIRONMENT=dev      # Uses arash_dev database, DEBUG log level
ENVIRONMENT=stage    # Uses arash_stage database, INFO log level
ENVIRONMENT=prod     # Uses arash_prod database, WARNING log level
```

**Benefits:**
- **Simple switching**: DevOps only changes one variable
- **Less error-prone**: All database names predefined in configuration
- **Environment-aware**: Code automatically optimizes based on environment
- **Centralized**: All environment configs in one place

### Database Configuration

Database names are **predefined** for each environment in `.env`:

```bash
# PostgreSQL connection (same for all environments)
DB_HOST=localhost
DB_PORT=5432
DB_USER=arash_user
DB_PASSWORD=your_password

# Predefined database names
DB_NAME_DEV=arash_dev
DB_NAME_STAGE=arash_stage
DB_NAME_PROD=arash_prod

# ENVIRONMENT variable determines which database to use
ENVIRONMENT=dev  # Change this to switch databases
```

**Database connection is built automatically** from individual parameters - no need to manually construct connection strings.

### Environment-Aware Features

The application automatically adjusts behavior based on `ENVIRONMENT`:

| Feature | dev | stage | prod |
|---------|-----|-------|------|
| **Database** | arash_dev | arash_stage | arash_prod |
| **Log Level** | DEBUG | INFO | WARNING |
| **API Docs** | Enabled | Enabled | Optional |
| **Debug Features** | Enabled | Disabled | Disabled |

You can override log level by setting `LOG_LEVEL` explicitly in `.env`.

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

- [ ] Configure PostgreSQL database (provided by DevOps)
- [ ] Set `ENVIRONMENT=prod` in `.env`
- [ ] Verify `DB_NAME_PROD` points to production database
- [ ] Run database migrations with `make migrate-up`
- [ ] Generate secure `INTERNAL_API_KEY` (32+ characters)
- [ ] Create initial teams and API keys
- [ ] Set `ENABLE_API_DOCS=false` (optional, for security)
- [ ] Configure CORS origins (don't use `*`)
- [ ] Set up log rotation
- [ ] Test quota enforcement
- [ ] Verify log level is WARNING or ERROR

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
