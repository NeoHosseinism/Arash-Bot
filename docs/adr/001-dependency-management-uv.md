# ADR-001: Migration from Poetry to uv

**Status:** Accepted
**Date:** 2025-01-14
**Impact:** High

---

## Context

Poetry was slow (2-5 min install times) and becoming a bottleneck for local development and CI/CD. With 46 dependencies, every environment setup was painful.

## Decision

Migrate to uv - an ultra-fast Python package installer written in Rust.

**Key Changes:**
- Convert `pyproject.toml` to PEP 621 standard format
- Replace `poetry.lock` with `uv.lock`
- Update Makefile and Dockerfile to use `uv` commands
- Change build backend from `poetry-core` to `setuptools`

## Consequences

### Positive
- **10-100x faster installs** (3 seconds vs 3 minutes)
- **60% faster Docker builds**
- **Faster CI/CD** (reduced pipeline times)
- Industry-standard PEP 621 format
- Better compatibility with modern Python tooling

### Negative
- Team needs to learn new tool (minimal learning curve)
- Poetry backup files need to be gitignored

## Implementation

```toml
# pyproject.toml (PEP 621 format)
[project]
name = "arash-bot"
version = "1.1.0"
requires-python = ">=3.11"
dependencies = [...]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

```bash
# Install
uv sync --all-extras

# Run tests
uv run pytest
```

**Migration Phases:**
1. ✅ Convert project files (pyproject.toml, lockfile)
2. ✅ Update tooling (Makefile, Dockerfile)
3. ✅ Validate (all 123 tests passing)

**Results:**
- Install time: 3 min → 3 sec
- Docker build: 60% faster
- All dependencies migrated successfully

---

**Related:** ADR-002 (test coverage validation)
