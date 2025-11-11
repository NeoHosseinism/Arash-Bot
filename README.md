# Arash Bot

Enterprise AI chatbot service with Telegram bot integration and multi-model support.

## Quick Start

```bash
# 1. Install dependencies
poetry install

# 2. Setup environment
cp .env.example .env
# Edit .env: Set DB credentials, bot token, AI service URL, super admin keys

# 3. Run database migrations
make migrate-up

# 4. Start service
make run
```

**Service:** http://localhost:3000
**API Docs:** http://localhost:3000/docs

---

## What It Does

- **Multi-AI Models**: GPT-5, Claude, Gemini, Grok, DeepSeek
- **Dual Platform**: Public Telegram bot + Private API with team isolation
- **Authentication**: Two-tier (super admins via env vars, teams via database)
- **Usage Tracking**: Logs requests, tokens, costs per team
- **Rate Limiting**: Configurable quotas per team
- **Single Container**: FastAPI + Telegram bot in one deployment

---

## Essential Commands

```bash
# Development
make run              # Start with auto-reload (port 3000)
make test             # Run tests
make lint             # Check code quality
make format           # Format code with Black

# Database
make migrate-up       # Apply pending migrations
make migrate-create   # Create new migration
make db-teams         # List all teams
make db-keys          # List all API keys

# Deployment
make docker-build     # Build container image
kubectl apply -f manifests/prod/  # Deploy to Kubernetes
```

---

## Configuration

Key environment variables in `.env`:

```bash
# Database (required)
DB_HOST=localhost
DB_PORT=5432
DB_USER=arash_dev
DB_PASSWORD=your_password
DB_NAME=arash_dev

# AI Service (required)
AI_SERVICE_URL=https://ai-service.example.com

# Super Admin Keys (comma-separated)
SUPER_ADMIN_API_KEYS=admin_key_1,admin_key_2

# Telegram Bot (optional)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
RUN_TELEGRAM_BOT=true

# Application
LOG_LEVEL=INFO
ENABLE_API_DOCS=true
```

---

## Architecture

```
Telegram Users  →  ┌──────────────────┐
Internal Apps   →  │  Arash Bot       │  →  AI Service
                   │  (FastAPI + Bot)  │
                   └─────────┬─────────┘
                             ↓
                        PostgreSQL
                        (Teams, Keys, Usage)
```

**Session Isolation**: `platform:team_id:chat_id` format prevents team data collision.

---

## API Usage

### Public Endpoint (Team API Key)
```bash
curl -X POST http://localhost:3000/v1/chat \
  -H "Authorization: Bearer <team-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "text": "سلام"}'
```

### Admin Endpoint (Super Admin Key)
```bash
# Create team
curl -X POST http://localhost:3000/v1/admin/teams \
  -H "Authorization: Bearer <super-admin-key>" \
  -H "Content-Type: application/json" \
  -d '{"platform_name": "Internal-BI", "monthly_quota": 100000, "daily_quota": 5000}'
```

---

## Deployment

**Docker:**
```bash
docker build -t arash-bot .
docker run --env-file .env -p 3000:3000 arash-bot
```

**Kubernetes:**
```bash
kubectl apply -f manifests/prod/
```

Health checks: `/health` endpoint on port 3000

---

## Development Guide

📖 **Detailed documentation:** See [CLAUDE.md](CLAUDE.md)

The CLAUDE.md file contains:
- Complete project architecture
- Development commands and workflows
- Database schema and migrations
- Code structure and patterns
- Testing guidelines
- Deployment procedures

---

## License

MIT
