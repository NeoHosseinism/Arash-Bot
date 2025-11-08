# Security Architecture - API v1

## Team Isolation & Authentication

This service implements comprehensive team isolation to ensure that each team can ONLY access their own data.

### Core Security Principles

1. **Database-Only Authentication**: All API keys are database-backed (no legacy fallback)
2. **Team Isolation**: Every session is tagged with `team_id` and `api_key_id`
3. **Session Key Isolation**: Team ID included in session keys to prevent collision
4. **Required Authentication**: All endpoints (except `/health`) require API key authentication
5. **Admin-Only Sensitive Endpoints**: Platform details and cross-team statistics are admin-only
6. **Telegram Bot Hidden**: Internal teams cannot discover the Telegram bot exists
7. **API Versioning**: All endpoints at `/api/v1/` for future compatibility

---

## Endpoint Security Matrix

### Public Endpoints (No Auth Required)

| Endpoint | Purpose | Security Notes |
|----------|---------|----------------|
| `GET /health` | Health check | Does NOT expose platform details |

### Authenticated Endpoints (API Key Required)

| Endpoint | Auth Level | Team Isolation | Notes |
|----------|-----------|----------------|-------|
| `POST /api/v1/message` | USER | ✅ Yes | Session tagged with team_id |
| `GET /api/v1/sessions` | USER | ✅ Yes | Returns ONLY team's sessions |
| `GET /api/v1/session/{id}` | USER | ✅ Yes | Access denied if session belongs to another team |
| `DELETE /api/v1/session/{id}` | USER | ✅ Yes | Can only delete own team's sessions |

### Admin-Only Endpoints

| Endpoint | Auth Level | Exposes Telegram | Notes |
|----------|-----------|------------------|-------|
| `GET /api/v1/admin/` | ADMIN | ✅ Yes | Platform details including Telegram |
| `GET /api/v1/admin/platforms` | ADMIN | ✅ Yes | Full platform configurations |
| `GET /api/v1/admin/stats` | ADMIN | ✅ Yes | Cross-team statistics |
| `POST /api/v1/admin/clear-sessions` | ADMIN | N/A | Can clear any sessions |
| `POST /api/v1/admin/teams` | ADMIN | No | Team management |
| `POST /api/v1/admin/api-keys` | ADMIN | No | API key management |
| `GET /api/v1/admin/usage/*` | TEAM_LEAD | No | Usage statistics |

### Removed Endpoints

| Endpoint | Status | Notes |
|----------|--------|-------|
| `/webhook/{platform}` | ❌ REMOVED | Completely removed from codebase - not needed |
| `/api/v1/admin/webhook/{platform}` | ❌ REMOVED | Completely removed from codebase - not needed |

---

## Team Isolation Implementation

### Session Model

```python
class ChatSession(BaseModel):
    # ... existing fields ...

    # Team isolation fields - CRITICAL for security
    team_id: int | None = None  # Team that owns this session
    api_key_id: int | None = None  # API key used to create this session
    api_key_prefix: str | None = None  # For logging/debugging
```

### Session Creation Flow

1. **API Request** → `/api/v1/message` endpoint with `Authorization: Bearer <api_key>`
2. **Authentication** → `verify_api_key()` validates and returns API key object (database only)
3. **Team Extraction** → Extract `team_id`, `api_key_id`, `api_key_prefix` from API key
4. **Session Key Generation** → Session key includes team_id: `platform:team_id:chat_id`
5. **Session Creation** → Session tagged with team info
6. **Isolation Enforced** → All future operations check team ownership

### Session Key Collision Prevention

**Problem**: Two teams with same `chat_id` could share sessions

**Solution**: Include `team_id` in session key

```python
# Session key format
def get_session_key(self, platform: str, chat_id: str, team_id: int | None = None) -> str:
    if team_id is not None:
        return f"{platform}:{team_id}:{chat_id}"  # Team isolated
    return f"{platform}:{chat_id}"  # Telegram bot (no team_id)
```

**Example**:
- Team A, chat_id="user123" → Session key: `internal:100:user123`
- Team B, chat_id="user123" → Session key: `internal:200:user123`
- Different keys = Different sessions ✅

### Session Access Control

When a team requests `/sessions`:
```python
# SECURITY: Only get sessions for THIS team
team_id = api_key.team_id
team_sessions = session_manager.get_sessions_by_team(team_id)
```

