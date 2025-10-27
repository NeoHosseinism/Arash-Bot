# Arash External API Service v1.0

A professional, enterprise-ready external API service with advanced team-based API key management, usage tracking, and AI model integration. Supports Telegram (public) and Internal (private) messaging platforms.

## Features

### Core Capabilities
- **Multi-Platform Support**: Telegram (public) and Internal (private) platforms with platform-specific configurations
- **Multiple AI Models**: Support for 15+ AI models including GPT-5, Claude Opus 4, Gemini, Grok, DeepSeek, and more
- **User-Friendly Model Names**: Technical model IDs automatically hidden - users see "Gemini 2.0 Flash" instead of "google/gemini-2.0-flash-001"
  - Friendly names shown in all API responses, Telegram messages, and Swagger UI
  - Technical IDs only used internally when calling AI services
  - Supports friendly names, aliases, and technical IDs as input
- **Smart Rate Limiting**: Per-user, per-platform rate limiting with quota management
- **Session Management**: Automatic session cleanup and conversation history
- **Image Processing**: Support for image uploads and vision-enabled models

### Enterprise Features
- **Team-Based Access Control**: Organize users into teams with hierarchical permissions
- **Multi-Level API Keys**: User, Team Lead, and Admin access levels
- **Usage Tracking**: Comprehensive logging of all API requests with analytics
- **Quota Management**: Daily and monthly quotas per team or per API key
- **PostgreSQL Database**: Production-ready database with connection pooling and smart table detection
  - Automatically detects existing tables to prevent data loss
  - Clear terminal output showing which tables were created/skipped
  - PostgreSQL-only (SQLite no longer supported)
- **CLI Admin Tool**: Command-line interface for managing teams, keys, and monitoring usage

### Security & Monitoring
- **Confidential Logging**: No sensitive service information exposed in logs
- **SHA256 Key Hashing**: API keys securely hashed and never stored in plain text
- **Flexible Authentication**: Database-based keys with legacy fallback support
- **Usage Analytics**: Track requests, response times, model usage, and costs
- **Terminal-Friendly Output**: All logs use ASCII-only characters for Docker/Linux compatibility
  - No emojis in logs (user-facing messages still support emojis)
  - Clear status indicators: [OK], [ERROR], [WARNING], [INFO]

## Requirements

- Python 3.9+
- PostgreSQL 12+ (required)
- Telegram Bot Token (from @BotFather)
- AI Service Access
- Internal API Key (for private platform)

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd Arash-Bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and configure your settings
nano .env  # or use any text editor
```

**Important environment variables:**
- `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather
- `INTERNAL_API_KEY`: Secure random key (min 32 characters) for legacy auth
- `AI_SERVICE_URL`: Your AI service endpoint
- `DATABASE_URL`: PostgreSQL connection string (provided in .env.example)

### 3. Initialize Database

```bash
# Initialize the database and create tables
python scripts/manage_api_keys.py init
```

**Terminal Output Example (First Time):**
```
============================================================
Initializing Database Connection
============================================================
Initializing PostgreSQL connection: 37.32.8.181:31917/postgres
[OK] PostgreSQL engine created successfully
[OK] PostgreSQL connection successful
[INFO] No existing tables found, creating new schema...
[OK] Created new tables: api_keys, teams, usage_logs
[OK] Database schema is ready
============================================================
```

**Terminal Output Example (Existing Tables):**
```
============================================================
Initializing Database Connection
============================================================
Initializing PostgreSQL connection: 37.32.8.181:31917/postgres
[OK] PostgreSQL engine created successfully
[OK] PostgreSQL connection successful
[INFO] Found existing tables in database: api_keys, teams, usage_logs
[OK] Skipped existing tables: api_keys, teams, usage_logs
[OK] All required tables already exist in database
[OK] Database schema is ready
============================================================
```

### 4. Create Your First Team and API Key

```bash
# Create a team
python scripts/manage_api_keys.py team create "Engineering Team" \
    --description "Main engineering team" \
    --monthly-quota 50000

# Create an admin API key for the team
python scripts/manage_api_keys.py key create 1 "Admin Key" \
    --level admin \
    --description "Administrator access key"

# The command will output your API key - save it securely!
```

### 5. Run Services

```bash
# Terminal 1: Run FastAPI service
python run_service.py

# Terminal 2: Run Telegram bot (optional)
python run_bot.py
```

