# Platform Architecture - Comprehensive Solutions

## Current State Analysis

### Architecture (Correct)
- **Public Platforms**: Telegram, Discord (future) - shared, rate-limited
- **Private Platforms**: Customer integrations (HOSCO-Popak, HOSCO-Avand) - isolated, dedicated quotas

### Problem
Platform manager only recognizes hardcoded platforms ("telegram", "internal"), causing:
- Warning logs for every private platform request
- Wrong config applied (Telegram config instead of Internal)

---

## Solution Options (Optimized & Comprehensive)

### Option 1: Database-Driven Platform Configuration ⭐ RECOMMENDED

**Concept**: Store platform configurations in database, no hardcoded configs

**Implementation:**

#### 1.1. Add Platform Config Columns to Teams Table

```python
# Alembic migration
def upgrade():
    # Add platform type
    op.add_column('teams',
        sa.Column('platform_type', sa.String(50), nullable=False, server_default='private')
    )

    # Add config overrides (NULL = use defaults)
    op.add_column('teams', sa.Column('rate_limit', sa.Integer, nullable=True))
    op.add_column('teams', sa.Column('max_history', sa.Integer, nullable=True))
    op.add_column('teams', sa.Column('default_model', sa.String(255), nullable=True))
    op.add_column('teams', sa.Column('available_models', sa.JSON, nullable=True))
    op.add_column('teams', sa.Column('allow_model_switch', sa.Boolean, nullable=True))

    # Set Telegram as public if exists
    op.execute("UPDATE teams SET platform_type = 'public' WHERE platform_name = 'telegram'")
```

#### 1.2. Update Team Model

```python
class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(255), unique=True, nullable=False, index=True)
    platform_name = Column(String(255), unique=True, nullable=False, index=True)

    # Platform type
    platform_type = Column(String(50), nullable=False, default='private')  # 'public' or 'private'

    # Quotas
    monthly_quota = Column(Integer, nullable=True)
    daily_quota = Column(Integer, nullable=True)

    # Platform config (NULL = use defaults from platform_type)
    rate_limit = Column(Integer, nullable=True)
    max_history = Column(Integer, nullable=True)
    default_model = Column(String(255), nullable=True)
    available_models = Column(JSON, nullable=True)  # ["model1", "model2"]
    allow_model_switch = Column(Boolean, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### 1.3. Update Platform Manager

```python
class PlatformManager:
    def __init__(self):
        # Default configs for platform types
        self.default_configs = {
            'public': PlatformConfig(
                type='public',
                model='google/gemini-2.0-flash-001',
                available_models=['google/gemini-2.0-flash-001', 'google/gemini-2.5-flash'],
                rate_limit=20,
                max_history=10,
                allow_model_switch=True,
                requires_auth=False,
                commands=['start', 'help', 'status', 'clear', 'model', 'models'],
            ),
            'private': PlatformConfig(
                type='private',
                model='openai/gpt-5-chat',
                available_models=settings.internal_models_list,
                rate_limit=60,
                max_history=30,
                allow_model_switch=True,
                requires_auth=True,
                commands=['start', 'help', 'status', 'clear', 'model', 'models', 'settings'],
            ),
        }

    def get_config(self, platform: str, team: Team = None) -> PlatformConfig:
        """Get configuration for platform, with team-specific overrides"""

        # If team provided, build custom config
        if team:
            # Start with default config for platform type
            base = self.default_configs[team.platform_type].copy()

            # Apply team-specific overrides
            if team.rate_limit is not None:
                base.rate_limit = team.rate_limit
            if team.max_history is not None:
                base.max_history = team.max_history
            if team.default_model is not None:
                base.model = team.default_model
            if team.available_models is not None:
                base.available_models = team.available_models
            if team.allow_model_switch is not None:
                base.allow_model_switch = team.allow_model_switch

            return base

        # Fallback: determine type by platform name
        if platform.lower() == 'telegram':
            return self.default_configs['public']
        else:
            return self.default_configs['private']
```

#### 1.4. Update Session Manager

```python
def get_or_create_session(
    self,
    platform: str,
    user_id: str,
    team_id: int | None = None,
    api_key_id: int | None = None,
    api_key_prefix: str | None = None,
) -> ChatSession:
    key = self.get_session_key(platform, user_id, team_id)

    if key not in self.sessions:
        # Load team if private platform
        team = None
        if team_id:
            db = get_db_session()
            team = db.query(Team).filter(Team.id == team_id).first()

        # Get config with team overrides
        config = platform_manager.get_config(platform, team=team)

        # ... rest of session creation
```

**Benefits:**
- ✅ **Per-platform customization**: Each customer can have different settings
- ✅ **No code changes needed**: Add new platform via admin API
- ✅ **Scalable**: Supports unlimited platforms
- ✅ **Flexible**: Override specific settings per platform
- ✅ **Zero warnings**: All platforms recognized
- ✅ **Database-driven**: Configuration managed via admin API

**Drawbacks:**
- Requires database migration
- Slightly more complex queries (one JOIN to load team)

---

### Option 2: Dynamic Platform Type Detection (Hybrid)

**Concept**: Keep hardcoded base configs, detect platform type automatically

**Implementation:**

```python
class PlatformManager:
    def __init__(self):
        self.configs = {
            'public': PlatformConfig(...),   # Base config for public platforms
            'private': PlatformConfig(...),  # Base config for private platforms
        }

        # Known public platforms
        self.public_platforms = {'telegram', 'discord', 'whatsapp', 'slack'}

    def get_platform_type(self, platform: str) -> str:
        """Determine platform type"""
        return 'public' if platform.lower() in self.public_platforms else 'private'

    def get_config(self, platform: str) -> PlatformConfig:
        """Get configuration for platform"""
        platform_type = self.get_platform_type(platform)
        return self.configs[platform_type]
