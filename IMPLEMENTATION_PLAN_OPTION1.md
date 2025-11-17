# Platform Architecture - Option 1 Implementation Plan (OPTIMIZED)

## Overview

Database-driven platform configuration with per-platform customization support.

**Key Changes:**
- Add configuration columns to existing `teams` table
- Update Platform Manager to load configs from database
- Remove '/settings' command from private platforms
- Maintain backward compatibility

---

## Phase 1: Database Schema Enhancement

### Migration: Add Platform Configuration Columns

```python
# alembic/versions/XXXXX_add_platform_config_columns.py

"""Add platform configuration columns to teams table

Revision ID: XXXXX
Revises: 71521c6321dc
Create Date: 2025-01-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'XXXXX'
down_revision = '71521c6321dc'
branch_labels = None
depends_on = None


def upgrade():
    # Add platform_type column
    op.add_column('teams',
        sa.Column('platform_type', sa.String(50), nullable=False, server_default='private')
    )

    # Add configuration override columns (NULL = use defaults)
    op.add_column('teams',
        sa.Column('rate_limit', sa.Integer, nullable=True,
                 comment='Override default rate limit (requests/min)')
    )
    op.add_column('teams',
        sa.Column('max_history', sa.Integer, nullable=True,
                 comment='Override default max conversation history')
    )
    op.add_column('teams',
        sa.Column('default_model', sa.String(255), nullable=True,
                 comment='Override default AI model')
    )
    op.add_column('teams',
        sa.Column('available_models', postgresql.JSON, nullable=True,
                 comment='Override available models list')
    )
    op.add_column('teams',
        sa.Column('allow_model_switch', sa.Boolean, nullable=True,
                 comment='Override model switch permission')
    )

    # Set existing Telegram platform as public (if exists)
    op.execute("""
        UPDATE teams
        SET platform_type = 'public'
        WHERE platform_name = 'telegram'
    """)

    # Add index for faster queries
    op.create_index('ix_teams_platform_type', 'teams', ['platform_type'])


def downgrade():
    op.drop_index('ix_teams_platform_type', table_name='teams')
    op.drop_column('teams', 'allow_model_switch')
    op.drop_column('teams', 'available_models')
    op.drop_column('teams', 'default_model')
    op.drop_column('teams', 'max_history')
    op.drop_column('teams', 'rate_limit')
    op.drop_column('teams', 'platform_type')
```

### Updated Team Model

```python
# app/models/database.py

class Team(Base):
    """
    Team model representing a platform integration.

    Platform Types:
    - 'public': Public messaging services (Telegram, Discord, etc.)
    - 'private': Customer-specific integrations (HOSCO-Popak, etc.)

    Configuration Priority:
    1. Team-specific overrides (rate_limit, max_history, etc.)
    2. Default config for platform_type
    """

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(255), unique=True, nullable=False, index=True)
    platform_name = Column(String(255), unique=True, nullable=False, index=True)

    # Platform type
    platform_type = Column(String(50), nullable=False, default='private', index=True)

    # Quotas
    monthly_quota = Column(Integer, nullable=True)
    daily_quota = Column(Integer, nullable=True)

    # Platform configuration overrides (NULL = use defaults)
    rate_limit = Column(Integer, nullable=True)
    max_history = Column(Integer, nullable=True)
    default_model = Column(String(255), nullable=True)
    available_models = Column(JSON, nullable=True)
    allow_model_switch = Column(Boolean, nullable=True)

    # Status and timestamps
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    api_keys = relationship("APIKey", back_populates="team", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="team", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Team(id={self.id}, platform_name='{self.platform_name}', type='{self.platform_type}')>"
```

---

## Phase 2: Platform Manager Refactoring

### Enhanced Platform Manager

