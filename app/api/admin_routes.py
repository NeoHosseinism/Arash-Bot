"""
Admin API routes for team and API key management

ADMIN ENDPOINTS: These endpoints expose platform details including Telegram.
Only accessible with admin API keys.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header
from pydantic import BaseModel, ConfigDict

from app.models.database import AccessLevel, get_db_session
from app.models.schemas import HealthCheckResponse, StatsResponse
from app.services.api_key_manager import APIKeyManager
from app.services.usage_tracker import UsageTracker
from app.services.session_manager import session_manager
from app.services.platform_manager import platform_manager
from app.api.dependencies import require_admin_access
from app.core.name_mapping import get_friendly_model_name
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ===========================
# Pydantic Models for Requests/Responses
# ===========================


class TeamCreate(BaseModel):
    """Request model for creating a team"""

    name: str
    description: Optional[str] = None
    monthly_quota: Optional[int] = None
    daily_quota: Optional[int] = None


class TeamUpdate(BaseModel):
    """Request model for updating a team"""

    name: Optional[str] = None
    description: Optional[str] = None
    monthly_quota: Optional[int] = None
    daily_quota: Optional[int] = None
    is_active: Optional[bool] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_enabled: Optional[bool] = None


class TeamResponse(BaseModel):
    """Response model for team"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    monthly_quota: Optional[int]
    daily_quota: Optional[int]
    is_active: bool
    webhook_url: Optional[str]
    webhook_enabled: bool
    created_at: datetime
    updated_at: datetime