The FastAPI service will be available at `http://localhost:8001`
API docs available at `http://localhost:8001/docs`

## Project Structure

```
Arash-Bot/
├── app/
│   ├── api/
│   │   ├── routes.py              # Main API routes
│   │   ├── admin_routes.py        # Team & key management routes
│   │   └── dependencies.py        # Auth & validation
│   ├── core/
│   │   ├── config.py              # Configuration management
│   │   ├── constants.py           # Constants & messages
│   │   └── name_mapping.py        # Model name mappings
│   ├── models/
│   │   ├── database.py            # Database models (teams, keys, usage)
│   │   ├── schemas.py             # API schemas
│   │   └── session.py             # Session model
│   ├── services/
│   │   ├── ai_client.py           # AI service client
│   │   ├── api_key_manager.py     # API key management
│   │   ├── command_processor.py   # Command handler
│   │   ├── message_processor.py   # Message processing
│   │   ├── platform_manager.py    # Platform configs
│   │   ├── session_manager.py     # Session management
│   │   └── usage_tracker.py       # Usage tracking & quotas
│   ├── utils/
│   │   ├── helpers.py
│   │   ├── logger.py
│   │   └── parsers.py
│   └── main.py                    # FastAPI application
├── scripts/
│   └── manage_api_keys.py         # CLI admin tool
├── telegram_bot/
│   ├── bot.py                     # Bot setup
│   └── handlers.py                # Message handlers
├── tests/                         # Test files
├── .env.example                   # Environment template
├── requirements.txt
├── run_service.py                 # Service entry point
├── run_bot.py                     # Bot entry point
└── README.md
```

## Database Schema

The system uses PostgreSQL with three main tables:

### Tables
- **teams**: Team information, quotas, and settings
- **api_keys**: Hashed API keys with access levels and expiration
- **usage_logs**: Request logs with metadata (model, timing, success/failure)

**Note**: Chat conversation history is NOT stored in this database - it's handled by the AI service for scalability.

## Configuration

### Platform Configurations

#### Telegram (Public)
- **Default Model**: Gemini 2.0 Flash
- **Rate Limit**: 20 messages/minute
- **Commands**: `/start`, `/help`, `/status`, `/clear`, `/model`, `/models`
- **History**: 10 messages max
- **Model Switching**: Enabled (5 optimized models)
- **Authentication**: Not required

#### Internal (Private)
- **Default Model**: GPT-5 Chat
- **Available Models**: 11+ models (GPT-5, Claude, Gemini, Grok, etc.)
- **Rate Limit**: 60 messages/minute
- **Commands**: `/start`, `/help`, `/status`, `/clear`, `/model`, `/models`, `/settings`
- **History**: 30 messages max
- **Model Switching**: Enabled (full model catalog)
- **Authentication**: Required (API key)

### Available Models

Models are displayed with friendly names:

```
Gemini 2.0 Flash          (google/gemini-2.0-flash-001)
Gemini 2.5 Flash          (google/gemini-2.5-flash)
GPT-5 Chat                (openai/gpt-5-chat)
GPT-4.1                   (openai/gpt-4.1)
GPT-4o                    (openai/gpt-4o)
GPT-4o Mini               (openai/gpt-4o-mini)
GPT-4o Search             (openai/gpt-4o-search)
Claude Opus 4             (anthropic/claude-opus-4)
Claude Sonnet 4           (anthropic/claude-sonnet-4)
DeepSeek Chat V3          (deepseek/deepseek-chat-v3-0324)
DeepSeek R1               (deepseek/deepseek-r1)
Grok 4                    (x-ai/grok-4)
Llama 4 Maverick          (meta-llama/llama-4-maverick)
Mistral Large             (mistralai/mistral-large)
```

**Note:** Technical IDs (shown in parentheses) are used internally. Users only see and interact with friendly names.

### Bot Commands

All commands work with user-friendly model names and support multiple input formats:

#### Common Commands (Both Platforms)

- **`/start`** - Show welcome message with current model and platform info
- **`/help`** - Display all available commands and platform details
- **`/status`** - Show current session status, model, message count, and uptime
- **`/clear`** - Clear conversation history and start fresh
- **`/model`** - Switch AI model or list available models
  - Usage: `/model` (list all models) or `/model <name>` (switch model)
  - Accepts friendly names: `/model Gemini 2.0 Flash`
  - Accepts aliases: `/model gemini`, `/model deepseek`
  - Accepts technical IDs: `/model google/gemini-2.0-flash-001`
