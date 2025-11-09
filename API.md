# API Reference

Complete API reference for Arash Bot service.

**Base URL:** `http://localhost:3000`
**API Version:** v1 (all endpoints at `/api/v1/`)

---

## Authentication

### Super Admin (Environment-Based)
```bash
Authorization: Bearer <SUPER_ADMIN_API_KEY>
```
Set via `SUPER_ADMIN_API_KEYS` environment variable. Used for `/api/v1/admin/*` endpoints.

### Team (Database-Based)
```bash
Authorization: Bearer <team_api_key>
```
Created by super admins via `/api/v1/admin/api-keys`. Used for `/api/v1/chat` endpoint.

---

## Public Endpoints

### Health Check

```
GET /health
```

**Auth:** None

**Response:**
```json
{
  "status": "healthy",
  "service": "Arash External API Service",
  "version": "1.1.0",
  "timestamp": "2025-11-01T12:34:56.789012"
}
```

**Example:**
```bash
curl http://localhost:3000/health
```

---

## Chat Endpoints

### Process Message

```
POST /api/v1/chat
Authorization: Bearer <team_api_key>
```

**Request:**
```json
{
  "platform": "internal",
  "user_id": "user123",
  "chat_id": "chat456",
  "message_id": "msg789",
  "text": "Hello, how are you?",
  "type": "text",
  "attachments": [],
  "metadata": {}
}
```

**Fields:**
- `platform` (required): Must be "internal" for API access
- `user_id` (required): Unique user identifier
- `chat_id` (required): Chat/conversation identifier
- `message_id` (required): Unique message identifier
- `text` (optional): Message text content
- `type` (optional): "text" | "image" | "audio" | "video" | "document"
- `attachments` (optional): List of attachments
- `metadata` (optional): Additional data

**Response:**
```json
{
  "success": true,
  "response": "I'm doing well, thank you! How can I help you today?",
  "data": {
    "session_id": "internal_100_chat456",
    "model": "GPT-5 Chat",
    "message_count": 5,
    "history_length": 10
  },
  "error": null
}
```

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Missing or invalid API key
- `403 Forbidden` - API key inactive/expired
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl -X POST http://localhost:3000/api/v1/chat \
  -H "Authorization: Bearer sk_live_YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "internal",
    "user_id": "user123",
    "chat_id": "chat456",
    "message_id": "msg001",
    "text": "Hello!"
  }'