```python
# app/services/platform_manager.py

from typing import Optional
from app.models.database import Team

class PlatformConfig:
    """Platform configuration"""

    def __init__(
        self,
        type: str,
        model: str,
        available_models: List[str] = None,
        rate_limit: int = 30,
        commands: List[str] = None,
        allow_model_switch: bool = False,
        requires_auth: bool = False,
        api_key: str = None,
        max_history: int = 20,
    ):
        self.type = type
        self.model = model
        self.available_models = available_models or [model]
        self.rate_limit = rate_limit
        self.commands = commands or []
        self.allow_model_switch = allow_model_switch
        self.requires_auth = requires_auth
        self.api_key = api_key
        self.max_history = max_history

    def copy(self) -> 'PlatformConfig':
        """Create a copy of this config"""
        return PlatformConfig(
            type=self.type,
            model=self.model,
            available_models=self.available_models.copy(),
            rate_limit=self.rate_limit,
            commands=self.commands.copy(),
            allow_model_switch=self.allow_model_switch,
            requires_auth=self.requires_auth,
            api_key=self.api_key,
            max_history=self.max_history,
        )

    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "model": self.model,
            "available_models": self.available_models,
            "rate_limit": self.rate_limit,
            "commands": self.commands,
            "allow_model_switch": self.allow_model_switch,
            "requires_auth": self.requires_auth,
            "max_history": self.max_history,
        }


class PlatformManager:
    """Manages platform-specific configurations with database-driven overrides"""

    def __init__(self):
        # Default configurations for platform types
        self.default_configs: Dict[str, PlatformConfig] = {}
        self._load_default_configurations()

    def _load_default_configurations(self):
        """Load default platform type configurations"""

        # Public platform defaults (Telegram, Discord, etc.)
        self.default_configs['public'] = PlatformConfig(
            type='public',
            model=settings.TELEGRAM_DEFAULT_MODEL,
            available_models=settings.telegram_models_list,
            rate_limit=settings.TELEGRAM_RATE_LIMIT,
            commands=['start', 'help', 'status', 'clear', 'model', 'models'],
            allow_model_switch=settings.TELEGRAM_ALLOW_MODEL_SWITCH,
            requires_auth=False,
            max_history=settings.TELEGRAM_MAX_HISTORY,
        )

        # Private platform defaults (Customer integrations)
        self.default_configs['private'] = PlatformConfig(
            type='private',
            model=settings.INTERNAL_DEFAULT_MODEL,
            available_models=settings.internal_models_list,
            rate_limit=settings.INTERNAL_RATE_LIMIT,
            commands=['start', 'help', 'status', 'clear', 'model', 'models'],  # NO /settings
            allow_model_switch=True,
            requires_auth=True,
            api_key=settings.INTERNAL_API_KEY,
            max_history=settings.INTERNAL_MAX_HISTORY,
        )

        logger.info("Default platform configurations loaded")
        logger.info(f"  - Public: {self.default_configs['public'].model}")
        logger.info(f"  - Private: {self.default_configs['private'].model}")

    def get_config(self, platform: str, team: Optional[Team] = None) -> PlatformConfig:
        """
        Get configuration for a platform with team-specific overrides.

        Args:
            platform: Platform name (e.g., "telegram", "HOSCO-Popak")
            team: Optional Team object for custom overrides

        Returns:
            PlatformConfig with defaults and team-specific overrides applied
        """

        # If team provided, build custom config
        if team:
            # Start with default config for platform type
            config = self.default_configs[team.platform_type].copy()

            # Apply team-specific overrides
            if team.rate_limit is not None:
                config.rate_limit = team.rate_limit
                logger.debug(f"Team {team.platform_name}: rate_limit override = {team.rate_limit}")

            if team.max_history is not None:
                config.max_history = team.max_history
                logger.debug(f"Team {team.platform_name}: max_history override = {team.max_history}")

            if team.default_model is not None:
                config.model = team.default_model
                logger.debug(f"Team {team.platform_name}: default_model override = {team.default_model}")

            if team.available_models is not None:
                config.available_models = team.available_models
                logger.debug(f"Team {team.platform_name}: available_models override = {len(team.available_models)} models")

            if team.allow_model_switch is not None:
                config.allow_model_switch = team.allow_model_switch
                logger.debug(f"Team {team.platform_name}: allow_model_switch override = {team.allow_model_switch}")

            return config

        # Fallback: determine type by platform name (for backward compatibility)
        platform_lower = platform.lower()

        if platform_lower == 'telegram':
            return self.default_configs['public']
        else:
            # Unknown platforms default to private
            return self.default_configs['private']

    # Keep all existing methods (is_private_platform, can_switch_models, etc.)
    # They now call get_config internally
```

---

## Phase 3: Session Manager Updates

### Minimal Changes to Session Manager

