# Security Architecture

## Team Isolation & Authentication

This service implements comprehensive team isolation to ensure that each team can ONLY access their own data.

### Core Security Principles

1. **Team Isolation**: Every session is tagged with `team_id` and `api_key_id`
2. **Required Authentication**: All endpoints (except `/health`) require API key authentication
3. **Admin-Only Sensitive Endpoints**: Platform details and cross-team statistics are admin-only
4. **Telegram Bot Hidden**: Internal teams cannot discover the Telegram bot exists

---

## Endpoint Security Matrix

### Public Endpoints (No Auth Required)

| Endpoint | Purpose | Security Notes |
|----------|---------|----------------|
| `GET /health` | Health check | Does NOT expose platform details |

### Authenticated Endpoints (API Key Required)

| Endpoint | Auth Level | Team Isolation | Notes |
|----------|-----------|----------------|-------|
| `POST /message` | USER | ✅ Yes | Session tagged with team_id |
| `GET /sessions` | USER | ✅ Yes | Returns ONLY team's sessions |
| `GET /session/{id}` | USER | ✅ Yes | Access denied if session belongs to another team |
| `DELETE /session/{id}` | USER | ✅ Yes | Can only delete own team's sessions |

### Admin-Only Endpoints

| Endpoint | Auth Level | Exposes Telegram | Notes |
|----------|-----------|------------------|-------|
| `GET /admin/` | ADMIN | ✅ Yes | Platform details including Telegram |
| `GET /admin/platforms` | ADMIN | ✅ Yes | Full platform configurations |
| `GET /admin/stats` | ADMIN | ✅ Yes | Cross-team statistics |
| `POST /admin/clear-sessions` | ADMIN | N/A | Can clear any sessions |
| `POST /admin/teams` | ADMIN | No | Team management |
| `POST /admin/api-keys` | ADMIN | No | API key management |
| `GET /admin/usage/*` | TEAM_LEAD | No | Usage statistics |

### Disabled Endpoints

| Endpoint | Status | Notes |
|----------|--------|-------|
| `/webhook/{platform}` | Commented Out | Not in use - will be enabled later |
| `/admin/webhook/{platform}` | Commented Out | Not in use - will be enabled later |

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

1. **API Request** → `/message` endpoint with `Authorization: Bearer <api_key>`
2. **Authentication** → `verify_api_key()` validates and returns API key object
3. **Team Extraction** → Extract `team_id`, `api_key_id`, `api_key_prefix` from API key
4. **Session Creation** → Session tagged with team info
5. **Isolation Enforced** → All future operations check team ownership

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
   - Validates key hash against database
   - Checks if key is active and not expired
   - Verifies required access level
   - Returns validated `APIKey` object
3. Endpoint receives authenticated `api_key` object with team info

### Fallback Auth (Legacy)

For backward compatibility, the system falls back to `INTERNAL_API_KEY` from config if:
- Database is unavailable
- API key validation fails

**Note**: Legacy auth does NOT provide team isolation. Migrate to database API keys.

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
GET /platforms → 401 Unauthorized
GET /admin/platforms → 200 OK (admin only)
```

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

## Migration from Old System

### Old System (INSECURE)
- Single `INTERNAL_API_KEY` for all teams
- No team isolation
- All teams could see all sessions
- Platform details publicly exposed

### New System (SECURE)
- Per-team API keys with roles
- Complete team isolation
- Teams can only see own sessions
- Platform details admin-only

### Migration Steps

1. ✅ Create teams in database
2. ✅ Generate API keys for each team
3. ✅ Update clients to use new API keys
4. ✅ Verify team isolation working
5. ⚠️ Eventually deprecate `INTERNAL_API_KEY`

---

## Testing Team Isolation

### Test Scenario 1: Session Access

```bash
# Team A creates session
curl -X POST /message \
  -H "Authorization: Bearer <team_a_key>" \
  -d '{"platform": "internal", "user_id": "user1", ...}'
# Returns: session_id = "abc123"

# Team B tries to access Team A's session
curl -X GET /session/abc123 \
  -H "Authorization: Bearer <team_b_key>"
# Expected: 403 Forbidden - "This session belongs to another team"
```

### Test Scenario 2: Session Listing

```bash
# Team A lists sessions
curl -X GET /sessions \
  -H "Authorization: Bearer <team_a_key>"
# Expected: Only Team A's sessions returned

# Team B lists sessions
curl -X GET /sessions \
  -H "Authorization: Bearer <team_b_key>"
# Expected: Only Team B's sessions returned (no overlap with Team A)
```

### Test Scenario 3: Platform Discovery

```bash
# Internal team tries to discover platforms
curl -X GET /platforms \
  -H "Authorization: Bearer <team_user_key>"
# Expected: 401 Unauthorized (endpoint doesn't exist)

# Admin accesses platform details
curl -X GET /admin/platforms \
  -H "Authorization: Bearer <admin_key>"
# Expected: 200 OK with Telegram + Internal platform details
```

---

## Security Checklist

- [x] API key authentication required on all sensitive endpoints
- [x] Team isolation enforced in sessions
- [x] Teams cannot access other teams' sessions
- [x] Teams cannot see other teams' statistics
- [x] Telegram bot hidden from internal teams
- [x] Platform details are admin-only
- [x] Webhook endpoints commented out (not in use)
- [x] Usage tracking logs team_id for all requests
- [x] API keys are hashed before storage
- [x] Session access checks team ownership
- [x] Statistics endpoints enforce team isolation
- [x] Admin endpoints require ADMIN access level

---

## Threat Model

### Threats Mitigated

✅ **Team A accessing Team B's sessions** → Prevented by team ownership checks
✅ **Discovering Telegram bot existence** → Admin-only endpoints
✅ **Accessing cross-team statistics** → Admin-only
✅ **API key theft** → Keys are hashed, can be revoked
✅ **Privilege escalation** → Access levels enforced at dependency level

### Remaining Risks

⚠️ **Admin key compromise** → Admin has full access (by design)
⚠️ **Database compromise** → Key hashes exposed (use strong keys)
⚠️ **Memory-based session access** → Sessions in-memory not persisted

---

## Contact

For security issues or questions:
- Review this document
- Check endpoint authentication in `app/api/dependencies.py`
- Review team isolation in `app/api/routes.py` and `app/services/session_manager.py`
