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
from pydantic import BaseModel

from app.models.database import AccessLevel, get_db_session
from app.models.schemas import HealthCheckResponse, StatsResponse
from app.services.api_key_manager import APIKeyManager
from app.services.usage_tracker import UsageTracker
from app.services.session_manager import session_manager
from app.services.platform_manager import platform_manager
from app.api.dependencies import require_admin_access, require_team_lead_access
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


class TeamResponse(BaseModel):
    """Response model for team"""

    id: int
    name: str
    description: Optional[str]
    monthly_quota: Optional[int]
    daily_quota: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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

    id: int
    key_prefix: str
    name: str
    team_id: int
    access_level: str
    monthly_quota: Optional[int]
    daily_quota: Optional[int]
    is_active: bool
    created_by: Optional[str]
    description: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    """Response model when creating an API key (includes the actual key)"""

    api_key: str
    key_info: APIKeyResponse
    warning: str = "Save this API key securely. It will not be shown again."


class UsageStatsResponse(BaseModel):
    """Response model for usage statistics"""

    team_id: Optional[int]
    api_key_id: Optional[int]
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
        version="1.1.0",
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
    total_sessions = len(session_manager.sessions)
    active_sessions = session_manager.get_active_session_count(minutes=5)

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

    return StatsResponse(
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        telegram=telegram_stats,
        internal={**internal_stats, "models_used": dict(internal_stats["models_used"])},
        uptime_seconds=0,  # Will be set by main app
    )


# ==========================================
# WEBHOOK ENDPOINTS - CURRENTLY DISABLED
# ==========================================
# Webhooks are not in use yet. Uncomment when needed.
#
# @router.post("/webhook/{platform}")
# async def admin_webhook_handler(
#     platform: str,
#     data: Dict[str, Any],
#     background_tasks: BackgroundTasks,
#     x_webhook_secret: Optional[str] = Header(None),
#     api_key=Depends(require_admin_access),
# ):
#     """Platform webhook handler (ADMIN ONLY - DISABLED)"""
#     raise HTTPException(
#         status_code=501,
#         detail="Webhook functionality is not currently enabled"
#     )


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
    api_key=Depends(require_team_lead_access),
):
    """List all teams (Team Lead or Admin)"""
    db = get_db_session()
    teams = APIKeyManager.list_all_teams(db, active_only=active_only)
    return [TeamResponse.from_orm(team) for team in teams]


@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    api_key=Depends(require_team_lead_access),
):
    """Get team details (Team Lead or Admin)"""
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

    return APIKeyCreateResponse(
        api_key=api_key_string,
        key_info=APIKeyResponse.from_orm(api_key_obj),
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    team_id: Optional[int] = None,
    api_key=Depends(require_team_lead_access),
):
    """List API keys, optionally filtered by team (Team Lead or Admin)"""
    db = get_db_session()

    if team_id:
        keys = APIKeyManager.list_team_api_keys(db, team_id)
    else:
        # List all teams and their keys (admin only would be better)
        teams = APIKeyManager.list_all_teams(db)
        keys = []
        for team in teams:
            keys.extend(APIKeyManager.list_team_api_keys(db, team.id))

    return [APIKeyResponse.from_orm(key) for key in keys]


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
    api_key=Depends(require_team_lead_access),
):
    """Get usage statistics for a team"""
    db = get_db_session()

    # Verify team exists
    team = APIKeyManager.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    start_date = datetime.utcnow() - timedelta(days=days)
    stats = UsageTracker.get_team_usage_stats(db, team_id, start_date)

    return UsageStatsResponse(**stats)


@router.get("/usage/api-key/{api_key_id}")
async def get_api_key_usage(
    api_key_id: int,
    days: int = 30,
    api_key=Depends(require_team_lead_access),
):
    """Get usage statistics for an API key"""
    db = get_db_session()

    start_date = datetime.utcnow() - timedelta(days=days)
    stats = UsageTracker.get_api_key_usage_stats(db, api_key_id, start_date)

    return stats


@router.get("/usage/quota/{api_key_id}")
async def check_quota(
    api_key_id: int,
    period: str = "daily",
    api_key=Depends(require_team_lead_access),
):
    """Check quota status for an API key"""
    db = get_db_session()

    # Get the API key
    from sqlalchemy.orm import sessionmaker
    from app.models.database import APIKey

    Session = sessionmaker(bind=db.bind)
    session = Session()
    key = session.query(APIKey).filter(APIKey.id == api_key_id).first()

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
    api_key=Depends(require_team_lead_access),
):
    """Get recent usage logs"""
    db = get_db_session()

    logs = UsageTracker.get_recent_usage(
        db=db,
        team_id=team_id,
        api_key_id=api_key_id,
        limit=limit
    )

    return {
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "api_key_id": log.api_key_id,
                "team_id": log.team_id,
                "session_id": log.session_id,
                "platform": log.platform,
                "model_used": log.model_used,
                "success": log.success,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ]
    }