```

**Benefits:**
- ✅ **Simple implementation**: 5 lines of code
- ✅ **No database changes**: Works immediately
- ✅ **No warnings**: All platforms recognized
- ✅ **Extensible**: Add new public platforms to set

**Drawbacks:**
- ❌ **No per-platform customization**: All private platforms share same config
- ❌ **Hardcoded public platforms**: Need code change to add Discord, etc.

---

### Option 3: Configuration Registry Pattern

**Concept**: Registry pattern with fallback chain

**Implementation:**

```python
class PlatformConfigRegistry:
    def __init__(self):
        self.configs = {}
        self.fallback_chain = {}

    def register(self, platform: str, config: PlatformConfig):
        """Register platform configuration"""
        self.configs[platform.lower()] = config

    def set_fallback(self, platform: str, fallback: str):
        """Set fallback for platform"""
        self.fallback_chain[platform.lower()] = fallback

    def get_config(self, platform: str) -> PlatformConfig:
        """Get config with fallback chain"""
        platform = platform.lower()

        # Direct lookup
        if platform in self.configs:
            return self.configs[platform]

        # Fallback chain
        if platform in self.fallback_chain:
            return self.get_config(self.fallback_chain[platform])

        # Default fallback
        return self.configs.get('default', self.configs['private'])

# Usage
registry = PlatformConfigRegistry()
registry.register('telegram', telegram_config)
registry.register('private', private_config)
registry.register('public', public_config)

# Set fallbacks
registry.set_fallback('discord', 'public')
registry.set_fallback('whatsapp', 'public')
registry.set_fallback('*', 'private')  # Default for unknown
```

**Benefits:**
- ✅ **Flexible fallback**: Clear chain of responsibility
- ✅ **Explicit mappings**: Easy to understand
- ✅ **Runtime registration**: Can add platforms dynamically

**Drawbacks:**
- More complex than needed
- Still hardcoded fallbacks

---

## Recommendation Matrix

| Criteria | Option 1 (DB-Driven) | Option 2 (Type Detection) | Option 3 (Registry) |
|----------|---------------------|--------------------------|---------------------|
| **Simplicity** | ⭐⭐⭐ Medium | ⭐⭐⭐⭐⭐ Very Simple | ⭐⭐ Complex |
| **Flexibility** | ⭐⭐⭐⭐⭐ Highest | ⭐⭐ Low | ⭐⭐⭐ Medium |
| **Scalability** | ⭐⭐⭐⭐⭐ Unlimited | ⭐⭐⭐⭐ Good | ⭐⭐⭐ Good |
| **Maintenance** | ⭐⭐⭐⭐ Low (DB) | ⭐⭐⭐⭐⭐ Very Low | ⭐⭐⭐ Medium |
| **Performance** | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Good |
| **Per-platform config** | ✅ Yes | ❌ No | ❌ No |
| **Zero code for new platform** | ✅ Yes | ❌ No | ❌ No |
| **Migration needed** | ⚠️ Yes | ✅ No | ✅ No |

---

## Final Recommendation

### **For Immediate Fix: Option 2** (Type Detection)
- 5 minutes to implement
- Zero database changes
- Solves the warning problem
- Good enough for current scale

### **For Long-term: Option 1** (Database-Driven)
- Best flexibility and scalability
- Future-proof for customer customization
- Clean separation of concerns
- Worth the migration effort

### **Implementation Path:**

**Phase 1 (Now)**: Option 2
```python
# app/services/platform_manager.py
def get_config(self, platform: str) -> PlatformConfig:
    platform = platform.lower()

    # Public platforms
    if platform in ['telegram', 'discord', 'whatsapp']:
        return self.configs['telegram']

    # Private platforms (all others)
    return self.configs['internal']
```

**Phase 2 (Later)**: Migrate to Option 1
- Add columns to teams table
- Update admin API to accept config overrides
- Update platform manager to load from database
- Allows per-customer customization

---

## Code Changes Summary

### Option 2 (Immediate - RECOMMENDED FOR NOW)

**File**: `app/services/platform_manager.py`
**Lines changed**: 10
**Migration needed**: No
**Time**: 5 minutes

### Option 1 (Future - RECOMMENDED FOR SCALE)

**Files**:
- Alembic migration (new file)
- `app/models/database.py` (+10 lines)
- `app/services/platform_manager.py` (+30 lines)
- `app/services/session_manager.py` (+5 lines)

**Lines changed**: ~50
**Migration needed**: Yes (backward compatible)
**Time**: 2-3 hours

---

## Decision Framework

Choose Option 2 if:
- Need immediate fix
- Current scale is fine (< 50 platforms)
- No per-customer customization needed yet

Choose Option 1 if:
- Want future-proof architecture
- Expect many customers with custom needs
- Want zero-code platform onboarding
- Have time for proper migration

Choose Option 3 if:
- You want middle ground
- Like registry patterns
- Need runtime flexibility

**My recommendation: Start with Option 2, plan for Option 1.**
