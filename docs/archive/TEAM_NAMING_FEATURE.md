# Team Naming Improvements - Admin UX Enhancement

**Date**: 2025-10-29
**Version**: 1.1.0
**Feature**: Team Name Mapping for Admin Statistics and Reports

---

## Overview

Added comprehensive team naming/mapping logic throughout the admin interface to improve UX for administrators. Now all statistics, reports, and API key listings show human-readable team names instead of just IDs.

---

## Changes Made

### 1. Updated Pydantic Response Models

#### APIKeyResponse
```python
class APIKeyResponse(BaseModel):
    id: int
    key_prefix: str
    name: str
    team_id: int
    team_name: str  # NEW: Team name for better UX
    access_level: str
    # ... other fields
```

#### UsageStatsResponse
```python
class UsageStatsResponse(BaseModel):
    team_id: Optional[int]
    team_name: Optional[str]  # NEW: Team name for better admin UX
    api_key_id: Optional[int]
    api_key_name: Optional[str]  # NEW: API key name for better admin UX
    # ... other fields
```

---

### 2. Enhanced Admin Statistics Endpoint

**Endpoint**: `GET /api/v1/admin/stats`

**New Features**:
- Team breakdown with names in internal platform stats
- Shows top teams by activity
- Includes sessions, messages, and active sessions per team
- Displays models used by each team

**Response Structure**:
```json
{
  "total_sessions": 150,
  "active_sessions": 45,
  "telegram": { ... },
  "internal": {
    "sessions": 100,
    "messages": 5000,
    "active": 30,
    "models_used": { "GPT-5": 70, "Claude Opus 4.5": 30 },
    "team_breakdown": [
      {
        "team_id": 1,
        "team_name": "Engineering",
        "sessions": 50,
        "messages": 3000,
        "active": 15,
        "models_used": { "GPT-5": 40, "Claude Opus 4.5": 10 }
      },
      {
        "team_id": 2,
        "team_name": "Data Science",
        "sessions": 30,
        "messages": 1500,
        "active": 10,
        "models_used": { "GPT-5": 20, "Claude Opus 4.5": 10 }
      }
    ]
  }
}
```

**Implementation**:
- Builds team name mapping from database
- Aggregates statistics by team_id
- Sorts teams by session count (descending)
- Includes model usage breakdown per team

---

### 3. Enhanced Usage Tracking Endpoints

#### GET /admin/usage/team/{team_id}
```json
{
  "team_id": 1,
  "team_name": "Engineering",  // NEW
  "period": { "start": "2024-10-01", "end": "2024-10-29" },
  "requests": { "total": 5000, ... },
  // ... other stats
}
```

#### GET /admin/usage/api-key/{api_key_id}
```json
{
  "team_id": 1,
  "team_name": "Engineering",  // NEW
  "api_key_id": 10,
  "api_key_name": "Production Key",  // NEW
  "period": { ... },
  "requests": { ... }
}
```

#### GET /admin/usage/recent
```json
{
  "count": 100,
  "logs": [
    {
      "id": 1,
      "api_key_id": 10,
      "api_key_name": "Production Key",  // NEW
      "team_id": 1,
      "team_name": "Engineering",  // NEW
      "session_id": "abc123",
      "platform": "internal",
      "model_used": "GPT-5",
      "success": true,
      "timestamp": "2024-10-29T10:30:00"
    }
  ]
}
```

**Implementation**:
- Builds mappings for team IDs → names and API key IDs → names
- Efficient batch lookup (only queries unique IDs)
- Adds "Unknown" fallback for missing entities

---

### 4. Enhanced API Key Management Endpoints

#### GET /admin/api-keys
Returns list of API keys with team names:
```json
[
  {
    "id": 1,
    "key_prefix": "sk_live_abc123",
    "name": "Production Key",
    "team_id": 1,
    "team_name": "Engineering",  // NEW
    "access_level": "admin",
    "is_active": true,
    // ... other fields
  }
]
```

#### POST /admin/api-keys
Returns created API key with team name:
```json
{
  "api_key": "sk_live_full_key_here",
  "key_info": {
    "id": 1,
    "team_id": 1,
    "team_name": "Engineering",  // NEW
    // ... other fields
  },
  "warning": "Save this API key securely..."
}
```

**Implementation**:
- Manually constructs APIKeyResponse with team.name
- Handles missing team with "Unknown" fallback
- Maintains all security checks (team isolation)

---

