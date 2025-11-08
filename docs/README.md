# Documentation Directory

This directory contains organized documentation for the Arash External API Service v1.0.

## Directory Structure

### 📦 archive/
Historical documentation preserved for reference but no longer actively maintained.

- **IMPLEMENTATION_PLAN.md** - Original implementation plan (1,896 lines)
- **TEAM_NAMING_FEATURE.md** - Team naming feature documentation (feature implemented)

### 🔐 security/
Security-related documentation and reviews.

- **SECURITY.md** - Security architecture and best practices
- **SECURITY_REVIEW_v1.0.md** - Comprehensive security audit and checklist

### 🚀 deployment/
Deployment guides and configurations.

- **DOCKER.md** - Docker and Kubernetes deployment guide

### 💻 development/
Developer resources and AI assistant guides.

- **CLAUDE.md** - Instructions for Claude Code AI when working with this repository

## Accessing Documentation

### From Root Directory

Important documentation files have symlinks in the root directory for easy access:
- `DOCKER.md` → `docs/deployment/DOCKER.md`
- `CLAUDE.md` → `docs/development/CLAUDE.md`

### Main Documentation Index

See [DOCS.md](../DOCS.md) in the root directory for the complete documentation index and navigation guide.

## Active vs Archived

**Active Documentation** (in root):
- README.md - Main documentation
- ARCHITECTURE.md - System architecture
- API_ENDPOINTS.md - API reference
- SECURITY.md - Security guidelines
- LOGGING.md - Logging configuration

**Archived Documentation** (in docs/archive/):
- Historical planning documents
- Implemented feature documentation
- Legacy guides no longer in active use

## Contributing to Documentation

When updating documentation:

1. **Active documentation** should be in the root directory
2. **Specialized documentation** should be in appropriate docs/ subdirectories
3. **Historical documentation** should be moved to docs/archive/
4. Update [DOCS.md](../DOCS.md) when adding new documentation
5. Keep the root directory clean - only essential, active documentation

## Documentation Standards

- Use Markdown format (.md)
- Include table of contents for long documents
- Keep documentation up-to-date with code changes
- Use clear, concise language
- Include examples where applicable
- Update version numbers when making significant changes

## Quick Navigation

### Get Started
- [Main README](../README.md) - Project overview and quick start
- [DOCS.md](../DOCS.md) - Complete documentation index

### Development
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System design
- [API_ENDPOINTS.md](../API_ENDPOINTS.md) - API reference
- [LOGGING.md](../LOGGING.md) - Logging configuration

### Deployment & Security
- [DOCKER.md](deployment/DOCKER.md) - Docker/Kubernetes deployment
- [SECURITY.md](security/SECURITY.md) - Security guidelines
- [SECURITY_REVIEW_v1.0.md](security/SECURITY_REVIEW_v1.0.md) - Security audit

### Historical Reference
- [IMPLEMENTATION_PLAN.md](archive/IMPLEMENTATION_PLAN.md) - Original plan
- [TEAM_NAMING_FEATURE.md](archive/TEAM_NAMING_FEATURE.md) - Feature docs

---

**Version:** 1.0.0
**Last Updated:** 2025-11-08
**For the complete documentation index, see [DOCS.md](../DOCS.md)**
