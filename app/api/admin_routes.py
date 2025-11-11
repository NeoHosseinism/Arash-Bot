"""
Admin API routes for team and API key management

TWO-PATH AUTHENTICATION:
These endpoints are ONLY accessible to SUPER ADMINS (internal team).
Authentication via SUPER_ADMIN_API_KEYS environment variable (NOT database).

ADMIN ENDPOINTS (SUPER ADMINS ONLY):
- Team management (create, list, update, delete teams)
- API key management (create, list, revoke API keys for any team)
- Usage statistics (view ALL teams' usage)
- Platform information (Telegram + Internal platform config)
- System administration (clear sessions, webhook config, etc.)

SECURITY:
- All endpoints protected by require_admin_access dependency
- Exposes platform details including Telegram (admin-only information)
- External teams (TEAM level) have NO ACCESS to these endpoints
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header
from pydantic import BaseModel, Field, ConfigDict

from app.models.database import get_db_session
from app.models.schemas import HealthCheckResponse, StatsResponse
from app.services.api_key_manager import APIKeyManager
from app.services.usage_tracker import UsageTracker
from app.services.session_manager import session_manager
from app.services.platform_manager import platform_manager
from app.api.dependencies import require_admin_access
from app.core.name_mapping import get_friendly_model_name
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Team Management & Administration"])


# ===========================
# Pydantic Models for Requests/Responses
# ===========================


class TeamCreate(BaseModel):
    """
    Request model for creating a team.

    Changes:
    - Uses platform_name instead of name/description (e.g., "Internal-BI", "External-Telegram")
    - Removed webhooks (not supported)
    - Auto-generates API key on creation
    """
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "platform_name": "Internal-BI",
                    "monthly_quota": 100000,
                    "daily_quota": 5000
                },
                {
                    "platform_name": "External-Marketing",
                    "monthly_quota": 50000,
                    "daily_quota": 2000
                }
            ]
        }
    )

    platform_name: str = Field(..., description="Platform name (e.g., 'Internal-BI', 'External-Marketing')", examples=["Internal-BI", "External-Marketing"])
    monthly_quota: Optional[int] = Field(None, description="Monthly request quota (None = unlimited)", examples=[100000, None])
    daily_quota: Optional[int] = Field(None, description="Daily request quota (None = unlimited)", examples=[5000, None])


class TeamUpdate(BaseModel):
    """
    Request model for updating a team.

    Changes:
    - Uses platform_name instead of name/description
    - Removed webhooks (not supported)
    """
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "platform_name": "Internal-BI-Updated",
                    "monthly_quota": 150000,
                    "daily_quota": 7000,
                    "is_active": True
                },
                {
                    "is_active": False
                }
            ]
        }
    )

    platform_name: Optional[str] = Field(None, examples=["Internal-BI-Updated"])
    monthly_quota: Optional[int] = Field(None, examples=[150000])
    daily_quota: Optional[int] = Field(None, examples=[7000])
    is_active: Optional[bool] = Field(None, examples=[True, False])


class TeamResponse(BaseModel):
    """
    Response model for team.

    Includes API key prefix (one key per team).
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "platform_name": "Internal-BI",
                    "monthly_quota": 100000,
                    "daily_quota": 5000,
                    "is_active": True,
                    "api_key_prefix": "ark_1234",
                    "api_key_last_used": "2025-01-15T14:30:00",
                    "created_at": "2025-01-01T10:00:00",
                    "updated_at": "2025-01-15T14:30:00"
                }
            ]
        }
    )

    id: int = Field(..., examples=[1])
    platform_name: str = Field(..., examples=["Internal-BI"])
    monthly_quota: Optional[int] = Field(None, examples=[100000])
    daily_quota: Optional[int] = Field(None, examples=[5000])
    is_active: bool = Field(..., examples=[True])
    api_key_prefix: Optional[str] = Field(None, examples=["ark_1234"])
    api_key_last_used: Optional[datetime] = Field(None, examples=["2025-01-15T14:30:00"])
    created_at: datetime
    updated_at: datetime


