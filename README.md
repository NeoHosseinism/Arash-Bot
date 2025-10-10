# Arash Messenger Bot v1.0

A professional, scalable multi-platform chatbot service supporting Telegram (public) and Internal (private) messaging platforms with AI model integration via OpenRouter.

## 🌟 Features

- **Multi-Platform Support**: Telegram (public) and Internal (private) platforms
- **Multiple AI Models**: Support for 11+ AI models including GPT-5, Claude Sonnet 4, Gemini, Grok, and more
- **Platform-Specific Configuration**: Different models, rate limits, and features per platform
- **Smart Rate Limiting**: Per-user, per-platform rate limiting
- **Session Management**: Automatic session cleanup and conversation history
- **Image Processing**: Support for image uploads and vision models
- **Command System**: Extensible command processor with platform-aware access control
- **Production-Ready**: Proper error handling, logging, retry logic, and monitoring

## 📋 Requirements

- Python 3.9+
- Telegram Bot Token (from @BotFather)
- OpenRouter Service Access
- Internal API Key (for private platform)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd arash-messenger-bot

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

# Edit .env and fill in your credentials
nano .env  # or use any text editor
```

**Important:** Make sure to set:
- `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather
- `INTERNAL_API_KEY`: Generate a secure random key (min 32 characters)
- `OPENROUTER_SERVICE_URL`: Your OpenRouter service URL

### 3. Run Services

```bash
# Terminal 1: Run FastAPI service
python run_service.py

# Terminal 2: Run Telegram bot
python run_telegram_bot.py
```

The FastAPI service will be available at `http://localhost:8001`
API docs available at `http://localhost:8001/docs`

## 📁 Project Structure

```
arash-messenger-bot/
├── app/
│   ├── models/                 # Data models
│   │   ├── schemas.py          # Pydantic schemas
│   │   └── session.py          # Session model
│   ├── services/               # Business logic
│   │   ├── command_processor.py
│   │   ├── message_processor.py
│   │   ├── openrouter_client.py
│   │   ├── platform_manager.py
│   │   └── session_manager.py
│   ├── utils/                  # Utilities
│   │   ├── helpers.py
│   │   ├── logger.py
│   │   └── parsers.py
│   └── main.py                 # FastAPI application
├── telegram/                   # Telegram bot
│   ├── bot.py                  # Bot setup
│   ├── client.py               # Service client
│   └── handlers.py             # Message handlers
├── tests/                      # Test files
├── .env.example                # Environment template
├── .gitignore
├── requirements.txt
├── run_service.py              # Service entry point
├── run_telegram_bot.py                  # Bot entry point
└── README.md
```

## 🔧 Configuration

### Platform Configurations

#### Telegram (Public)
- **Model**: `google/gemini-2.0-flash-001` (fixed)
- **Rate Limit**: 20 messages/minute
- **Commands**: start, help, status, translate
- **History**: 10 messages max
- **Model Switching**: Disabled

#### Internal (Private)
- **Default Model**: `openai/gpt-5-chat`
- **Available Models**: 11 models (GPT-5, Claude, Gemini, Grok, etc.)
- **Rate Limit**: 60 messages/minute
- **Commands**: All commands available
- **History**: 30 messages max
- **Model Switching**: Enabled
- **Authentication**: Required

### Available Models

```
google/gemini-2.0-flash-001
deepseek/deepseek-chat-v3-0324
openai/gpt-4o-mini
google/gemma-3-1b-it
anthropic/claude-sonnet-4
openai/gpt-4.1
openai/gpt-4o-search-preview
x-ai/grok-4
meta-llama/llama-4-maverick
google/gemini-2.5-flash
openai/gpt-5-chat
```

### Model Aliases (for easier switching)

```
claude, sonnet → anthropic/claude-sonnet-4
gpt, gpt5 → openai/gpt-5-chat
gpt4 → openai/gpt-4.1
mini → openai/gpt-4o-mini
web, search → openai/gpt-4o-search-preview
gemini → google/gemini-2.5-flash
grok → x-ai/grok-4
deepseek → deepseek/deepseek-chat-v3-0324
llama → meta-llama/llama-4-maverick
```

## 📚 API Documentation