```

---

## Admin Endpoints

**All admin endpoints require super admin API key.**

### Platform Information

#### Get Platform Info

```
GET /api/v1/admin/
Authorization: Bearer <super_admin_key>
```

**Response:**
```json
{
  "service": "Arash External API Service",
  "version": "1.1.0",
  "status": "healthy",
  "platforms": {
    "telegram": {
      "type": "public",
      "model": "Gemini 2.0 Flash",
      "rate_limit": 20,
      "model_switching": false
    },
    "internal": {
      "type": "private",
      "models": ["GPT-5 Chat", "Claude 4.5 Sonnet", "Gemini 2.5 Flash"],
      "rate_limit": 60,
      "model_switching": true
    }
  },
  "active_sessions": 42,
  "timestamp": "2025-11-01T12:34:56.789012"
}
```

#### Get Platform Configurations

```
GET /api/v1/admin/platforms
Authorization: Bearer <super_admin_key>
```

#### Get Service Statistics

```
GET /api/v1/admin/stats
Authorization: Bearer <super_admin_key>
```

**Response:**
```json
{
  "total_sessions": 100,
  "active_sessions": 42,
  "telegram": {
    "sessions": 60,
    "messages": 1200,
    "active": 25
  },
  "internal": {
    "sessions": 40,
    "messages": 800,
    "active": 17,
    "team_breakdown": [...]
  },
  "uptime_seconds": 86400
}
```

#### Clear Sessions

```
POST /api/v1/admin/clear-sessions?platform=<platform>
Authorization: Bearer <super_admin_key>
```

**Query Params:**
- `platform` (optional): Filter by "telegram" or "internal"

**Response:**
```json
{
  "success": true,
  "cleared": 42,
  "message": "Cleared 42 sessions"
}
```

---

### Team Management

#### Create Team

```
POST /api/v1/admin/teams
Authorization: Bearer <super_admin_key>
```

**Request:**
```json
{
  "name": "Engineering",
  "description": "Engineering team for internal projects",
  "monthly_quota": 10000,
  "daily_quota": 500
}
```

**Fields:**
- `name` (required): Team name (unique)
- `description` (optional): Team description
- `monthly_quota` (optional): Monthly request limit (null = unlimited)
- `daily_quota` (optional): Daily request limit (null = unlimited)

**Response:**
```json
{
  "id": 1,
  "name": "Engineering",
  "description": "Engineering team for internal projects",
  "monthly_quota": 10000,
  "daily_quota": 500,
  "is_active": true,
  "webhook_url": null,
  "webhook_enabled": false,
  "created_at": "2025-11-01T12:34:56.789012",
  "updated_at": "2025-11-01T12:34:56.789012"
}
```

#### List Teams

```
GET /api/v1/admin/teams?active_only=true
Authorization: Bearer <super_admin_key>
```

**Query Params:**
- `active_only` (optional, default=true): Filter active teams only

**Response:**
```json
[
  {
    "id": 1,
    "name": "Engineering",
    "monthly_quota": 10000,
    "daily_quota": 500,
    "is_active": true,
    "created_at": "2025-11-01T12:34:56.789012"
  },
  ...
]
```

#### Get Team Details

```
GET /api/v1/admin/teams/{team_id}
Authorization: Bearer <super_admin_key>
```

#### Update Team

```
PATCH /api/v1/admin/teams/{team_id}
Authorization: Bearer <super_admin_key>
```

**Request:**
```json
{
  "name": "Engineering Team",
  "description": "Updated description",
  "monthly_quota": 15000,
  "daily_quota": 750,
  "is_active": true
}
```

All fields are optional.

---

### API Key Management

#### Create API Key

```
POST /api/v1/admin/api-keys
Authorization: Bearer <super_admin_key>
```

**Request:**
```json
{
  "team_id": 1,
  "name": "Production API Key",
  "description": "Production environment key for external client",
  "monthly_quota": null,
  "daily_quota": null,
  "expires_in_days": 365
}
```

**Fields:**
- `team_id` (required): Team ID
- `name` (required): API key friendly name
- `description` (optional): Key description
- `monthly_quota` (optional): Override team monthly quota (null = use team quota)
- `daily_quota` (optional): Override team daily quota (null = use team quota)
- `expires_in_days` (optional): Expiration in days (null = never expires)

**Response:**
```json
{
  "api_key": "sk_live_EXAMPLE_KEY_REPLACE_WITH_REAL_KEY",
  "key_info": {
    "id": 1,
    "key_prefix": "sk_live_",
    "name": "Production API Key",
    "team_id": 1,
    "team_name": "Engineering",
    "monthly_quota": null,
    "daily_quota": null,
    "is_active": true,
    "expires_at": "2026-11-01T12:34:56.789012"
  },
  "warning": "Save this API key securely. It will not be shown again."
}
```

**IMPORTANT:** The `api_key` field is shown **only once**. Store it securely.

#### List API Keys

```
GET /api/v1/admin/api-keys?team_id=<team_id>
Authorization: Bearer <super_admin_key>
```

**Query Params:**
- `team_id` (optional): Filter by team ID

**Response:**
```json
[
  {
    "id": 1,
    "key_prefix": "sk_live_",
    "name": "Production API Key",
    "team_id": 1,
    "team_name": "Engineering",
    "monthly_quota": null,
    "daily_quota": null,
    "is_active": true,
    "created_at": "2025-11-01T12:34:56.789012",
    "last_used_at": "2025-11-01T15:30:00.000000",
    "expires_at": "2026-11-01T12:34:56.789012"
  },
  ...
]
```

#### Delete API Key

```
DELETE /api/v1/admin/api-keys/{key_id}?permanent=false
Authorization: Bearer <super_admin_key>
```

**Query Params:**
- `permanent` (optional, default=false): Permanently delete (true) or soft delete (false)

**Response:**
```json
{
  "message": "API key revoked successfully",
  "key_id": 1
}
```

**Examples:**
```bash
# Soft delete (revoke)
curl -X DELETE http://localhost:3000/api/v1/admin/api-keys/1 \
  -H "Authorization: Bearer <super_admin_key>"

