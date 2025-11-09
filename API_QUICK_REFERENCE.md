# Arash Bot API - Quick Reference

## Authentication

### Super Admin (Environment-Based)
```bash
Authorization: Bearer <SUPER_ADMIN_API_KEY>
# Set via SUPER_ADMIN_API_KEYS environment variable
```

### Team API Key (Database-Based)
```bash
Authorization: Bearer <team_api_key>
# Created via /api/v1/admin/api-keys endpoint
```

---

## Public Endpoints

### Health Check
```
GET /health
```
No authentication required.

---

## Team Endpoints (Team API Key Required)

### Chat
```
POST /api/v1/chat
Authorization: Bearer <team_api_key>

{
  "platform": "internal",
  "user_id": "user123",
  "chat_id": "chat123",
  "message_id": "msg123",
  "text": "Hello",
  "type": "text",
  "metadata": {}
}
```

---

## Admin Endpoints (Super Admin Key Required)

All endpoints require: `Authorization: Bearer <SUPER_ADMIN_API_KEY>`

### Platform Info
```
GET /api/v1/admin/
GET /api/v1/admin/platforms
GET /api/v1/admin/stats
```

### Sessions
```
POST /api/v1/admin/clear-sessions?platform=internal
```

### Teams
```
POST /api/v1/admin/teams
{
  "name": "Team Name",
  "description": "Optional",
  "monthly_quota": 10000,
  "daily_quota": 500
}

GET /api/v1/admin/teams?active_only=true
GET /api/v1/admin/teams/{team_id}

PATCH /api/v1/admin/teams/{team_id}
{
  "name": "New Name",
  "description": "New Description",
  "monthly_quota": 20000,
  "daily_quota": 1000,
  "is_active": true
}
```

### API Keys
```
POST /api/v1/admin/api-keys
{
  "team_id": 1,
  "name": "Production Key",
  "description": "Optional",
  "monthly_quota": null,
  "daily_quota": null,
  "expires_in_days": 365
}

GET /api/v1/admin/api-keys?team_id=1
DELETE /api/v1/admin/api-keys/{key_id}?permanent=false
```

### Usage Statistics
```
GET /api/v1/admin/usage/team/{team_id}?days=30
GET /api/v1/admin/usage/api-key/{api_key_id}?days=30
GET /api/v1/admin/usage/quota/{api_key_id}?period=daily
GET /api/v1/admin/usage/recent?team_id=1&api_key_id=1&limit=100
```

### Webhooks
```
PUT /api/v1/admin/{team_id}/webhook
{
  "webhook_url": "https://example.com/webhook",
  "webhook_secret": "secret123",
  "webhook_enabled": true
}

POST /api/v1/admin/{team_id}/webhook/test
GET /api/v1/admin/{team_id}/webhook
```

---

## Access Summary

| Endpoint Pattern | Authentication | Access |
|-----------------|----------------|---------|
| `/health` | None | Public |
| `/api/v1/chat` | Team API Key | External Teams |
| `/api/v1/admin/*` | Super Admin Key | Internal Team Only |

---

## Two-Path Authentication

**Super Admins:**
- Environment: `SUPER_ADMIN_API_KEYS="key1,key2,key3"`
- Access: All admin endpoints
- NOT in database

**Teams:**
- Database: `api_keys` table
- Access: Chat endpoint only
- Created by super admins