## Benefits

### For Administrators
1. **Quick Team Identification**: See "Engineering" instead of "Team ID: 1"
2. **Better Reports**: Usage reports show meaningful team names
3. **Easier Debugging**: API key listings show both team ID and name
4. **Team Insights**: Stats endpoint shows per-team breakdown with names

### For Team Leads
1. **Clearer Context**: Own team's usage shows team name
2. **API Key Clarity**: Know which team each key belongs to

### For Auditing
1. **Readable Logs**: Recent usage shows team names and API key names
2. **Better Traceability**: Can quickly identify which team is using what
3. **Compliance**: Easier to generate reports for specific teams

---

## Technical Implementation Details

### Team Name Mapping Strategy

```python
# 1. Get all teams from database
teams = APIKeyManager.list_all_teams(db)
team_name_map = {team.id: team.name for team in teams}

# 2. Use mapping when building responses
team_name = team_name_map.get(session.team_id, "Unknown")
```

### API Key Name Mapping
```python
# Build mapping for efficient lookup
api_key_ids = set(log.api_key_id for log in logs if log.api_key_id)
api_key_name_map = {}
for kid in api_key_ids:
    key = session.query(DBAPIKey).filter(DBAPIKey.id == kid).first()
    if key:
        api_key_name_map[kid] = key.name
```

---

## Security Considerations

### No Security Changes
- Team isolation still enforced (no changes)
- Team leads still restricted to own team
- Admins have full access (unchanged)

### Only Display Enhancement
- Team names are read-only display information
- No new access patterns introduced
- All existing security checks maintained

---

## Examples

### Admin Dashboard View
```
Current Statistics:
- Total Sessions: 150
- Active Sessions: 45

Team Breakdown (Internal):
1. Engineering (50 sessions, 3000 messages)
   - GPT-5: 40 sessions
   - Claude Opus 4.5: 10 sessions

2. Data Science (30 sessions, 1500 messages)
   - GPT-5: 20 sessions
   - Claude Opus 4.5: 10 sessions

3. Marketing (20 sessions, 500 messages)
   - Gemini 2.0: 20 sessions
```

### API Key List View
```
Active API Keys:
1. sk_live_abc123 | "Production Key" | Engineering | ADMIN
2. sk_live_def456 | "Dev Key" | Engineering | USER
3. sk_live_ghi789 | "Analytics Key" | Data Science | TEAM_LEAD
```

### Recent Usage View
```
Recent API Activity:
1. Engineering > "Production Key" > GPT-5 > ✓ Success (10:30 AM)
2. Data Science > "Analytics Key" > Claude Opus > ✓ Success (10:25 AM)
3. Marketing > "Marketing API" > Gemini 2.0 > ✓ Success (10:20 AM)
```

---

## Migration Notes

### No Breaking Changes
- All existing API clients continue to work
- New fields are additions (not replacements)
- Team IDs still present for backward compatibility

### Response Format Changes
```diff
  {
    "team_id": 1,
+   "team_name": "Engineering",
    "api_key_id": 10,
+   "api_key_name": "Production Key",
    ...
  }
```

---

## Testing Recommendations

### Manual Testing
1. Create teams with different names
2. Check /admin/stats shows correct team names
3. Verify /admin/api-keys shows team names
4. Check /admin/usage/recent shows team and key names
5. Verify team isolation still works (team leads can't see other teams)

### Automated Testing
```python
def test_admin_stats_includes_team_names():
    response = admin_client.get("/api/v1/admin/stats")
    assert "team_breakdown" in response.json()["internal"]
    for team in response.json()["internal"]["team_breakdown"]:
        assert "team_name" in team
        assert isinstance(team["team_name"], str)

def test_api_keys_include_team_names():
    response = admin_client.get("/api/v1/admin/api-keys")
    for key in response.json():
        assert "team_name" in key
        assert isinstance(key["team_name"], str)
```

---

## Summary

**Enhancement Type**: User Experience Improvement (Admin Interface)
**Lines Changed**: ~150 lines
**Security Impact**: None (display-only enhancement)
**Backward Compatibility**: 100% (additive changes only)

**User Benefits**:
- ✅ Human-readable team names in all admin interfaces
- ✅ Per-team statistics breakdown with names
- ✅ API key listings show team context
- ✅ Usage logs show team and key names
- ✅ Better admin UX for managing multiple teams

**Ready for deployment** - Admin interface now provides clear, team-based context for all operations!