- **`/models`** - List all available models with aliases

#### Internal Platform Only

- **`/settings`** - View user settings and preferences

#### Model Aliases

Quick shortcuts for model switching:

**Telegram:**
- `gemini`, `flash` → Gemini 2.0 Flash
- `flash-2.5` → Gemini 2.5 Flash
- `deepseek`, `deep` → DeepSeek Chat V3
- `mini` → GPT-4o Mini
- `gemma` → Gemma 3 1B

**Internal:**
- `claude`, `sonnet` → Claude Sonnet 4
- `opus` → Claude Opus 4.5
- `gpt`, `gpt5` → GPT-5 Chat
- `gpt4` → GPT-4.1
- `mini` → GPT-4o Mini
- `search`, `web` → GPT-4o Search
- `gemini` → Gemini 2.5 Flash
- `grok` → Grok 4
- `deepseek` → DeepSeek Chat V3
- `llama` → Llama 4 Maverick

## API Key Management

### Access Levels

1. **USER**: Basic access to AI service
2. **TEAM_LEAD**: View team usage, manage team members
3. **ADMIN**: Full access - create teams, manage keys, view all usage

### CLI Tool Usage

#### Initialize Database
```bash
python scripts/manage_api_keys.py init
```

#### Team Management
```bash
# Create team
python scripts/manage_api_keys.py team create "Data Science" \
    --description "Data science team" \
    --daily-quota 1000 \
    --monthly-quota 30000

# List teams
python scripts/manage_api_keys.py team list
```

#### API Key Management
```bash
# Create API key
python scripts/manage_api_keys.py key create 1 "Production API" \
    --level admin \
    --description "Production deployment key" \
    --expires 365

# List keys
python scripts/manage_api_keys.py key list --team-id 1

# Revoke key
python scripts/manage_api_keys.py key revoke 5
```

#### Usage Monitoring
```bash
# View team usage
python scripts/manage_api_keys.py usage --team-id 1 --days 30

# View API key usage
python scripts/manage_api_keys.py usage --key-id 5 --days 7
```

## API Documentation

### Core Endpoints

#### Health & Info
- `GET /` - Health check with platform info
- `GET /health` - Detailed health check with service status
- `GET /platforms` - Get platform configurations
- `GET /stats` - Service statistics

#### Message Processing
- `POST /message` - Process a message
- `POST /webhook/{platform}` - Platform webhook handler

#### Session Management
- `GET /sessions` - List all sessions
- `GET /session/{session_id}` - Get specific session details
- `DELETE /session/{session_id}` - Delete session (admin only)
- `POST /admin/clear-sessions` - Clear all sessions (admin only)

### Admin API Endpoints

All admin endpoints require authentication and appropriate access level.

#### Team Management (Admin only)
- `POST /admin/teams` - Create team
- `GET /admin/teams` - List teams
- `GET /admin/teams/{id}` - Get team details
- `PATCH /admin/teams/{id}` - Update team

#### API Key Management
- `POST /admin/api-keys` - Create API key (Admin only)
- `GET /admin/api-keys` - List API keys (Team Lead+)
- `DELETE /admin/api-keys/{id}` - Revoke/delete key (Admin only)

#### Usage Tracking
- `GET /admin/usage/team/{id}` - Team usage stats (Team Lead+)
- `GET /admin/usage/api-key/{id}` - Key usage stats (Team Lead+)
- `GET /admin/usage/quota/{id}` - Check quota status (Team Lead+)
- `GET /admin/usage/recent` - Recent usage logs (Team Lead+)

### API Usage Examples

#### Send Message (with API Key)
```bash
curl -X POST http://localhost:8001/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ak_your_api_key_here" \
  -d '{
    "platform": "internal",
    "user_id": "user123",
    "chat_id": "chat456",
    "message_id": "msg789",
    "text": "What models are available?"
  }'
```

#### Create Team (Admin)
```bash
curl -X POST http://localhost:8001/admin/teams \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ak_admin_key_here" \
  -d '{
    "name": "Engineering Team",
    "description": "Main engineering team",
    "monthly_quota": 50000,
    "daily_quota": 2000
  }'
```

