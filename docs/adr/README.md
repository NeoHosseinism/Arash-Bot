# Architecture Decision Records (ADR)

## Purpose

Track important architectural decisions with context and rationale. Helps avoid repeating discussions and onboards new team members faster.

## When to Create an ADR

Create an ADR for decisions about:
- Architecture (microservices, monolith, session management)
- Technology choices (frameworks, libraries, tools)
- Data models and storage strategies
- Security approaches
- Performance strategies

**Don't create ADRs for:**
- Bug fixes
- Minor refactoring
- Routine dependency updates
- Configuration changes

## ADR Index

| ADR | Title | Impact | Date | Status |
|-----|-------|--------|------|--------|
| [001](./001-dependency-management-uv.md) | Migration from Poetry to uv | High | 2025-01-14 | ✅ Accepted |
| [002](./002-test-coverage-strategy.md) | Test Coverage Improvement Strategy | Medium | 2025-01-14 | ✅ Accepted |
| [003](./003-user-based-session-architecture.md) | User-Based Session Architecture | High | 2025-01-15 | ✅ Accepted |

## Status Lifecycle

```
Proposed → Accepted → Deprecated → Superseded
         ↘ Rejected
```

- **Proposed:** Under discussion
- **Accepted:** Approved and implemented
- **Deprecated:** No longer recommended but still in use
- **Superseded:** Replaced by newer ADR
- **Rejected:** Considered but not chosen

## Creating a New ADR

1. Copy template: `cp 000-adr-template.md 00X-your-title.md`
2. Use sequential numbering (001, 002, 003...)
3. Keep it concise - focus on **why** not **what**
4. Update this index when done

## Template Structure

```markdown
# ADR-XXX: Title

**Status:** Proposed | Accepted | Deprecated
**Date:** YYYY-MM-DD
**Impact:** Low | Medium | High

## Context
What's the problem?

## Decision
What did we decide?

## Consequences
What are the tradeoffs?

## Implementation
Key technical details
```

---

**Last Updated:** 2025-01-15