### Endpoints

#### Health & Info
- `GET /` - Health check with platform info
- `GET /health` - Detailed health check
- `GET /platforms` - Get platform configurations

#### Message Processing
- `POST /message` - Process a message
- `POST /webhook/{platform}` - Platform webhook handler

#### Session Management
- `GET /sessions` - List all sessions (auth required for details)
- `GET /session/{session_id}` - Get specific session
- `DELETE /session/{session_id}` - Delete session (admin only)

#### Statistics & Admin
- `GET /stats` - Service statistics
- `POST /admin/clear-sessions` - Clear sessions (admin only)

### Example: Send Message

```bash
curl -X POST http://localhost:8001/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "platform": "internal",
    "user_id": "user123",
    "chat_id": "chat456",
    "message_id": "msg789",
    "text": "Hello, what models are available?"
  }'
```

## 🤖 Telegram Bot Commands

### Public Commands (Telegram)
- `/start` - Welcome message
- `/help` - Show available commands
- `/status` - Show session status
- `/translate [lang] [text]` - Translate text

### Private Commands (Internal Only)
- `/model [name]` - Switch AI model
- `/models` - List available models
- `/clear` - Clear conversation history
- `/summarize` - Summarize conversation
- `/settings` - User settings

## 🔐 Security

### Best Practices Implemented

1. **Environment Variables**: All secrets in `.env` (never committed)
2. **API Key Authentication**: Required for internal platform
3. **Webhook Verification**: Optional webhook secret validation
4. **Rate Limiting**: Per-user, per-platform limits
5. **Input Validation**: Pydantic models for all inputs
6. **Error Handling**: Comprehensive error handling with logging
7. **CORS**: Configurable CORS origins

### Generating Secure Keys

```bash
# Generate a secure API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate webhook secret
python -c "import secrets; print(secrets.token_hex(32))"
```

## 📊 Monitoring

### Logs

Logs are stored in `logs/arash_bot_service.log` with rotation.

```bash
# View logs
tail -f logs/arash_bot_service.log

# Search for errors
grep ERROR logs/arash_bot_service.log
```

### Statistics API

```bash
# Get service statistics
curl http://localhost:8001/stats
```

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

## 🚢 Deployment

### Docker (Recommended)

```dockerfile
# Dockerfile example
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run both services
CMD ["sh", "-c", "python run_service.py & python run_telegram_bot.py"]
```

### Systemd Service

```ini
# /etc/systemd/system/arash-bot.service
[Unit]
Description=Arash Messenger Bot Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/arash-bot
Environment="PATH=/opt/arash-bot/venv/bin"
ExecStart=/opt/arash-bot/venv/bin/python run_service.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Generate strong API keys (min 32 characters)
- [ ] Configure CORS origins (don't use `*`)
- [ ] Set up SSL/TLS for webhooks
- [ ] Configure reverse proxy (nginx/caddy)
- [ ] Set up log rotation
- [ ] Enable monitoring (Prometheus/Grafana)
- [ ] Set up backups for session data
- [ ] Configure Redis for session persistence
- [ ] Set `ENABLE_API_DOCS=false` for production

## 🔄 Migration from Old Version

If you're migrating from the previous version:

1. **Update environment variables** - New `.env` format
2. **Update model names** - Some model IDs have changed
3. **Review API endpoints** - New endpoint structure
4. **Update client code** - New response format

## 🐛 Troubleshooting

### Bot not responding
- Check if FastAPI service is running
- Verify bot token in `.env`
- Check logs for errors
- Ensure bot service URL is correct

### Rate limit errors
- Increase rate limit in `.env`
- Check if user is being rate limited
- Review session cleanup intervals

### Model switching not working
- Verify platform is "internal"
- Check if model name is correct
- Use model aliases for easier switching

### Authentication failures
- Verify API key is correct
- Check Authorization header format
- Ensure internal platform authentication is enabled

## 📞 Support

For issues or questions:
1. Check the logs: `logs/arash_bot_service.log`
2. Review API docs: `http://localhost:8001/docs`
3. Check configuration: `GET /platforms`

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- FastAPI for the excellent framework
- python-telegram-bot for Telegram integration
- OpenRouter for AI model access