#### Get Usage Statistics
```bash
curl -X GET "http://localhost:8001/admin/usage/team/1?days=30" \
  -H "Authorization: Bearer ak_team_lead_key_here"
```

## Telegram Bot Commands

### Public Commands
- `/start` - Welcome message
- `/help` - Show available commands
- `/status` - Show session status
- `/translate [lang] [text]` - Translate text
- `/model [name]` - Switch AI model
- `/models` - List available models

### Private Commands (Internal Only)
- `/clear` - Clear conversation history
- `/summarize` - Summarize conversation
- `/settings` - User settings

## Security

### Best Practices Implemented

1. **API Key Hashing**: SHA256 hashing, keys never stored in plain text
2. **Access Control**: Hierarchical access levels with permission checks
3. **Rate Limiting**: Per-user and per-team quota enforcement
4. **Input Validation**: Pydantic models for all API inputs
5. **Database Security**: Parameterized queries, connection pooling
6. **Confidential Logging**: No service-specific information in logs
7. **Environment Variables**: All secrets in `.env` file
8. **CORS Configuration**: Configurable allowed origins

### Generating Secure Keys

```bash
# Generate a secure API key (for legacy INTERNAL_API_KEY)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate webhook secret
python -c "import secrets; print(secrets.token_hex(32))"
```

**Note**: For team-based access, use the CLI tool to generate API keys which are automatically hashed.

## Monitoring & Analytics

### Usage Tracking

The system tracks:
- **Request Count**: Total, successful, and failed requests
- **Model Usage**: Which models are being used by which teams
- **Response Times**: Average response time per request
- **Token Usage**: If provided by AI service
- **Cost Tracking**: Estimated costs (if configured)
- **Quota Status**: Current usage vs limits

### Logs

Logs are stored in `logs/arash_api_service.log`:

```bash
# View logs
tail -f logs/arash_api_service.log

# Search for errors
grep ERROR logs/arash_api_service.log

# Filter by team
grep "team_id=5" logs/arash_api_service.log
```

### Statistics Dashboard

```bash
# Get service statistics
curl http://localhost:8001/stats

# Get team usage (last 30 days)
python scripts/manage_api_keys.py usage --team-id 1 --days 30
```

## Testing

```bash
# Install test dependencies (already in requirements.txt)
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_ai_service.py -v
```

**Expected Output:**
```
================================= test session starts ==================================
platform linux -- Python 3.13.4, pytest-8.3.4, pluggy-1.6.0
collected 9 items

tests/test_ai_service.py::test_base_url_reachable PASSED               [ 11%]
tests/test_ai_service.py::test_health_endpoint SKIPPED                 [ 22%]
tests/test_ai_service.py::test_chat_endpoint_format PASSED             [ 33%]
...

======================= 8 passed, 1 skipped in 6.94s ==========================
```

**Note:** The `test_health_endpoint` test may be skipped if the AI service doesn't have a `/health` endpoint (returns 404). This is expected behavior.

**Pytest Configuration:**
- Async tests configured with `pytest-asyncio`
- Event loop scope set to `function` to avoid warnings
- Tests automatically skip if external services are unavailable

## Deployment

### PostgreSQL Setup

The system requires PostgreSQL for production. Connection details are in `.env.example`:

```bash
DATABASE_URL=postgresql://postgres:password@host:port/database
```

**Note:** PostgreSQL is required. SQLite is no longer supported.

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Initialize database on startup
CMD python scripts/manage_api_keys.py init && \
    python run_service.py
```

### Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: arash_api
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  bot-service:
    build: .
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://postgres:your_password@postgres:5432/arash_api
    env_file:
      - .env
    ports:
      - "8001:8001"
    volumes:
      - ./logs:/app/logs

volumes:
  postgres_data:
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Configure PostgreSQL database with backups
- [ ] Generate strong API keys (use CLI tool)
- [ ] Set up SSL/TLS certificates
- [ ] Configure reverse proxy (nginx/caddy)
- [ ] Set up log rotation
- [ ] Enable monitoring (Prometheus/Grafana recommended)
- [ ] Set `ENABLE_API_DOCS=false` for production
- [ ] Configure CORS origins (don't use `*`)
- [ ] Set up database connection pooling
- [ ] Initialize teams and API keys before launch
- [ ] Test quota enforcement
- [ ] Configure rate limits appropriately

## Troubleshooting

### Database Issues

**Connection failed**
```bash
# Test connection
python -c "from app.models.database import get_database; db = get_database(); print('OK' if db.test_connection() else 'FAILED')"

