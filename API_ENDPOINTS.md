# API Endpoints Reference

Complete list of all API endpoints with request/response specifications.

---

## Table of Contents

1. [Unversioned Endpoints](#unversioned-endpoints)
2. [Public API v1 Endpoints](#public-api-v1-endpoints)
3. [Admin API v1 Endpoints](#admin-api-v1-endpoints)

---

## Unversioned Endpoints

### GET `/health`

**Description:** Health check endpoint (unversioned for monitoring compatibility)

**Authentication:** None required

**Request:** None

**Response:**
```json
{
  "status": "healthy" | "degraded",
  "service": "Arash External API Service",
  "version": "1.1.0",
  "timestamp": "2025-11-01T12:34:56.789012"
}
```

**Status Codes:**
- `200 OK`: Service is running

**Example:**
```bash
curl http://localhost:3000/health
```

---

## Public API v1 Endpoints

Base URL: `/api/v1/`

### POST `/api/v1/chat`

**Description:** Process a chat message

**Authentication:** Required (Bearer token)

**Request Body:**
```json
{
  "platform": "internal",
  "user_id": "user123",
  "chat_id": "chat456",
  "message_id": "msg789",
  "text": "Hello, how are you?",
  "type": "text",
  "attachments": [],
  "reply_to_message_id": null,
  "timestamp": "2025-11-01T12:34:56.789012",
  "metadata": {},
  "auth_token": null
}
```

**Request Fields:**
- `platform` (string, required): Must be "internal" for API access
- `user_id` (string, required): Unique user identifier
- `chat_id` (string, required): Chat/conversation identifier
- `message_id` (string, required): Unique message identifier
- `text` (string, optional): Message text content
- `type` (string, optional): Message type - "text", "image", "audio", "video", "document"
- `attachments` (array, optional): List of message attachments
- `reply_to_message_id` (string, optional): ID of message being replied to
- `timestamp` (datetime, optional): Message timestamp (auto-generated if not provided)
- `metadata` (object, optional): Additional metadata
- `auth_token` (string, optional): Legacy authentication token

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

**Response Fields:**
- `success` (boolean): Request success status
- `response` (string): AI-generated response text
- `data` (object): Additional response data
  - `session_id` (string): Session identifier
  - `model` (string): AI model used (friendly name)
  - `message_count` (int): Total messages in session
  - `history_length` (int): Messages in context
- `error` (string): Error message if success=false

**Status Codes:**
- `200 OK`: Message processed successfully
- `400 Bad Request`: Invalid platform or validation error
- `401 Unauthorized`: Missing or invalid API key
- `403 Forbidden`: API key inactive or expired
- `429 Too Many Requests`: Rate limit or quota exceeded
- `500 Internal Server Error`: Server error

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

## Admin API v1 Endpoints

Base URL: `/api/v1/admin/`

**SUPER ADMIN ONLY** - All admin endpoints require `access_level=admin` API key.

These endpoints are only accessible to super admins (internal team).
External teams (with `access_level=team`) cannot access these endpoints.

---

### Platform Information

### GET `/api/v1/admin/`

**Description:** Get platform information and service overview

**Authentication:** Required (Admin only)

**Request:** None

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
      "models": ["GPT-5 Chat", "Claude 3.5 Sonnet", "Gemini 2.5 Flash"],
      "rate_limit": 60,
      "model_switching": true
    }
  },
  "active_sessions": 42,
  "timestamp": "2025-11-01T12:34:56.789012"
}
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Missing API key
- `403 Forbidden`: Not admin

---

### GET `/api/v1/admin/platforms`

**Description:** Get detailed platform configurations

**Authentication:** Required (Admin only)

**Request:** None