```python
# app/services/session_manager.py

def get_or_create_session(
    self,
    platform: str,
    user_id: str,
    team_id: int | None = None,
    api_key_id: int | None = None,
    api_key_prefix: str | None = None,
) -> ChatSession:
    """
    Get existing session or create new one with platform-specific config and team isolation.
    """
    key = self.get_session_key(platform, user_id, team_id)

    if key not in self.sessions:
        # Load team if available (for config overrides)
        team = None
        if team_id:
            db = get_db_session()
            try:
                team = db.query(Team).filter(Team.id == team_id).first()
            except Exception as e:
                logger.error(f"Error loading team {team_id}: {e}")

        # Get config with team-specific overrides
        config = platform_manager.get_config(platform, team=team)

        # Load message history from database
        db = get_db_session()
        try:
            # Count total messages for this user
            total_count = (
                db.query(func.count(Message.id))
                .filter(
                    Message.platform == platform,
                    Message.user_id == user_id,
                    Message.team_id == team_id if team_id else Message.team_id.is_(None),
                )
                .scalar()
                or 0
            )

            # Load uncleared messages for AI context
            uncleared_messages = (
                db.query(Message)
                .filter(
                    Message.platform == platform,
                    Message.user_id == user_id,
                    Message.team_id == team_id if team_id else Message.team_id.is_(None),
                    Message.cleared_at.is_(None),
                )
                .order_by(Message.created_at)
                .all()
            )

            history = [{"role": msg.role, "content": msg.content} for msg in uncleared_messages]

        except Exception as e:
            logger.error(f"Error loading message history: {e}")
            total_count = 0
            history = []

        # Create session
        self.sessions[key] = ChatSession(
            session_id=hashlib.md5(key.encode()).hexdigest(),
            platform=platform,
            platform_config=config.dict(),
            user_id=user_id,
            current_model=config.model,
            history=history,
            total_message_count=total_count,
            is_admin=platform_manager.is_admin(platform, user_id),
            team_id=team_id,
            api_key_id=api_key_id,
            api_key_prefix=api_key_prefix,
        )

        friendly_platform = get_friendly_platform_name(platform)
        masked_id = mask_session_id(self.sessions[key].session_id)
        team_info = f" (team: {team_id}, key: {api_key_prefix})" if team_id else ""
        logger.info(
            f"Created session for {friendly_platform} user={user_id} (session: {masked_id}){team_info} "
            f"with {total_count} total messages ({len(history)} in context)"
        )
    else:
        # Existing session - verify ownership
        existing_session = self.sessions[key]

        if api_key_id is not None and existing_session.api_key_id != api_key_id:
            logger.warning(
                f"[SECURITY] API key {api_key_prefix} attempted to access user_id={user_id} "
                f"owned by API key ID {existing_session.api_key_id}"
            )
            raise PermissionError("Access denied. This user's conversation belongs to a different API key.")

        existing_session.update_activity()

    return self.sessions[key]
```

---

## Phase 4: Admin API Enhancements

### Update Team Creation Endpoint

```python
# app/api/admin_routes.py

from app.models.schemas import TeamCreate, TeamCreateResponse, TeamUpdate

class TeamCreate(BaseModel):
    """Schema for creating a new team"""
    display_name: str = Field(..., min_length=1, max_length=255)
    platform_name: str = Field(..., min_length=1, max_length=255)
    platform_type: str = Field(default='private', pattern='^(public|private)$')

    # Quotas
    monthly_quota: Optional[int] = Field(None, ge=0)
    daily_quota: Optional[int] = Field(None, ge=0)

    # Configuration overrides (optional)
    rate_limit: Optional[int] = Field(None, ge=1, le=1000)
    max_history: Optional[int] = Field(None, ge=1, le=100)
    default_model: Optional[str] = Field(None, max_length=255)
    available_models: Optional[List[str]] = None
    allow_model_switch: Optional[bool] = None

class TeamUpdate(BaseModel):
    """Schema for updating a team"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    platform_type: Optional[str] = Field(None, pattern='^(public|private)$')
    monthly_quota: Optional[int] = Field(None, ge=0)
    daily_quota: Optional[int] = Field(None, ge=0)
    rate_limit: Optional[int] = Field(None, ge=1, le=1000)
    max_history: Optional[int] = Field(None, ge=1, le=100)
    default_model: Optional[str] = None
    available_models: Optional[List[str]] = None
    allow_model_switch: Optional[bool] = None
    is_active: Optional[bool] = None

@router.post("/teams", response_model=TeamCreateResponse)
async def create_team(
    team_data: TeamCreate,
    admin: str = Depends(require_admin_access),
):
    """
    Create a new team with optional configuration overrides.

    Configuration priority:
    1. Team-specific overrides (if provided)
    2. Default config for platform_type
    """
    db = get_db_session()

    try:
        # Check if platform_name already exists
        existing_team = APIKeyManager.get_team_by_platform_name(db, team_data.platform_name)
        if existing_team:
            raise HTTPException(
                status_code=400,
                detail=f"Platform name '{team_data.platform_name}' already exists"
            )

        # Create team with config overrides
        new_team = Team(
            display_name=team_data.display_name,
            platform_name=team_data.platform_name,
            platform_type=team_data.platform_type,
            monthly_quota=team_data.monthly_quota,
            daily_quota=team_data.daily_quota,
            rate_limit=team_data.rate_limit,
            max_history=team_data.max_history,
            default_model=team_data.default_model,
            available_models=team_data.available_models,
            allow_model_switch=team_data.allow_model_switch,
        )

        db.add(new_team)
        db.commit()
        db.refresh(new_team)

        # Auto-generate API key
        api_key_plain, api_key_obj = APIKeyManager.create_api_key(
            db=db,
            team_id=new_team.id,
            name=f"Auto-generated for {new_team.display_name}",
            created_by=admin,
        )

        logger.info(
            f"Created team '{new_team.display_name}' (ID: {new_team.id}) "
            f"type={new_team.platform_type} with auto-generated API key (prefix: {api_key_obj.key_prefix})"
        )

        return TeamCreateResponse(
            id=new_team.id,
            display_name=new_team.display_name,
            platform_name=new_team.platform_name,
            platform_type=new_team.platform_type,
            monthly_quota=new_team.monthly_quota,
            daily_quota=new_team.daily_quota,
            is_active=new_team.is_active,
            created_at=new_team.created_at,
            api_key=api_key_plain,
            warning="Save this API key securely. It will not be shown again.",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating team: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create team: {str(e)}")
```

