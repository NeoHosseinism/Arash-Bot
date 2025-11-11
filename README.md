# Arash Bot

AI chatbot service with Telegram bot and multi-model support (GPT, Claude, Gemini, Grok, DeepSeek).

## Quick Start

```bash
poetry install
cp .env.example .env  # Edit: DB, AI service URL, tokens
make migrate-up
make run              # http://localhost:3000
```

## Commands

```bash
make run              # Start server (port 3000)
make test             # Run tests
make lint             # Check code
make migrate-up       # Apply DB migrations
make docker-build     # Build container
```

## Config (.env)

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=arash
DB_PASSWORD=***
DB_NAME=arash_db

# AI Service
AI_SERVICE_URL=https://ai.example.com

# Auth
SUPER_ADMIN_API_KEYS=key1,key2
TELEGRAM_BOT_TOKEN=***
```

## API

```bash
# Chat (team key)
curl -X POST http://localhost:3000/v1/chat \
  -H "Authorization: Bearer <key>" \
  -d '{"user_id": "u1", "text": "سلام"}'

# Create team (admin key)
curl -X POST http://localhost:3000/v1/admin/teams \
  -H "Authorization: Bearer <admin-key>" \
  -d '{"platform_name": "Team1", "daily_quota": 1000}'
```

**Docs:** http://localhost:3000/docs

## Deploy

```bash
docker build -t arash-bot .
docker run --env-file .env -p 3000:3000 arash-bot
```

## License

MIT