When accessing a specific session:
```python
# SECURITY: Check team ownership
if session.team_id != api_key.team_id:
    raise HTTPException(403, "Access denied: This session belongs to another team")
```

---

## Authentication Levels

### AccessLevel Hierarchy

```python
class AccessLevel(Enum):
    USER = "user"  # Can use service, access own sessions
    TEAM_LEAD = "team_lead"  # Can view team usage stats
    ADMIN = "admin"  # Full access including platform details
```

### Permission Matrix

| Operation | USER | TEAM_LEAD | ADMIN |
|-----------|------|-----------|-------|
| Send messages | ✅ | ✅ | ✅ |
| View own sessions | ✅ | ✅ | ✅ |
| View team usage stats | ❌ | ✅ | ✅ |
| Create teams | ❌ | ❌ | ✅ |
| Create API keys | ❌ | ❌ | ✅ |
| View platform details | ❌ | ❌ | ✅ |
| View cross-team stats | ❌ | ❌ | ✅ |

---

## API Key Authentication

### How It Works

1. Client sends: `Authorization: Bearer sk_live_abc123...`
2. `verify_api_key()` dependency:
   - Validates key hash against database (SHA256)
   - Checks if key is active and not expired
   - Verifies required access level (USER/TEAM_LEAD/ADMIN)
   - Returns validated `APIKey` object with team info
3. Endpoint receives authenticated `api_key` object with team info
4. All operations are tagged with `team_id`, `api_key_id`, `api_key_prefix`

### No Legacy Authentication

**This service uses database-only authentication.** All API keys must be:
- Generated via `/api/v1/admin/api-keys` endpoint (by admin)
- OR created via `scripts/manage_api_keys.py` CLI tool
- Stored in PostgreSQL with SHA256 hash
- Associated with a team

There is **no fallback authentication method** for better security and team isolation.

---

## Telegram Bot Isolation

### Problem
Internal teams should NOT know that a Telegram bot exists.

### Solution

1. **Admin-Only Endpoints**: Platform details moved to `/admin/*`
2. **No Public Exposure**: `/health` endpoint doesn't mention platforms
3. **Team Isolation**: Internal teams only see their own `internal` platform sessions
4. **Statistics**: Cross-platform stats (including Telegram) are admin-only

### What Internal Teams See

**Before** (INSECURE):
```json
GET /platforms
{
  "telegram": {"type": "public", "model": "Gemini 2.0 Flash"},  // ❌ EXPOSED
  "internal": {"type": "private", "models": [...]}
}
```

**After** (SECURE):
```
GET /api/v1/platforms → 404 Not Found (endpoint doesn't exist)
GET /api/v1/admin/platforms → 403 Forbidden (requires ADMIN access)
```

Only administrators with ADMIN-level API keys can access platform information.

---

## Database Security

### API Key Storage

- Keys are hashed with SHA256 before storage
- Only first 8 characters (`key_prefix`) stored for identification
- Actual key value NEVER stored in database
- Keys are generated with cryptographically secure randomness

### Team Data Isolation

- Each API key belongs to ONE team
- Sessions are tagged with `team_id`
- Usage logs track `team_id` and `api_key_id`
- Complete audit trail per team

---

## Usage Tracking & Auditing

Every API request is logged with:
- `team_id`: Which team made the request
- `api_key_id`: Which key was used
- `session_id`: Which session was accessed
- `platform`: Always "internal" for API access
- `model_used`: Which AI model processed the request
- `success`: Whether request succeeded
- `timestamp`: When request occurred

This enables:
- ✅ Per-team usage tracking
- ✅ Per-key usage tracking
- ✅ Quota enforcement
- ✅ Security auditing
- ✅ Billing/chargeback per team

---

## Security Best Practices

### For DevOps

1. **Separate API Keys**: Each team should have their own API keys
2. **Principle of Least Privilege**: Grant USER level by default
3. **Rotate Keys**: Implement key rotation policy
4. **Monitor Usage**: Track usage logs for anomalies
5. **Secure Storage**: Store API keys in secrets management (K8s Secrets, Vault)

### For Developers

1. **Never Log API Keys**: Only log `key_prefix` (first 8 chars)
2. **Always Check Team Ownership**: Before accessing sessions/data
3. **Use Dependencies**: Leverage `verify_api_key()`, `require_admin_access()`
4. **Validate Input**: Don't trust client-provided `team_id`
5. **Fail Secure**: Default to denying access on errors

---

