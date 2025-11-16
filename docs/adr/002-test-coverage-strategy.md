# ADR-002: Test Coverage Improvement Strategy

**Status:** Accepted
**Date:** 2025-01-14
**Impact:** Medium

---

## Context

Initial test coverage was 53% overall with critical services poorly tested:
- `command_processor.py`: 12%
- `usage_tracker.py`: 28%
- `session_manager.py`: 60%
- `message_processor.py`: 34%

## Decision

Target high-value services first, not 100% coverage everywhere. Focus on business logic, not infrastructure code.

**Prioritization:**
1. Critical services (session, auth, quota) → 95%+
2. Business logic (commands, messages) → 80%+
3. Infrastructure (main.py, logging) → best effort

## Consequences

### Positive
- **79% overall coverage** (up from 53%)
- **10 services at 100% coverage**
- Critical paths fully tested
- Fast test execution (22s for 326 tests)
- Confidence for production deployment

### Negative
- Infrastructure code remains partially tested
- Requires discipline to maintain coverage

## Implementation

**Test Organization:**
```
tests/
├── test_sessions.py          (37 tests, 100% coverage)
├── test_usage_tracker.py     (21 tests, 100% coverage)
├── test_command_processor.py (35 tests, 99% coverage)
├── test_message_processor.py (19 tests, 67% coverage)
└── test_comprehensive.py     (27 integration tests)
```

**Coverage Achieved:**
- ✅ session_manager: 60% → 100%
- ✅ usage_tracker: 28% → 100%
- ✅ command_processor: 12% → 99%
- ✅ api_key_manager: 99%
- ✅ platform_manager: 100%

**Testing Patterns:**
- Use pytest fixtures for common setups
- Mock external dependencies (DB, AI service)
- Test error paths, not just happy paths
- Focus on edge cases (None values, empty lists)

---

**Related:** ADR-001 (uv enabled faster test runs)