# Check connection string
echo $DATABASE_URL
```

**Tables not created**
```bash
# Manually initialize
python scripts/manage_api_keys.py init
```

### API Key Issues

**Invalid API key**
- Check key format (should start with `ak_`)
- Verify key is active: `python scripts/manage_api_keys.py key list`
- Check expiration date

**Permission denied**
- Verify access level: USER < TEAM_LEAD < ADMIN
- Check endpoint requirements in API docs

### Rate Limiting

**Quota exceeded**
```bash
# Check current usage
python scripts/manage_api_keys.py usage --team-id 1

# Increase quota
# (Update via database or recreate team with higher limits)
```

### Bot Not Responding

- Verify FastAPI service is running
- Check bot token in `.env`
- Review logs: `tail -f logs/arash_api_service.log`
- Test AI service connectivity

## Migration Guide

### From Previous Version

1. **Update environment variables**
   - Rename `OPENROUTER_SERVICE_URL` → `AI_SERVICE_URL`
   - Add `DATABASE_URL` for PostgreSQL

2. **Initialize database**
   ```bash
   python scripts/manage_api_keys.py init
   ```

3. **Create teams and migrate users**
   - Create teams for your organization
   - Generate API keys for each team
   - Update client applications with new keys

4. **Update API calls**
   - Add `Authorization: Bearer` header with new API keys
   - Update endpoint URLs if needed

## Recent Updates & Changes

### Version 1.1 (Latest)

**User-Friendly Model Names** 🎨
- All technical model IDs automatically hidden from users
- Users see "Gemini 2.0 Flash" instead of "google/gemini-2.0-flash-001"
- Friendly names shown in all API responses, Telegram messages, and Swagger UI
- Supports friendly names, aliases, and technical IDs as input
- `/model` command accepts multi-word names: `/model Gemini 2.0 Flash`

**PostgreSQL Improvements** 🗄️
- Removed SQLite support (PostgreSQL now required)
- Smart table detection prevents data loss
- Clear terminal output showing which tables exist/were created
- ASCII-friendly status indicators: `[OK]`, `[ERROR]`, `[WARNING]`, `[INFO]`
- Automatic .env loading in all scripts

**Command Updates** 🤖
- **Added** `/clear` command to Telegram platform
- **Removed** `/translate` command (was non-functional placeholder)
- **Removed** `/summarize` command (was non-functional placeholder)
- All commands now show friendly model names

**Testing Improvements** ✅
- Fixed pytest asyncio configuration warnings
- Health endpoint test now skips gracefully if unavailable
- Event loop fixture updated to pytest-asyncio standards
- No more deprecation warnings

**Terminal Compatibility** 🖥️
- All log output uses ASCII-only characters
- Works perfectly in Docker and basic Linux terminals
- User-facing messages (Telegram/API) still support emojis
- Clear status indicators replace emojis in logs

**Bug Fixes** 🐛
- Fixed DATABASE_URL warning on startup
- Fixed `/clear` command visibility in Telegram
- Fixed model name display in all endpoints
- Fixed pytest configuration for Python 3.13+

### Breaking Changes

⚠️ **Important:** If upgrading from a previous version:

1. **Update your `.env` file:**
   ```bash
   # Add 'clear' to Telegram commands
   TELEGRAM_COMMANDS=start,help,status,clear,model,models

   # Remove 'translate' from the list
   ```

2. **PostgreSQL is now required:**
   - SQLite is no longer supported
   - Update `DATABASE_URL` to use PostgreSQL connection string

3. **Model names have changed:**
   - API responses now return friendly names
   - Update any code that parses model names from responses
   - Technical IDs still accepted as input for backward compatibility

## Support

For issues or questions:

1. **Check logs**: `logs/arash_api_service.log`
2. **Review API docs**: `http://localhost:8001/docs`
3. **Test configuration**: `GET /platforms` and `GET /health`
4. **Usage analytics**: Use CLI tool to check team usage
5. **Database status**: Run `python scripts/manage_api_keys.py init` to verify

## License

[Your License Here]

## Acknowledgments

- FastAPI for the excellent web framework
- python-telegram-bot for Telegram integration
- SQLAlchemy for database ORM
- PostgreSQL for production database
- Pydantic for data validation