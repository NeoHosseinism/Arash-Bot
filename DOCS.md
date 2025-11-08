# Documentation Index

Complete documentation for Arash External API Service v1.0

## Quick Start

- **[README.md](README.md)** - Main documentation, quick start guide, and overview
- **[.env.example](.env.example)** - Environment configuration template
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes

## Core Documentation

### Architecture & Design

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture, components, and design patterns
- **[API_ENDPOINTS.md](API_ENDPOINTS.md)** - Complete API endpoint reference

### Configuration

- **[LOGGING.md](LOGGING.md)** - Comprehensive logging guide
  - Dual timestamp support (UTC + Iranian/Jalali calendar)
  - Color-coded output
  - Structured key-value logging
  - Environment-specific configurations
  - Quick reference and examples

### Security

- **[SECURITY.md](SECURITY.md)** - Security architecture and best practices
  - API key management
  - Team isolation
  - Authentication & authorization
  - Rate limiting & quotas

## Deployment

- **[DOCKER.md](DOCKER.md)** → docs/deployment/DOCKER.md
  - Building images
  - Running containers
  - Docker Compose setup

- **[manifests/](manifests/)** - Kubernetes deployment configurations
  - `dev/` - Development environment
  - `stage/` - Staging environment
  - `prod/` - Production environment

## Developer Resources

### For Development

- **[CLAUDE.md](CLAUDE.md)** → docs/development/CLAUDE.md
  - Instructions for Claude Code AI
  - Development commands
  - Architecture overview
  - Common scenarios
  - Testing guidelines

- **[Makefile](Makefile)** - Development commands and automation
  - `make help` - Show all available commands
  - `make run` - Run the application
  - `make test` - Run test suite
  - `make migrate-up` - Apply database migrations

- **[pyproject.toml](pyproject.toml)** - Poetry dependency management
- **[alembic.ini](alembic.ini)** - Database migration configuration

### Testing & Demos

- **[demo_timestamp_modes.py](demo_timestamp_modes.py)** - Interactive logging timestamp mode demo
- **[tests/test_logging.py](tests/test_logging.py)** - Comprehensive logging examples and tests
- **[tests/](tests/)** - Full test suite
  - `test_api.py` - API endpoint tests
  - `test_commands.py` - Command processing tests
  - `test_sessions.py` - Session management tests
  - `test_ai_service.py` - AI service integration tests

## Additional Documentation

### Archive (Historical Reference)

- **[docs/archive/IMPLEMENTATION_PLAN.md](docs/archive/IMPLEMENTATION_PLAN.md)** - Original implementation plan (1,896 lines)
- **[docs/archive/TEAM_NAMING_FEATURE.md](docs/archive/TEAM_NAMING_FEATURE.md)** - Team naming feature documentation

### Security Deep Dive

- **[docs/security/SECURITY_REVIEW_v1.0.md](docs/security/SECURITY_REVIEW_v1.0.md)** - Comprehensive security audit
  - Team confidentiality checks
  - Data isolation verification
  - Security checklist

## Getting Help

1. **Start here**: [README.md](README.md) - Overview and quick start
2. **Configuration**: [LOGGING.md](LOGGING.md) - Logging setup
3. **API Reference**: [API_ENDPOINTS.md](API_ENDPOINTS.md) - All endpoints
4. **Security**: [SECURITY.md](SECURITY.md) - Security guidelines
5. **Deployment**: [DOCKER.md](DOCKER.md) - Docker & Kubernetes

## Online Resources

- **API Documentation (when running):**
  - Swagger UI: `http://localhost:3000/docs`
  - ReDoc: `http://localhost:3000/redoc`
  - OpenAPI JSON: `http://localhost:3000/openapi.json`

- **Health Check**: `http://localhost:3000/health`

## Documentation Organization

```
Root Directory:
├── README.md               # Main documentation
├── DOCS.md                 # This file - documentation index
├── CHANGELOG.md            # Version history
├── ARCHITECTURE.md         # System architecture
├── API_ENDPOINTS.md        # API reference
├── SECURITY.md             # Security guidelines
├── LOGGING.md              # Logging guide (consolidated)
├── DOCKER.md               # → docs/deployment/DOCKER.md (symlink)
├── CLAUDE.md               # → docs/development/CLAUDE.md (symlink)
└── docs/
    ├── archive/            # Historical documents
    │   ├── IMPLEMENTATION_PLAN.md
    │   └── TEAM_NAMING_FEATURE.md
    ├── security/           # Security documentation
    │   ├── SECURITY.md
    │   └── SECURITY_REVIEW_v1.0.md
    ├── deployment/         # Deployment guides
    │   └── DOCKER.md
    └── development/        # Developer resources
        └── CLAUDE.md
```

## Version Information

- **Current Version**: 1.0.0
- **Last Updated**: 2025-11-08
- **Python**: 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL with Alembic migrations

---

For questions or issues, refer to the troubleshooting section in [README.md](README.md).