## Security Evolution

### Previous System (Removed)
- Single `INTERNAL_API_KEY` for all teams (REMOVED in v1.1)
- Optional team isolation (FIXED)
- Session key collision between teams (FIXED)
- Platform details publicly exposed (FIXED)

### Current System (v1.1+)
- Database-only API keys (no legacy fallback)
- Mandatory team isolation on all operations
- Session keys include team_id to prevent collision
- Platform details admin-only
- API versioning at `/api/v1/` for future compatibility

### Changes in v1.1

1. ✅ **Removed ALL legacy authentication** - Database API keys only
2. ✅ **Fixed session key collision** - Team ID included in session keys
3. ✅ **Added team ownership checks** - All admin usage endpoints verify team
4. ✅ **Added API versioning** - All endpoints at `/api/v1/`
5. ✅ **Strengthened team isolation** - No way to bypass team checks

---

## Testing Team Isolation

### Test Scenario 1: Session Access

```bash
# Team A creates session
curl -X POST /api/v1/message \
  -H "Authorization: Bearer <team_a_key>" \
  -d '{"platform": "internal", "user_id": "user1", ...}'
# Returns: session_id = "abc123"

# Team B tries to access Team A's session
curl -X GET /api/v1/session/abc123 \
  -H "Authorization: Bearer <team_b_key>"
# Expected: 403 Forbidden - "This session belongs to another team"
```

### Test Scenario 2: Session Listing

```bash
# Team A lists sessions
curl -X GET /api/v1/sessions \
  -H "Authorization: Bearer <team_a_key>"
# Expected: Only Team A's sessions returned

# Team B lists sessions
curl -X GET /api/v1/sessions \
  -H "Authorization: Bearer <team_b_key>"
# Expected: Only Team B's sessions returned (no overlap with Team A)
```

### Test Scenario 3: Platform Discovery

```bash
# Internal team tries to discover platforms
curl -X GET /api/v1/platforms \
  -H "Authorization: Bearer <team_user_key>"
# Expected: 404 Not Found (endpoint doesn't exist)

# Admin accesses platform details
curl -X GET /api/v1/admin/platforms \
  -H "Authorization: Bearer <admin_key>"
# Expected: 200 OK with Telegram + Internal platform details
```

---

## Security Checklist (v1.1)

- [x] **Database-only authentication** - No legacy fallback
- [x] **API key authentication required** on all sensitive endpoints
- [x] **Session key isolation** - Team ID included in session keys
- [x] **Team isolation enforced** in sessions and data access
- [x] **Teams cannot access other teams' sessions** - Ownership checks enforced
- [x] **Teams cannot see other teams' statistics** - Team filtering on all usage endpoints
- [x] **Telegram bot hidden** from internal teams
- [x] **Platform details are admin-only** - Moved to `/api/v1/admin/*`
- [x] **Webhook endpoints completely removed** - Not needed, code cleaned
- [x] **Usage tracking logs team_id** for all requests
- [x] **API keys are SHA256 hashed** before storage
- [x] **Session access checks team ownership** before returning data
- [x] **Statistics endpoints enforce team isolation** - Team leads see only own team
- [x] **Admin endpoints require ADMIN access level** - Hierarchical permissions
- [x] **API versioning** - All endpoints at `/api/v1/`

---

## Threat Model

### Threats Mitigated

✅ **Team A accessing Team B's sessions** → Prevented by team ownership checks
✅ **Discovering Telegram bot existence** → Admin-only endpoints
✅ **Accessing cross-team statistics** → Admin-only
✅ **API key theft** → Keys are hashed, can be revoked
✅ **Privilege escalation** → Access levels enforced at dependency level

### Remaining Risks

⚠️ **Admin key compromise** → Admin has full access (by design). Mitigation: Rotate admin keys regularly, monitor usage logs
⚠️ **Database compromise** → Key hashes exposed. Mitigation: Use strong API keys (32+ chars), encrypt database at rest
⚠️ **Memory-based session access** → Sessions in-memory not persisted. Mitigation: Acceptable for stateless design, sessions expire after timeout
⚠️ **API v1 breaking changes** → Future v2 may break clients. Mitigation: Maintain v1 compatibility, communicate deprecation timeline

---

## Contact

For security issues or questions:
- Review this document
- Check endpoint authentication in `app/api/dependencies.py`
- Review team isolation in `app/api/routes.py` and `app/services/session_manager.py`