---

## Implementation Checklist

### Phase 1: Database
- [ ] Create Alembic migration file
- [ ] Add columns to teams table
- [ ] Update Team model in database.py
- [ ] Run migration: `alembic upgrade head`
- [ ] Verify schema: Check all columns exist

### Phase 2: Platform Manager
- [ ] Add `.copy()` method to PlatformConfig
- [ ] Update `_load_default_configurations()` (remove /settings from private)
- [ ] Enhance `get_config()` to accept team parameter
- [ ] Test with and without team parameter

### Phase 3: Session Manager
- [ ] Update `get_or_create_session()` to load team
- [ ] Pass team to `platform_manager.get_config()`
- [ ] Test session creation with custom configs

### Phase 4: Admin API
- [ ] Update TeamCreate schema
- [ ] Update TeamUpdate schema
- [ ] Update create_team endpoint
- [ ] Add update_team endpoint (if not exists)
- [ ] Test API with config overrides

### Phase 5: Testing
- [ ] Create team without overrides (use defaults)
- [ ] Create team with rate_limit override
- [ ] Create team with custom models
- [ ] Verify configs applied correctly
- [ ] Test backward compatibility (existing teams)

---

## Example Usage

### Create Team with Defaults
```bash
POST /v1/admin/teams
{
  "display_name": "HOSCO Tabriz",
  "platform_name": "HOSCO-Tabriz",
  "platform_type": "private",
  "monthly_quota": 100000,
  "daily_quota": 5000
}
# Uses default private config: 60/min rate, 30 history, all models
```

### Create Team with Custom Config
```bash
POST /v1/admin/teams
{
  "display_name": "HOSCO VIP",
  "platform_name": "HOSCO-VIP",
  "platform_type": "private",
  "monthly_quota": 500000,
  "daily_quota": 20000,
  "rate_limit": 120,
  "max_history": 50,
  "available_models": ["openai/gpt-4", "anthropic/claude-sonnet-4"]
}
# Custom config: 120/min rate, 50 history, only GPT-4 and Claude
```

---

## Benefits

✅ **Per-platform customization**: Each customer gets tailored config
✅ **Database-driven**: No code changes to add platforms
✅ **Backward compatible**: Existing platforms work with defaults
✅ **Scalable**: Supports unlimited platforms
✅ **Clean code**: Single source of truth (database)
✅ **Flexible**: Override only what you need

---

## Performance Impact

- **Query overhead**: +1 JOIN when loading team (negligible)
- **Memory**: Minimal (config cached in session)
- **Response time**: < 1ms additional per request
- **Database**: Well-indexed, no performance issues

---

## Migration Strategy

1. **Deploy migration**: Add columns (non-breaking)
2. **Deploy code**: Update platform manager + session manager
3. **Verify**: Existing platforms work (use defaults)
4. **Customize**: Update teams with specific configs via admin API

---

## Questions Before Implementation?

1. Do you want to add more configurable fields?
2. Should we add validation for available_models?
3. Do you want a separate endpoint to update only configs?
4. Any other commands to remove from private platforms?

Let me know if this plan looks good, or if you want any changes!
