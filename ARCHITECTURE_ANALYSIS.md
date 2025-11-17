# Architecture Analysis: Platform vs Team Confusion

## The Core Problem

The codebase conflates two fundamentally different concepts:

### What They SHOULD Be:

1. **Platform** = Communication channel/interface
   - Examples: Telegram, REST API, gRPC, WebSocket
   - Purpose: How clients connect to the service
   - Controls: Message format, authentication method, protocol

2. **Team** = Customer/Organization
   - Examples: HOSCO-Popak, HOSCO-Avand, Internal-BI
   - Purpose: Who is using the service
   - Controls: Quotas, billing, access permissions

### What They CURRENTLY Are:

- **Team.platform_name** is used as BOTH team identifier AND platform identifier
- Platform manager expects "telegram" or "internal" but receives "HOSCO-Popak"
- Results in: `Unknown platform: hosco-popak, defaulting to Telegram`

---

## Data Flow (Current Implementation)

```
1. Admin creates team:
   POST /v1/admin/teams
   {
     "display_name": "HOSCO Popak",
     "platform_name": "HOSCO-Popak"  ← This is the problem
   }

2. Team stored in database:
   teams table: id=1, platform_name="HOSCO-Popak"
   api_keys table: team_id=1, key="ak_BKulsj605"

3. Client makes request:
   Authorization: Bearer ak_BKulsj605

4. API route (app/api/routes.py:317):
   platform_name = auth.team.platform_name  # "HOSCO-Popak"

5. Message processor (app/services/message_processor.py:116):
   session = session_manager.get_or_create_session(
       platform=platform_name  # "HOSCO-Popak"
   )

6. Session manager (app/services/session_manager.py:68):
   config = platform_manager.get_config(platform)  # Looks up "HOSCO-Popak"

7. Platform manager (app/services/platform_manager.py:104):
   logger.warning(f"Unknown platform: {platform}, defaulting to Telegram")
   return self.configs["telegram"]  # ⚠️ Falls back to Telegram config
```

---

## Problems This Causes

### 1. **Log Spam**
```
[warn] Unknown platform: hosco-popak, defaulting to Telegram
[warn] Unknown platform: hosco-avand, defaulting to Telegram
```

### 2. **All Teams Use Same Config**
- HOSCO-Popak → Falls back to Telegram config (20/min rate limit, 10 max history)
- HOSCO-Avand → Falls back to Telegram config (same limits)
- No per-team customization possible

### 3. **Semantic Confusion**
- Database field called `platform_name` but stores team identifier
- Platform manager called with team names
- Code comments say "platform" but mean "team"

### 4. **Scaling Issues**
- Adding new team = warning in logs
- Can't have different configs per team
- Platform manager hardcoded with only 2 platforms

---

## Where The Confusion Exists

### File: `app/models/database.py`

**Line 35:**
```python
"""
Each team represents a platform (e.g., "Internal-BI", "External-Telegram")
and has exactly ONE API key auto-generated on creation.
"""
```
❌ **Wrong**: Team ≠ Platform

**Line 51-52:**
```python
platform_name = Column(
    String(255), unique=True, nullable=False, index=True
)  # System identifier for platform routing
```
❌ **Misleading**: This is actually a team identifier, not platform identifier

**Line 332:**
```python
platform = Column(String(50), nullable=False, index=True)  # "telegram", "Internal-BI", etc.
```
❌ **Mixed**: "telegram" is a platform, "Internal-BI" is a team

### File: `app/services/platform_manager.py`

**Line 95-105:**
```python
def get_config(self, platform: str) -> PlatformConfig:
    """Get configuration for a platform"""
    # Normalize platform name
    platform = platform.lower()

    # Return config if exists, otherwise default to telegram (public)
    if platform in self.configs:
        return self.configs[platform]

    logger.warning(f"Unknown platform: {platform}, defaulting to Telegram")
    return self.configs[Platform.TELEGRAM]
```
❌ **Problem**: Only knows "telegram" and "internal", but receives team names

### File: `app/api/routes.py`

**Line 317:**
```python
platform_name = auth.team.platform_name
```
❌ **Confusion**: Gets team's platform_name and treats it as platform identifier

---

## Architectural Solutions

### Option 1: Separate Platform and Team (RECOMMENDED)

**Database Changes:**
```python
class Team(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)  # "HOSCO-Popak"
    platform_type = Column(String(50))       # "api", "telegram", "grpc"
    config = Column(JSON)                     # Team-specific config overrides
```

**Platform Manager:**
```python
class PlatformManager:
    def get_team_config(self, team: Team) -> PlatformConfig:
        # Get base config for platform type
        base_config = self.configs[team.platform_type]

        # Override with team-specific settings
        if team.config:
            return merge_configs(base_config, team.config)

        return base_config
```

### Option 2: Dynamic Platform Registration (SIMPLER)

Keep current structure but make platform_manager support dynamic teams:

**Platform Manager:**
```python
def get_config(self, platform: str) -> PlatformConfig:
    platform_lower = platform.lower()

    # Check hardcoded platforms first
    if platform_lower in self.configs:
        return self.configs[platform_lower]

    # For teams (custom platforms), use "internal" config as base
    logger.info(f"Using internal config for team: {platform}")
    return self.configs["internal"]
```

No warning, just info log.

### Option 3: Config in Database (BEST LONG-TERM)

**Add TeamConfig table:**
```python
class TeamConfig(Base):
    team_id = Column(Integer, ForeignKey("teams.id"))
    rate_limit = Column(Integer, default=60)
    max_history = Column(Integer, default=30)
    available_models = Column(JSON)  # ["gpt-4", "claude-3"]
    default_model = Column(String(255))
```

Platform manager reads from database instead of hardcoded configs.

---

## Recommended Fix (Minimal Changes)

### 1. Rename Database Field
```python
# In alembic migration:
op.alter_column('teams', 'platform_name', new_column_name='team_identifier')
```

### 2. Update Platform Manager
```python
def get_config(self, identifier: str) -> PlatformConfig:
    """Get config for platform or team"""
    identifier_lower = identifier.lower()

    # Hardcoded platforms
    if identifier_lower in ["telegram", "internal"]:
        return self.configs[identifier_lower]

    # Teams use internal config by default
    logger.debug(f"Team '{identifier}' using internal config")
    return self.configs["internal"]
```

### 3. Update Comments
Fix all comments that say "platform" when they mean "team"

---

## Impact Analysis

**Files affected:**
- `app/models/database.py` - Field naming, comments
- `app/services/platform_manager.py` - Config lookup logic
- `app/services/session_manager.py` - References to platform
- `app/services/message_processor.py` - Platform parameter usage
- `app/api/routes.py` - Platform extraction from team

**Breaking changes:**
- Database field rename (requires migration)
- API contracts (if exposed in responses)

**Non-breaking changes:**
- Internal logic improvements
- Comment/documentation fixes

---

## Conclusion

The root cause is **semantic overloading**: `platform_name` is used as:
1. Team identifier (what it actually is)
2. Platform type (what the code thinks it is)
3. Configuration key (what platform_manager expects)

**Quick fix**: Make platform_manager accept team identifiers without warnings
**Proper fix**: Separate team identity from platform type
**Future-proof**: Store team configs in database

Choose based on timeline and scope constraints.