class APIKeyCreate(BaseModel):
    """Request model for creating an API key"""

    team_id: int
    name: str
    access_level: AccessLevel = AccessLevel.USER
    description: Optional[str] = None
    monthly_quota: Optional[int] = None
    daily_quota: Optional[int] = None
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    """Response model for API key (without the actual key)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    key_prefix: str
    name: str
    team_id: int
    team_name: str  # Team name for better UX
    access_level: str
    monthly_quota: Optional[int]
    daily_quota: Optional[int]
    is_active: bool
    created_by: Optional[str]
    description: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]


class APIKeyCreateResponse(BaseModel):
    """Response model when creating an API key (includes the actual key)"""

    api_key: str
    key_info: APIKeyResponse
    warning: str = "Save this API key securely. It will not be shown again."


class UsageStatsResponse(BaseModel):
    """Response model for usage statistics"""

    team_id: Optional[int]
    team_name: Optional[str]  # Team name for better admin UX
    api_key_id: Optional[int]
    api_key_name: Optional[str]  # API key name for better admin UX
    period: dict
    requests: dict
    tokens: dict
    cost: dict
    performance: dict
    models: List[dict]


# ===========================
# Platform Information Endpoints (Admin Only)
# ===========================


@router.get("/", response_model=HealthCheckResponse)
async def admin_root(
    api_key=Depends(require_admin_access),
):
    """
    Root endpoint with platform information (ADMIN ONLY)

    SECURITY: Exposes Telegram platform details - Admin access required
    """
    telegram_config = platform_manager.get_config("telegram")
    internal_config = platform_manager.get_config("internal")

    return HealthCheckResponse(
        service="Arash External API Service",
        version="1.0.0",
        status="healthy",
        platforms={
            "telegram": {
                "type": "public",
                "model": get_friendly_model_name(telegram_config.model),
                "rate_limit": telegram_config.rate_limit,
                "model_switching": False,
            },
            "internal": {
                "type": "private",
                "models": [get_friendly_model_name(m) for m in internal_config.available_models],
                "rate_limit": internal_config.rate_limit,
                "model_switching": True,
            },
        },
        active_sessions=len(session_manager.sessions),
        timestamp=datetime.now(),
    )


@router.get("/platforms")
async def get_platforms(
    api_key=Depends(require_admin_access),
):
    """
    Get ALL platform configurations (ADMIN ONLY)

    SECURITY: Exposes Telegram platform details - Admin access required
    """
    telegram_config = platform_manager.get_config("telegram")
    internal_config = platform_manager.get_config("internal")

    return {
        "telegram": {
            "type": "public",
            "model": get_friendly_model_name(telegram_config.model),
            "rate_limit": telegram_config.rate_limit,
            "commands": telegram_config.commands,
            "max_history": telegram_config.max_history,
            "features": {"model_switching": False, "requires_auth": False},
        },
        "internal": {
            "type": "private",
            "default_model": get_friendly_model_name(internal_config.model),
            "available_models": [get_friendly_model_name(m) for m in internal_config.available_models],
            "rate_limit": internal_config.rate_limit,
            "commands": internal_config.commands,
            "max_history": internal_config.max_history,
            "features": {"model_switching": True, "requires_auth": True},
        },
    }


@router.get("/stats", response_model=StatsResponse)
async def get_statistics(
    api_key=Depends(require_admin_access),
):
    """
    Get ALL service statistics (ADMIN ONLY)

    SECURITY: Exposes stats for ALL platforms including Telegram - Admin access required
    """
    db = get_db_session()
    total_sessions = len(session_manager.sessions)
    active_sessions = session_manager.get_active_session_count(minutes=5)

    # Get team name mapping for internal stats
    teams = APIKeyManager.list_all_teams(db)
    team_name_map = {team.id: team.name for team in teams}

    # Statistics by platform
    telegram_stats = {
        "sessions": 0,
        "messages": 0,
        "active": 0,
        "model": get_friendly_model_name(platform_manager.get_config("telegram").model),
    }

    internal_stats = {
        "sessions": 0,
        "messages": 0,
        "active": 0,
        "models_used": defaultdict(int),
    }

    # Statistics by team (for internal platform)
    team_stats = defaultdict(lambda: {
        "team_id": None,
        "team_name": "Unknown",
        "sessions": 0,
        "messages": 0,
        "active": 0,
        "models_used": defaultdict(int),
    })

    for session in session_manager.sessions.values():
        is_active = not session.is_expired(5)

        if session.platform == "telegram":
            telegram_stats["sessions"] += 1
            telegram_stats["messages"] += session.message_count
            if is_active:
                telegram_stats["active"] += 1
        elif session.platform == "internal":
            internal_stats["sessions"] += 1
            internal_stats["messages"] += session.message_count
            friendly_model = get_friendly_model_name(session.current_model)
            internal_stats["models_used"][friendly_model] += 1
            if is_active:
                internal_stats["active"] += 1

            # Aggregate by team
            if session.team_id:
                team_id = session.team_id
                if team_id not in team_stats:
                    team_stats[team_id]["team_id"] = team_id
                    team_stats[team_id]["team_name"] = team_name_map.get(team_id, f"Team {team_id}")

                team_stats[team_id]["sessions"] += 1
                team_stats[team_id]["messages"] += session.message_count
                team_stats[team_id]["models_used"][friendly_model] += 1
                if is_active:
                    team_stats[team_id]["active"] += 1

    # Convert team stats to list
    team_breakdown = [
        {
            "team_id": stats["team_id"],
            "team_name": stats["team_name"],
            "sessions": stats["sessions"],
            "messages": stats["messages"],
            "active": stats["active"],
            "models_used": dict(stats["models_used"]),
        }
        for stats in team_stats.values()
    ]
    # Sort by sessions descending
    team_breakdown.sort(key=lambda x: x["sessions"], reverse=True)

    return StatsResponse(
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        telegram=telegram_stats,
        internal={
            **internal_stats,
            "models_used": dict(internal_stats["models_used"]),
            "team_breakdown": team_breakdown,  # Add team breakdown
        },
        uptime_seconds=0,  # Will be set by main app
    )


@router.post("/clear-sessions")
async def clear_sessions(
    platform: Optional[str] = None,
    api_key=Depends(require_admin_access),
):
    """
    Clear sessions (ADMIN ONLY)

    SECURITY:
    - Admin-only endpoint
    - Can clear all sessions or filter by platform
    - No team isolation needed (admin has full access)
    """
    if platform:
        keys_to_remove = [
            key
            for key, session in session_manager.sessions.items()
            if session.platform == platform
        ]
    else:
        keys_to_remove = list(session_manager.sessions.keys())

    for key in keys_to_remove:
        del session_manager.sessions[key]

    logger.info(f"Admin cleared {len(keys_to_remove)} sessions (platform: {platform or 'all'})")

    return {
        "success": True,
        "cleared": len(keys_to_remove),
        "message": f"Cleared {len(keys_to_remove)} sessions",
    }


# ===========================
# Team Management Endpoints
# ===========================


@router.post("/teams", response_model=TeamResponse)
async def create_team(
    team_data: TeamCreate,
    api_key=Depends(require_admin_access),
):
    """Create a new team (Admin only)"""
    db = get_db_session()

    # Check if team name already exists
    existing_team = APIKeyManager.get_team_by_name(db, team_data.name)
    if existing_team:
        raise HTTPException(
            status_code=400,
            detail=f"Team with name '{team_data.name}' already exists"
        )

    team = APIKeyManager.create_team(
        db=db,
        name=team_data.name,
        description=team_data.description,
        monthly_quota=team_data.monthly_quota,
        daily_quota=team_data.daily_quota,
    )

    return TeamResponse.from_orm(team)


@router.get("/teams", response_model=List[TeamResponse])
async def list_teams(
    active_only: bool = True,
    api_key=Depends(require_admin_access),
):
    """List all teams (Admin only)"""
    db = get_db_session()
    teams = APIKeyManager.list_all_teams(db, active_only=active_only)
    return [TeamResponse.from_orm(team) for team in teams]


@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    api_key=Depends(require_admin_access),
):
    """Get team details (Admin only)"""
    db = get_db_session()
    team = APIKeyManager.get_team_by_id(db, team_id)

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return TeamResponse.from_orm(team)


@router.patch("/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_data: TeamUpdate,
    api_key=Depends(require_admin_access),
):
    """Update team settings (Admin only)"""
    db = get_db_session()

    team = APIKeyManager.update_team(
        db=db,
        team_id=team_id,
        name=team_data.name,
        description=team_data.description,
        monthly_quota=team_data.monthly_quota,
        daily_quota=team_data.daily_quota,
        is_active=team_data.is_active,
    )

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return TeamResponse.from_orm(team)


# ===========================
# API Key Management Endpoints
# ===========================


@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    api_key=Depends(require_admin_access),
):
    """Create a new API key (Admin only)"""
    db = get_db_session()

    # Verify team exists
    team = APIKeyManager.get_team_by_id(db, key_data.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Create the key
    api_key_string, api_key_obj = APIKeyManager.create_api_key(
        db=db,
        team_id=key_data.team_id,
        name=key_data.name,
        access_level=key_data.access_level,
        description=key_data.description,
        monthly_quota=key_data.monthly_quota,
        daily_quota=key_data.daily_quota,
        expires_in_days=key_data.expires_in_days,
        created_by=api_key.key_prefix if api_key else "system",
    )

    # Construct response with team name
    key_info = APIKeyResponse(
        id=api_key_obj.id,
        key_prefix=api_key_obj.key_prefix,
        name=api_key_obj.name,
        team_id=api_key_obj.team_id,
        team_name=team.name,
        access_level=api_key_obj.access_level,
        monthly_quota=api_key_obj.monthly_quota_override,
        daily_quota=api_key_obj.daily_quota_override,
        is_active=api_key_obj.is_active,
        created_by=api_key_obj.created_by,
        description=api_key_obj.description,
        created_at=api_key_obj.created_at,
        last_used_at=api_key_obj.last_used_at,
        expires_at=api_key_obj.expires_at,
    )

    return APIKeyCreateResponse(
        api_key=api_key_string,
        key_info=key_info,
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    team_id: Optional[int] = None,
    api_key=Depends(require_admin_access),
):
    """
    List API keys, optionally filtered by team (Admin only)

    SECURITY: Only admins can list API keys
    """
    db = get_db_session()

    if team_id:
        keys = APIKeyManager.list_team_api_keys(db, team_id)
    else:
        # List all teams and their keys
        teams = APIKeyManager.list_all_teams(db)
        keys = []
        for team in teams:
            keys.extend(APIKeyManager.list_team_api_keys(db, team.id))

    # Manually construct responses with team names
    responses = []
    for key in keys:
        team_name = key.team.name if key.team else "Unknown"
        responses.append(
            APIKeyResponse(
                id=key.id,
                key_prefix=key.key_prefix,
                name=key.name,
                team_id=key.team_id,
                team_name=team_name,
                access_level=key.access_level,
                monthly_quota=key.monthly_quota_override,
                daily_quota=key.daily_quota_override,
                is_active=key.is_active,
                created_by=key.created_by,
                description=key.description,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
                expires_at=key.expires_at,
            )
        )

    return responses


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    permanent: bool = False,
    api_key=Depends(require_admin_access),
):
    """Revoke or delete an API key (Admin only)"""
    db = get_db_session()

    if permanent:
        success = APIKeyManager.delete_api_key(db, key_id)
        action = "deleted"
    else:
        success = APIKeyManager.revoke_api_key(db, key_id)
        action = "revoked"

    if not success:
        raise HTTPException(status_code=404, detail="API key not found")

    return {"message": f"API key {action} successfully", "key_id": key_id}


# ===========================
# Usage Tracking Endpoints
# ===========================


@router.get("/usage/team/{team_id}", response_model=UsageStatsResponse)
async def get_team_usage(
    team_id: int,
    days: int = 30,
    api_key=Depends(require_admin_access),
):
    """
    Get usage statistics for a team (Admin only)

    SECURITY: Only admins can access team usage statistics
    """
    db = get_db_session()

    # Verify team exists
    team = APIKeyManager.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    start_date = datetime.utcnow() - timedelta(days=days)
    stats = UsageTracker.get_team_usage_stats(db, team_id, start_date)

    # Add team name for better UX
    stats["team_name"] = team.name

    return UsageStatsResponse(**stats)


@router.get("/usage/api-key/{api_key_id}")
async def get_api_key_usage(
    api_key_id: int,
    days: int = 30,
    api_key=Depends(require_admin_access),
):
    """
    Get usage statistics for an API key (Admin only)

    SECURITY: Only admins can access API key usage statistics
    """
    db = get_db_session()

    # Get the target API key
    from sqlalchemy.orm import sessionmaker
    from app.models.database import APIKey as DBAPIKey

    Session = sessionmaker(bind=db.bind)
    session = Session()
    target_key = session.query(DBAPIKey).filter(DBAPIKey.id == api_key_id).first()

    if not target_key:
        raise HTTPException(status_code=404, detail="API key not found")

    start_date = datetime.utcnow() - timedelta(days=days)
    stats = UsageTracker.get_api_key_usage_stats(db, api_key_id, start_date)

    # Add team name and API key name for better UX
    stats["team_name"] = target_key.team.name if target_key.team else "Unknown"
    stats["api_key_name"] = target_key.name

    return stats


@router.get("/usage/quota/{api_key_id}")
async def check_quota(
    api_key_id: int,
    period: str = "daily",
    api_key=Depends(require_admin_access),
):
    """
    Check quota status for an API key (Admin only)

    SECURITY: Only admins can check API key quotas
    """
    db = get_db_session()

    # Get the API key
    from sqlalchemy.orm import sessionmaker
    from app.models.database import APIKey as DBAPIKey

    Session = sessionmaker(bind=db.bind)
    session = Session()
    key = session.query(DBAPIKey).filter(DBAPIKey.id == api_key_id).first()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    if period not in ["daily", "monthly"]:
        raise HTTPException(
            status_code=400,
            detail="Period must be 'daily' or 'monthly'"
        )

    quota_info = UsageTracker.check_quota(db, key, period)

    return quota_info


@router.get("/usage/recent")
async def get_recent_usage(
    team_id: Optional[int] = None,
    api_key_id: Optional[int] = None,
    limit: int = 100,
    api_key=Depends(require_admin_access),
):
    """
    Get recent usage logs (Admin only)

    SECURITY: Only admins can view usage logs
    """
    db = get_db_session()

    logs = UsageTracker.get_recent_usage(
        db=db,
        team_id=team_id,
        api_key_id=api_key_id,
        limit=limit
    )

    # Build mapping for team names and API key names
    team_ids = set(log.team_id for log in logs if log.team_id)
    api_key_ids = set(log.api_key_id for log in logs if log.api_key_id)

    team_name_map = {}
    for tid in team_ids:
        team = APIKeyManager.get_team_by_id(db, tid)
        if team:
            team_name_map[tid] = team.name

    from sqlalchemy.orm import sessionmaker
    from app.models.database import APIKey as DBAPIKey
    Session = sessionmaker(bind=db.bind)
    session = Session()

    api_key_name_map = {}
    for kid in api_key_ids:
        key = session.query(DBAPIKey).filter(DBAPIKey.id == kid).first()
        if key:
            api_key_name_map[kid] = key.name

    return {
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "api_key_id": log.api_key_id,
                "api_key_name": api_key_name_map.get(log.api_key_id, "Unknown"),
                "team_id": log.team_id,
                "team_name": team_name_map.get(log.team_id, "Unknown"),
                "session_id": log.session_id,
                "platform": log.platform,
                "model_used": log.model_used,
                "success": log.success,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ]
    }


# ===========================
# Webhook Management Endpoints
# ===========================


class WebhookConfig(BaseModel):
    """Request model for configuring team webhook"""

    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_enabled: bool = False


@router.put("/{team_id}/webhook", dependencies=[Depends(require_admin_access)])
async def configure_team_webhook(
    team_id: int,
    webhook_config: WebhookConfig,
    db=Depends(get_db_session)
):
    """
    Configure webhook for a team (admin only)

    Args:
        team_id: Team ID
        webhook_config: Webhook configuration

    Returns:
        Updated team info
    """
    from app.models.database import Team

    # Get team
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Validate webhook URL if provided
    if webhook_config.webhook_url:
        if not webhook_config.webhook_url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=400,
                detail="Webhook URL must start with http:// or https://"
            )

    # Update webhook configuration
    if webhook_config.webhook_url is not None:
        team.webhook_url = webhook_config.webhook_url
    if webhook_config.webhook_secret is not None:
        team.webhook_secret = webhook_config.webhook_secret
    team.webhook_enabled = webhook_config.webhook_enabled

    # Disable webhook if URL is empty
    if not team.webhook_url:
        team.webhook_enabled = False

    db.commit()
    db.refresh(team)

    logger.info(f"Webhook configured for team {team_id} ({team.name})")

    return TeamResponse.model_validate(team)


@router.post("/{team_id}/webhook/test", dependencies=[Depends(require_admin_access)])
async def test_team_webhook(
    team_id: int,
    db=Depends(get_db_session)
):
    """
    Send a test webhook to verify configuration (admin only)

    Args:
        team_id: Team ID

    Returns:
        Test result
    """
    from app.models.database import Team
    from app.services.webhook_client import webhook_client

    # Get team
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if not team.webhook_url:
        raise HTTPException(
            status_code=400,
            detail="No webhook URL configured for this team"
        )

    # Send test webhook
    result = await webhook_client.test_webhook(team)

    return {
        "team_id": team_id,
        "team_name": team.name,
        "webhook_url": team.webhook_url,
        "test_result": result
    }


@router.get("/{team_id}/webhook")
async def get_team_webhook_config(
    team_id: int,
    api_key=Depends(require_admin_access),
    db=Depends(get_db_session)
):
    """
    Get webhook configuration for a team (Admin only)

    Note: webhook_secret is masked for security

    Args:
        team_id: Team ID

    Returns:
        Webhook configuration
    """
    from app.models.database import Team

    # Get team
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return {
        "team_id": team.id,
        "team_name": team.name,
        "webhook_url": team.webhook_url,
        "webhook_secret_configured": bool(team.webhook_secret),
        "webhook_enabled": team.webhook_enabled
    }