**Response:**
```json
{
  "telegram": {
    "type": "public",
    "model": "Gemini 2.0 Flash",
    "rate_limit": 20,
    "commands": ["start", "help", "status", "clear", "model", "models"],
    "max_history": 10,
    "features": {
      "model_switching": false,
      "requires_auth": false
    }
  },
  "internal": {
    "type": "private",
    "default_model": "GPT-5 Chat",
    "available_models": ["GPT-5 Chat", "Claude 3.5 Sonnet", "Gemini 2.5 Flash"],
    "rate_limit": 60,
    "commands": ["help", "status", "clear", "model", "models"],
    "max_history": 30,
    "features": {
      "model_switching": true,
      "requires_auth": true
    }
  }
}
```

**Status Codes:**
- `200 OK`: Success
- `403 Forbidden`: Not admin

---

### GET `/api/v1/admin/stats`

**Description:** Get service-wide statistics

**Authentication:** Required (Admin only)

**Request:** None

**Response:**
```json
{
  "total_sessions": 100,
  "active_sessions": 42,
  "telegram": {
    "sessions": 60,
    "messages": 1200,
    "active": 25,
    "model": "Gemini 2.0 Flash"
  },
  "internal": {
    "sessions": 40,
    "messages": 800,
    "active": 17,
    "models_used": {
      "GPT-5 Chat": 25,
      "Claude 3.5 Sonnet": 15
    },
    "team_breakdown": [
      {
        "team_id": 100,
        "team_name": "Engineering",
        "sessions": 20,
        "messages": 400,
        "active": 10,
        "models_used": {
          "GPT-5 Chat": 15,
          "Claude 3.5 Sonnet": 5
        }
      }
    ]
  },
  "uptime_seconds": 86400
}
```

**Status Codes:**
- `200 OK`: Success
- `403 Forbidden`: Not admin

---

### POST `/api/v1/admin/clear-sessions`

**Description:** Clear sessions (all or by platform)

**Authentication:** Required (Admin only)

**Request Query Params:**
- `platform` (string, optional): Filter by platform ("telegram" or "internal")

**Request:** None (query params only)

**Response:**
```json
{
  "success": true,
  "cleared": 42,
  "message": "Cleared 42 sessions"
}
```

**Status Codes:**
- `200 OK`: Sessions cleared
- `403 Forbidden`: Not admin

**Example:**
```bash
# Clear all sessions
curl -X POST http://localhost:3000/api/v1/admin/clear-sessions \
  -H "Authorization: Bearer sk_admin_YOUR_KEY_HERE"

# Clear only telegram sessions
curl -X POST "http://localhost:3000/api/v1/admin/clear-sessions?platform=telegram" \
  -H "Authorization: Bearer sk_admin_YOUR_KEY_HERE"
```

---

### Team Management

### POST `/api/v1/admin/teams`

**Description:** Create a new team

**Authentication:** Required (Admin only)

**Request Body:**
```json
{
  "name": "Engineering",
  "description": "Engineering team for internal projects",
  "monthly_quota": 10000,
  "daily_quota": 500
}
```

**Request Fields:**
- `name` (string, required): Team name (unique)
- `description` (string, optional): Team description
- `monthly_quota` (int, optional): Monthly request limit (null = unlimited)
- `daily_quota` (int, optional): Daily request limit (null = unlimited)

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

**Status Codes:**
- `200 OK`: Team created
- `400 Bad Request`: Team name already exists
- `403 Forbidden`: Not admin

---

### GET `/api/v1/admin/teams`

**Description:** List all teams

**Authentication:** Required (Admin only)

**Request Query Params:**
- `active_only` (boolean, optional, default=true): Filter active teams only