# Hard delete (permanent)
curl -X DELETE "http://localhost:3000/api/v1/admin/api-keys/1?permanent=true" \
  -H "Authorization: Bearer <super_admin_key>"
```

---

### Usage Tracking

#### Get Team Usage

```
GET /api/v1/admin/usage/team/{team_id}?days=30
Authorization: Bearer <super_admin_key>
```

**Query Params:**
- `days` (optional, default=30): Number of days to include

**Response:**
```json
{
  "team_id": 1,
  "team_name": "Engineering",
  "period": {
    "start": "2025-10-02T00:00:00",
    "end": "2025-11-01T23:59:59",
    "days": 30
  },
  "requests": {
    "total": 1500,
    "successful": 1450,
    "failed": 50,
    "success_rate": 0.967
  },
  "tokens": {
    "total": 150000,
    "average_per_request": 100
  },
  "cost": {
    "total": 15.50,
    "currency": "USD"
  },
  "models": [
    {
      "model": "GPT-5 Chat",
      "requests": 1000,
      "tokens": 100000
    },
    ...
  ]
}
```

#### Get API Key Usage

```
GET /api/v1/admin/usage/api-key/{api_key_id}?days=30
Authorization: Bearer <super_admin_key>
```

Similar response format as team usage.

#### Check Quota Status

```
GET /api/v1/admin/usage/quota/{api_key_id}?period=daily
Authorization: Bearer <super_admin_key>
```

**Query Params:**
- `period` (optional, default="daily"): "daily" or "monthly"

**Response:**
```json
{
  "quota": 500,
  "used": 342,
  "remaining": 158,
  "exceeded": false,
  "period": "daily",
  "reset_at": "2025-11-02T00:00:00"
}
```

#### Get Recent Usage Logs

```
GET /api/v1/admin/usage/recent?team_id=1&limit=100
Authorization: Bearer <super_admin_key>
```

**Query Params:**
- `team_id` (optional): Filter by team ID
- `api_key_id` (optional): Filter by API key ID
- `limit` (optional, default=100): Maximum number of logs

**Response:**
```json
{
  "count": 10,
  "logs": [
    {
      "id": 1001,
      "api_key_id": 1,
      "api_key_name": "Production API Key",
      "team_id": 1,
      "team_name": "Engineering",
      "session_id": "internal_1_chat123",
      "platform": "internal",
      "model_used": "GPT-5 Chat",
      "success": true,
      "timestamp": "2025-11-01T15:30:00.000000"
    },
    ...
  ]
}
```

---

### Webhook Management

#### Configure Webhook

```
PUT /api/v1/admin/{team_id}/webhook
Authorization: Bearer <super_admin_key>
```

**Request:**
```json
{
  "webhook_url": "https://example.com/webhook",
  "webhook_secret": "my_secret_key_123",
  "webhook_enabled": true
}
```

**Fields:**
- `webhook_url` (optional): Webhook URL (must start with http:// or https://)
- `webhook_secret` (optional): Secret for HMAC signature
- `webhook_enabled` (optional, default=false): Enable/disable webhook

#### Test Webhook

```
POST /api/v1/admin/{team_id}/webhook/test
Authorization: Bearer <super_admin_key>
```

**Response:**
```json
{
  "team_id": 1,
  "team_name": "Engineering",
  "webhook_url": "https://example.com/webhook",
  "test_result": {
    "success": true,
    "status_code": 200,
    "response_time_ms": 123,
    "error": null
  }
}
```

#### Get Webhook Config

```
GET /api/v1/admin/{team_id}/webhook
Authorization: Bearer <super_admin_key>
```

**Response:**
```json
{
  "team_id": 1,
  "team_name": "Engineering",
  "webhook_url": "https://example.com/webhook",
  "webhook_secret_configured": true,
  "webhook_enabled": true
}
```

---

## Webhook Payload

When webhook is enabled, this payload is sent after each message:

**Method:** POST

**Headers:**
```
Content-Type: application/json
X-Webhook-Signature: sha256=<hmac_signature>
```

**Payload:**
```json
{
  "event": "message.completed",
  "timestamp": "2025-11-01T15:30:00.000000Z",
  "team_id": 1,
  "session_id": "internal_1_chat123",
  "message": {
    "user_id": "user123",
    "chat_id": "chat456",
    "text": "Hello, how are you?",
    "type": "text"
  },
  "response": {
    "success": true,
    "response": "I'm doing well, thank you!",
    "model": "GPT-5 Chat"
  }
}
```

**Signature Verification (Python):**
```python
import hmac
import hashlib
import json