class TeamCreateResponse(BaseModel):
    """
    Response model when creating a team (includes the generated API key).

    The API key is shown ONLY ONCE during creation.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "platform_name": "Internal-BI",
                    "monthly_quota": 100000,
                    "daily_quota": 5000,
                    "is_active": True,
                    "created_at": "2025-01-15T10:00:00",
                    "api_key": "ark_1234567890abcdef1234567890abcdef12345678",
                    "warning": "Save this API key securely. It will not be shown again."
                }
            ]
        }
    )

    id: int = Field(..., examples=[1])
    platform_name: str = Field(..., examples=["Internal-BI"])
    monthly_quota: Optional[int] = Field(None, examples=[100000])
    daily_quota: Optional[int] = Field(None, examples=[5000])
    is_active: bool = Field(..., examples=[True])
    created_at: datetime
    api_key: str = Field(..., description="Full API key - shown only once!", examples=["ark_1234567890abcdef1234567890abcdef12345678"])
    warning: str = "Save this API key securely. It will not be shown again."


class UsageStatsResponse(BaseModel):
    """Response model for usage statistics (team-based only, no api_key_id)"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "team_id": 1,
                    "team_name": "Internal-BI",
                    "period": {
                        "start": "2025-01-01T00:00:00",
                        "end": "2025-01-31T23:59:59",
                        "days": 30
                    },
                    "requests": {
                        "total": 15000,
                        "successful": 14850,
                        "failed": 150
                    },
                    "tokens": {
                        "total": 1500000,
                        "average_per_request": 100
                    },
                    "cost": {
                        "total": 15.50,
                        "currency": "USD"
                    },
                    "performance": {
                        "average_response_time_ms": 850,
                        "p95_response_time_ms": 1200
                    },
                    "models": [
                        {
                            "model": "Gemini 2.0 Flash",
                            "requests": 8000,
                            "percentage": 53.3
                        },
                        {
                            "model": "GPT-5 Chat",
                            "requests": 5000,
                            "percentage": 33.3
                        },
                        {
                            "model": "DeepSeek v3",
                            "requests": 2000,
                            "percentage": 13.3
                        }
                    ]
                }
            ]
        }
    )

    team_id: Optional[int] = Field(None, examples=[1])
    team_name: Optional[str] = Field(None, examples=["Internal-BI"])
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
    team_id: Optional[int] = None,
    api_key=Depends(require_admin_access),
):
    """
    Clear sessions (ADMIN ONLY)

    SECURITY:
    - Admin-only endpoint
    - Can clear all sessions or filter by team_id
    - No team isolation needed (admin has full access)
    """
    if team_id:
        keys_to_remove = [
            key
            for key, session in session_manager.sessions.items()
            if session.team_id == team_id
        ]
    else:
        keys_to_remove = list(session_manager.sessions.keys())

    for key in keys_to_remove:
        del session_manager.sessions[key]

    logger.info(f"Admin cleared {len(keys_to_remove)} sessions (team_id: {team_id or 'all'})")

    return {
        "success": True,
        "cleared": len(keys_to_remove),
        "message": f"Cleared {len(keys_to_remove)} sessions",
    }


# ===========================
# Team Management Endpoints
# ===========================