**Response:**
```json
[
  {
    "id": 1,
    "name": "Engineering",
    "description": "Engineering team",
    "monthly_quota": 10000,
    "daily_quota": 500,
    "is_active": true,
    "webhook_url": "https://example.com/webhook",
    "webhook_enabled": true,
    "created_at": "2025-11-01T12:34:56.789012",
    "updated_at": "2025-11-01T12:34:56.789012"
  },
  {
    "id": 2,
    "name": "Marketing",
    "description": "Marketing team",
    "monthly_quota": 5000,
    "daily_quota": 250,
    "is_active": true,
    "webhook_url": null,
    "webhook_enabled": false,
    "created_at": "2025-11-01T13:00:00.000000",
    "updated_at": "2025-11-01T13:00:00.000000"
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `403 Forbidden`: Not admin

---

### GET `/api/v1/admin/teams/{team_id}`

**Description:** Get team details by ID

**Authentication:** Required (Admin only)

**Request Path Params:**
- `team_id` (int, required): Team ID

**Response:**
```json
{
  "id": 1,
  "name": "Engineering",
  "description": "Engineering team",
  "monthly_quota": 10000,
  "daily_quota": 500,
  "is_active": true,
  "webhook_url": "https://example.com/webhook",
  "webhook_enabled": true,
  "created_at": "2025-11-01T12:34:56.789012",
  "updated_at": "2025-11-01T12:34:56.789012"
}
```

**Status Codes:**
- `200 OK`: Success
- `404 Not Found`: Team not found
- `403 Forbidden`: Not admin

---

### PATCH `/api/v1/admin/teams/{team_id}`

**Description:** Update team settings

**Authentication:** Required (Admin only)

**Request Path Params:**
- `team_id` (int, required): Team ID

**Request Body:**
```json
{
  "name": "Engineering Team",
  "description": "Updated description",
  "monthly_quota": 15000,
  "daily_quota": 750,
  "is_active": true,
  "webhook_url": "https://new-webhook.com/endpoint",
  "webhook_secret": "new_secret_123",
  "webhook_enabled": true
}
```

**Request Fields:** (all optional)
- `name` (string): Team name
- `description` (string): Team description
- `monthly_quota` (int): Monthly request limit
- `daily_quota` (int): Daily request limit
- `is_active` (boolean): Team active status
- `webhook_url` (string): Webhook URL
- `webhook_secret` (string): Webhook secret
- `webhook_enabled` (boolean): Enable webhook

**Response:**
```json
{
  "id": 1,
  "name": "Engineering Team",
  "description": "Updated description",
  "monthly_quota": 15000,
  "daily_quota": 750,
  "is_active": true,
  "webhook_url": "https://new-webhook.com/endpoint",
  "webhook_enabled": true,
  "created_at": "2025-11-01T12:34:56.789012",
  "updated_at": "2025-11-01T14:00:00.000000"
}
```

**Status Codes:**
- `200 OK`: Team updated
- `404 Not Found`: Team not found
- `403 Forbidden`: Not admin

---

### API Key Management

### POST `/api/v1/admin/api-keys`

**Description:** Create a new API key

**Authentication:** Required (Admin only)

**Request Body:**
```json
{
  "team_id": 1,
  "name": "Production API Key",
  "access_level": "team",
  "description": "Production environment key for external client",
  "monthly_quota": null,
  "daily_quota": null,
  "expires_in_days": 365
}
```

**Request Fields:**
- `team_id` (int, required): Team ID
- `name` (string, required): API key friendly name
- `access_level` (string, optional, default="team"): Access level:
  - `"team"` - External teams (clients) - can only use chat service [DEFAULT]
  - `"admin"` - Super admins (internal team) - full access to admin endpoints
- `description` (string, optional): Key description
- `monthly_quota` (int, optional): Override team monthly quota (null = use team quota)
- `daily_quota` (int, optional): Override team daily quota (null = use team quota)
- `expires_in_days` (int, optional): Expiration in days (null = never expires)

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
    "access_level": "user",
    "monthly_quota": null,
    "daily_quota": null,
    "is_active": true,
    "created_by": "sk_admin_",
    "description": "Production environment key",
    "created_at": "2025-11-01T12:34:56.789012",
    "last_used_at": null,
    "expires_at": "2026-11-01T12:34:56.789012"
  },
  "warning": "Save this API key securely. It will not be shown again."
}
```