def verify_signature(payload, signature, secret):
    expected = hmac.new(
        key=secret.encode('utf-8'),
        msg=json.dumps(payload, sort_keys=True).encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    return f"sha256={expected}" == signature
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Status Codes:**
- `400 Bad Request` - Invalid parameters
- `401 Unauthorized` - Missing/invalid authentication
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

---

## Rate Limiting

**Limits:**
- **Telegram**: 20 messages/minute per user
- **Internal**: 60 messages/minute per user
- **Teams**: Daily/monthly quotas configurable

**Rate Limit Response:**
```json
{
  "detail": "Rate limit exceeded. Please try again later.",
  "success": false,
  "error": "rate_limit_exceeded"
}
```

---

## Quick Examples

### Complete Flow

```bash
# 1. Create team (super admin)
curl -X POST http://localhost:3000/api/v1/admin/teams \
  -H "Authorization: Bearer super_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Engineering",
    "monthly_quota": 10000,
    "daily_quota": 500
  }'
# Response: {"id": 1, "name": "Engineering", ...}

# 2. Create API key for team (super admin)
curl -X POST http://localhost:3000/api/v1/admin/api-keys \
  -H "Authorization: Bearer super_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": 1,
    "name": "Production Key",
    "expires_in_days": 365
  }'
# Response: {"api_key": "sk_live_xxx...", ...}
# SAVE THIS KEY - shown only once!

# 3. Send chat message (team API key)
curl -X POST http://localhost:3000/api/v1/chat \
  -H "Authorization: Bearer sk_live_xxx..." \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "internal",
    "user_id": "user123",
    "chat_id": "chat456",
    "message_id": "msg001",
    "text": "Hello!"
  }'
# Response: {"success": true, "response": "Hi! How can I help?", ...}

# 4. Check usage (super admin)
curl -X GET "http://localhost:3000/api/v1/admin/usage/team/1?days=7" \
  -H "Authorization: Bearer super_admin_key"
# Response: {"team_id": 1, "requests": {...}, "tokens": {...}, ...}
```

---

## Interactive Documentation

When `ENABLE_API_DOCS=true`:

- **Swagger UI:** http://localhost:3000/docs
- **ReDoc:** http://localhost:3000/redoc
- **OpenAPI JSON:** http://localhost:3000/openapi.json

---

**For setup, deployment, and troubleshooting, see [README.md](README.md)**