@router.post(
    "/teams",
    response_model=TeamCreateResponse,
    responses={
        200: {
            "description": "Team created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "platform_name": "Internal-BI",
                        "monthly_quota": 100000,
                        "daily_quota": 5000,
                        "is_active": True,
                        "created_at": "2025-01-15T10:00:00",
                        "api_key": "ark_1234567890abcdef1234567890abcdef12345678",
                        "warning": "Save this API key securely. It will not be shown again."
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Authentication required"
                    }
                }
            }
        },
        403: {
            "description": "Invalid super admin API key",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid super admin API key"
                    }
                }
            }
        }
    }
)
async def create_team(
    team_data: TeamCreate,
    api_key=Depends(require_admin_access),
):
    """
    Create a new team with auto-generated API key (Admin only).

    ⚠️ **IMPORTANT**: The API key is shown ONLY ONCE in the response. Save it securely!

    ## Request Example
    ```json
    {
      "platform_name": "Internal-BI",
      "monthly_quota": 100000,
      "daily_quota": 5000
    }
    ```

    ## Response
    The response includes the full API key. This is the **only time** it will be visible.
    Store it immediately in a secure location.

    ## Authentication
    Requires super admin API key in Authorization header:
    ```http
    Authorization: Bearer <super-admin-key>
    ```
    """
    db = get_db_session()

    # Check if platform_name already exists
    existing_team = APIKeyManager.get_team_by_platform_name(db, team_data.platform_name)
    if existing_team:
        raise HTTPException(
            status_code=400,
            detail=f"Team with platform name '{team_data.platform_name}' already exists"
        )

    # Create team with auto-generated API key
    team, api_key_string = APIKeyManager.create_team_with_key(
        db=db,
        platform_name=team_data.platform_name,
        monthly_quota=team_data.monthly_quota,
        daily_quota=team_data.daily_quota,
    )

    return TeamCreateResponse(
        id=team.id,
        platform_name=team.platform_name,
        monthly_quota=team.monthly_quota,
        daily_quota=team.daily_quota,
        is_active=team.is_active,
        created_at=team.created_at,
        api_key=api_key_string,
    )


@router.get("/teams", response_model=List[TeamResponse])
async def list_teams(
    active_only: bool = True,
    api_key=Depends(require_admin_access),
):
    """List all teams (Admin only) with API key prefix"""
    db = get_db_session()
    teams = APIKeyManager.list_all_teams(db, active_only=active_only)

    # Build response with API key prefix for each team
    responses = []
    for team in teams:
        # Get the team's API key (one per team)
        api_key_obj = db.query(APIKey).filter(APIKey.team_id == team.id).first()

        responses.append(TeamResponse(
            id=team.id,
            platform_name=team.platform_name,
            monthly_quota=team.monthly_quota,
            daily_quota=team.daily_quota,
            is_active=team.is_active,
            api_key_prefix=api_key_obj.key_prefix if api_key_obj else None,
            api_key_last_used=api_key_obj.last_used_at if api_key_obj else None,
            created_at=team.created_at,
            updated_at=team.updated_at,
        ))

    return responses


@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    api_key=Depends(require_admin_access),
):
    """Get team details (Admin only) with API key prefix"""
    db = get_db_session()
    team = APIKeyManager.get_team_by_id(db, team_id)

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Get the team's API key
    api_key_obj = db.query(APIKey).filter(APIKey.team_id == team.id).first()

    return TeamResponse(
        id=team.id,
        platform_name=team.platform_name,
        monthly_quota=team.monthly_quota,
        daily_quota=team.daily_quota,
        is_active=team.is_active,
        api_key_prefix=api_key_obj.key_prefix if api_key_obj else None,
        api_key_last_used=api_key_obj.last_used_at if api_key_obj else None,
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


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
        platform_name=team_data.platform_name,
        monthly_quota=team_data.monthly_quota,
        daily_quota=team_data.daily_quota,
        is_active=team_data.is_active,
    )

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Get the team's API key
    api_key_obj = db.query(APIKey).filter(APIKey.team_id == team.id).first()

    return TeamResponse(
        id=team.id,
        platform_name=team.platform_name,
        monthly_quota=team.monthly_quota,
        daily_quota=team.daily_quota,
        is_active=team.is_active,
        api_key_prefix=api_key_obj.key_prefix if api_key_obj else None,
        api_key_last_used=api_key_obj.last_used_at if api_key_obj else None,
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


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


@router.get("/usage/recent")
async def get_recent_usage(
    team_id: Optional[int] = None,
    limit: int = 100,
    api_key=Depends(require_admin_access),
):
    """
    Get recent usage logs (Admin only, team-based tracking)

    SECURITY: Only admins can view usage logs
    """
    db = get_db_session()

    logs = UsageTracker.get_recent_usage(
        db=db,
        team_id=team_id,
        limit=limit
    )

    # Build mapping for team names
    team_ids = set(log.team_id for log in logs if log.team_id)

    team_name_map = {}
    for tid in team_ids:
        team = APIKeyManager.get_team_by_id(db, tid)
        if team:
            team_name_map[tid] = team.platform_name  # Use platform_name instead of name

    return {
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
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