**Status Codes:**
- `200 OK`: API key created
- `404 Not Found`: Team not found
- `403 Forbidden`: Not admin

**Important:** The `api_key` field contains the actual key and will **only be shown once**. Store it securely.

---

### GET `/api/v1/admin/api-keys`

**Description:** List API keys (all or filtered by team)

**Authentication:** Required (Admin only)

**Request Query Params:**
- `team_id` (int, optional): Filter by team ID

**Response:**
```json
[
  {
    "id": 1,
    "key_prefix": "sk_live_",
    "name": "Production API Key",
    "team_id": 1,
    "team_name": "Engineering",
    "access_level": "user",
    "monthly_quota": null,
    "daily_quota": null,
    "is_active": true,
    "created_by": "sk_admin_",
    "description": "Production environment key",
    "created_at": "2025-11-01T12:34:56.789012",
    "last_used_at": "2025-11-01T15:30:00.000000",
    "expires_at": "2026-11-01T12:34:56.789012"
  },
  {
    "id": 2,
    "key_prefix": "sk_test_",
    "name": "Development API Key",
    "team_id": 1,
    "team_name": "Engineering",
    "access_level": "user",
    "monthly_quota": 1000,
    "daily_quota": 50,
    "is_active": true,
    "created_by": "sk_admin_",
    "description": "Development environment",
    "created_at": "2025-11-01T13:00:00.000000",
    "last_used_at": null,
    "expires_at": null
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `403 Forbidden`: Not admin

---

### DELETE `/api/v1/admin/api-keys/{key_id}`

**Description:** Revoke or permanently delete an API key

**Authentication:** Required (Admin only)

**Request Path Params:**
- `key_id` (int, required): API key ID

**Request Query Params:**
- `permanent` (boolean, optional, default=false): Permanently delete (true) or soft delete (false)

**Response:**
```json
{
  "message": "API key revoked successfully",
  "key_id": 1
}
```

**Status Codes:**
- `200 OK`: API key revoked/deleted
- `404 Not Found`: API key not found
- `403 Forbidden`: Not admin

**Example:**
```bash
# Soft delete (revoke)
curl -X DELETE http://localhost:3000/api/v1/admin/api-keys/1 \
  -H "Authorization: Bearer sk_admin_YOUR_KEY_HERE"

# Hard delete (permanent)
curl -X DELETE "http://localhost:3000/api/v1/admin/api-keys/1?permanent=true" \
  -H "Authorization: Bearer sk_admin_YOUR_KEY_HERE"
```

---

### Usage Tracking

### GET `/api/v1/admin/usage/team/{team_id}`

**Description:** Get usage statistics for a team

**Authentication:** Required (Admin only)

**Request Path Params:**
- `team_id` (int, required): Team ID

**Request Query Params:**
- `days` (int, optional, default=30): Number of days to include

**Response:**
```json
{
  "team_id": 1,
  "team_name": "Engineering",
  "api_key_id": null,
  "api_key_name": null,
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
  "performance": {
    "avg_response_time_ms": 250,
    "median_response_time_ms": 200,
    "p95_response_time_ms": 500
  },
  "models": [
    {
      "model": "GPT-5 Chat",
      "requests": 1000,
      "tokens": 100000
    },
    {
      "model": "Claude 3.5 Sonnet",
      "requests": 500,
      "tokens": 50000
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Success
- `404 Not Found`: Team not found
- `403 Forbidden`: Not admin

---

### GET `/api/v1/admin/usage/api-key/{api_key_id}`

**Description:** Get usage statistics for an API key

**Authentication:** Required (Admin only)

**Request Path Params:**
- `api_key_id` (int, required): API key ID

**Request Query Params:**
- `days` (int, optional, default=30): Number of days to include

**Response:**
```json
{
  "team_id": 1,
  "team_name": "Engineering",
  "api_key_id": 1,
  "api_key_name": "Production API Key",
  "period": {
    "start": "2025-10-02T00:00:00",
    "end": "2025-11-01T23:59:59",
    "days": 30
  },
  "requests": {
    "total": 1000,
    "successful": 980,
    "failed": 20,
    "success_rate": 0.98
  },
  "tokens": {
    "total": 100000,
    "average_per_request": 100
  },
  "cost": {
    "total": 10.00,
    "currency": "USD"
  },
  "performance": {
    "avg_response_time_ms": 240,
    "median_response_time_ms": 200,
    "p95_response_time_ms": 480
  },
  "models": [
    {
      "model": "GPT-5 Chat",
      "requests": 800,
      "tokens": 80000
    },
    {
      "model": "Claude 3.5 Sonnet",
      "requests": 200,
      "tokens": 20000
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Success
- `404 Not Found`: API key not found
- `403 Forbidden`: Not admin

---

### GET `/api/v1/admin/usage/quota/{api_key_id}`

**Description:** Check quota status for an API key

**Authentication:** Required (Admin only)

**Request Path Params:**
- `api_key_id` (int, required): API key ID

**Request Query Params:**
- `period` (string, optional, default="daily"): Period type ("daily" or "monthly")

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

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid period value
- `404 Not Found`: API key not found
- `403 Forbidden`: Not admin

---

### GET `/api/v1/admin/usage/recent`

**Description:** Get recent usage logs

**Authentication:** Required (Admin only)

**Request Query Params:**
- `team_id` (int, optional): Filter by team ID
- `api_key_id` (int, optional): Filter by API key ID
- `limit` (int, optional, default=100): Maximum number of logs to return

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
    {
      "id": 1000,
      "api_key_id": 1,
      "api_key_name": "Production API Key",
      "team_id": 1,
      "team_name": "Engineering",
      "session_id": "internal_1_chat123",
      "platform": "internal",
      "model_used": "Claude 3.5 Sonnet",
      "success": true,
      "timestamp": "2025-11-01T15:25:00.000000"
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Success
- `403 Forbidden`: Not admin

---

### Webhook Management

### PUT `/api/v1/admin/{team_id}/webhook`

**Description:** Configure webhook for a team

**Authentication:** Required (Admin only)

**Request Path Params:**
- `team_id` (int, required): Team ID

**Request Body:**
```json
{
  "webhook_url": "https://example.com/webhook",
  "webhook_secret": "my_secret_key_123",
  "webhook_enabled": true
}
```

**Request Fields:**
- `webhook_url` (string, optional): Webhook URL (must start with http:// or https://)
- `webhook_secret` (string, optional): Secret for HMAC signature
- `webhook_enabled` (boolean, optional, default=false): Enable/disable webhook

**Response:**
```json
{
  "id": 1,
  "name": "Engineering",
  "description": "Engineering team",
  "monthly_quota": 10000,
  "daily_quota": 500,
  "is_active": true,
  "webhook_url": "https://example.com/webhook",
  "webhook_enabled": true,
  "created_at": "2025-11-01T12:34:56.789012",
  "updated_at": "2025-11-01T16:00:00.000000"
}
```

**Status Codes:**
- `200 OK`: Webhook configured
- `400 Bad Request`: Invalid webhook URL format
- `404 Not Found`: Team not found
- `403 Forbidden`: Not admin

---

### POST `/api/v1/admin/{team_id}/webhook/test`

**Description:** Send a test webhook to verify configuration

**Authentication:** Required (Admin only)

**Request Path Params:**
- `team_id` (int, required): Team ID

**Request:** None

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

**Test Result Fields:**
- `success` (boolean): Test successful
- `status_code` (int): HTTP status code from webhook
- `response_time_ms` (int): Response time in milliseconds
- `error` (string): Error message if failed

**Status Codes:**
- `200 OK`: Test completed (check test_result.success for actual result)
- `400 Bad Request`: No webhook URL configured
- `404 Not Found`: Team not found
- `403 Forbidden`: Not admin

---

### GET `/api/v1/admin/{team_id}/webhook`

**Description:** Get webhook configuration for a team

**Authentication:** Required (Admin only)

**Request Path Params:**
- `team_id` (int, required): Team ID

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

**Response Fields:**
- `team_id` (int): Team ID
- `team_name` (string): Team name
- `webhook_url` (string): Webhook URL
- `webhook_secret_configured` (boolean): Whether secret is set (actual secret is masked)
- `webhook_enabled` (boolean): Whether webhook is enabled

**Status Codes:**
- `200 OK`: Success
- `404 Not Found`: Team not found
- `403 Forbidden`: Not admin

---

## Webhook Payload Specification

When webhook is enabled for a team, the following payload is sent to the configured webhook URL after each successful message processing:

**HTTP Method:** POST

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

**Signature Verification:**

The `X-Webhook-Signature` header contains an HMAC-SHA256 signature of the payload:

```python
import hmac
import hashlib
import json

def verify_signature(payload, signature, secret):
    """Verify webhook signature"""
    expected = hmac.new(
        key=secret.encode('utf-8'),
        msg=json.dumps(payload, sort_keys=True).encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    return f"sha256={expected}" == signature
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Error Status Codes:**

- `400 Bad Request`: Invalid request parameters or validation error
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions (e.g., not admin when admin required)
- `404 Not Found`: Resource not found (team, API key, etc.)
- `422 Unprocessable Entity`: Request validation failed
- `429 Too Many Requests`: Rate limit or quota exceeded
- `500 Internal Server Error`: Server error

---

## Authentication

### API Key Format

API keys follow this format:
```
sk_<type>_<random_string>

Examples:
- sk_live_EXAMPLE_KEY_REPLACE_WITH_REAL_KEY
- sk_test_EXAMPLE_KEY_REPLACE_WITH_REAL_KEY
```

### Authorization Header

Include API key in the `Authorization` header using Bearer authentication:

```
Authorization: Bearer sk_live_EXAMPLE_KEY_REPLACE_WITH_REAL_KEY
```

### Access Levels

Three access levels exist:

1. **user**: Basic access - can use `/api/v1/chat` endpoint
2. **team_lead**: Can manage team members (currently same as user)
3. **admin**: Full access - can manage teams, API keys, webhooks, view all data

---

## Rate Limiting

Rate limits are enforced per platform:

- **Telegram**: 20 messages per minute (per user)
- **Internal**: 60 messages per minute (per user)

Additionally, teams can have daily and monthly quotas configured.

When rate limit or quota is exceeded, the API returns:

```json
{
  "detail": "Rate limit exceeded. Please try again later.",
  "success": false,
  "error": "rate_limit_exceeded"
}
```

**Status Code:** `429 Too Many Requests`

---

## Pagination

Currently, the API does not support pagination. List endpoints return all results up to reasonable limits:

- `/api/v1/admin/teams`: Returns all teams
- `/api/v1/admin/api-keys`: Returns all API keys (or filtered by team)
- `/api/v1/admin/usage/recent`: Limited to `limit` parameter (max 100, default 100)

---

## Documentation

### Interactive API Documentation

When `ENABLE_API_DOCS=true` in environment:

- **Swagger UI:** http://localhost:3000/api/v1/docs
- **ReDoc:** http://localhost:3000/api/v1/redoc
- **OpenAPI JSON:** http://localhost:3000/api/v1/openapi.json

### Example Requests

All examples use `curl` and assume the API is running on `http://localhost:3000`.

Replace `sk_live_YOUR_KEY_HERE` and `sk_admin_YOUR_KEY_HERE` with actual API keys.

---

## Summary

**Total Endpoints:** 20

**Unversioned:** 1
- Health check

**Public API v1:** 1
- Chat

**Admin API v1:** 18
- Platform info: 3 endpoints
- Team management: 4 endpoints
- API key management: 3 endpoints
- Usage tracking: 4 endpoints
- Webhook management: 3 endpoints
- Session management: 1 endpoint
