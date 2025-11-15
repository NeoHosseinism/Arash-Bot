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
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import require_admin_access
from app.core.name_mapping import get_friendly_model_name
from app.models.database import APIKey, get_db_session
from app.services.api_key_manager import APIKeyManager
from app.services.platform_manager import platform_manager
from app.services.session_manager import session_manager
from app.services.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Team Management & Administration"])


# ===========================
# Pydantic Models for Requests/Responses
# ===========================


class TeamCreate(BaseModel):
    """
    Request model for creating a team.

    Field Distinction:
    - display_name: Human-friendly name (supports Persian/Farsi) for admin UI and chat
    - platform_name: System identifier for routing (ASCII, no spaces)
    - Auto-generates API key on creation
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "display_name": "تیم هوش مصنوعی داخلی",
                    "platform_name": "Internal-BI",
                    "monthly_quota": 100000,
                    "daily_quota": 5000,
                },
                {
                    "display_name": "پلتفرم بازاریابی",
                    "platform_name": "External-Marketing",
                    "monthly_quota": 50000,
                    "daily_quota": 2000,
                },
                {
                    "platform_name": "Data-Analytics",
                    "monthly_quota": 75000,
                },
            ]
        }
    )

    display_name: Optional[str] = Field(
        None,
        description="Human-friendly display name (supports Persian/Farsi). Defaults to platform_name if not provided.",
        examples=["تیم هوش مصنوعی داخلی", "Internal BI Team", "پلتفرم بازاریابی"],
    )
    platform_name: str = Field(
        ...,
        description="System identifier for routing (ASCII, no spaces, e.g., 'Internal-BI', 'External-Marketing')",
        examples=["Internal-BI", "External-Marketing", "Data-Analytics"],
    )
    monthly_quota: Optional[int] = Field(
        None, description="Monthly request quota (None = unlimited)", examples=[100000, None]
    )
    daily_quota: Optional[int] = Field(
        None, description="Daily request quota (None = unlimited)", examples=[5000, None]
    )


class TeamUpdate(BaseModel):
    """
    Request model for updating a team.

    Field Distinction:
    - display_name: Human-friendly name for admin UI and reports
    - platform_name: System identifier for routing and session isolation
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "display_name": "Internal BI Team",
                    "platform_name": "Internal-BI-Updated",
                    "monthly_quota": 150000,
                    "daily_quota": 7000,
                    "is_active": True,
                },
                {"is_active": False},
                {
                    "display_name": "Marketing Platform",
                    "platform_name": "Marketing-Platform",
                },
            ]
        }
    )

    display_name: Optional[str] = Field(None, examples=["Internal BI Team"])
    platform_name: Optional[str] = Field(None, examples=["Internal-BI-Updated"])
    monthly_quota: Optional[int] = Field(None, examples=[150000])
    daily_quota: Optional[int] = Field(None, examples=[7000])
    is_active: Optional[bool] = Field(None, examples=[True, False])


class TeamResponse(BaseModel):
    """
    Response model for team with usage statistics.

    Includes API key prefix and usage data (one key per team).

    Field Distinction:
    - display_name: Human-friendly name for display purposes
    - platform_name: System identifier for routing/operations
    - usage: Recent usage statistics (last 30 days by default)
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "display_name": "Internal BI Team",
                    "platform_name": "Internal-BI",
                    "monthly_quota": 100000,
                    "daily_quota": 5000,
                    "is_active": True,
                    "api_key_prefix": "ark_1234",
                    "api_key_last_used": "2025-01-15T14:30:00",
                    "created_at": "2025-01-01T10:00:00",
                    "updated_at": "2025-01-15T14:30:00",
                    "usage": {
                        "period": {
                            "start": "2025-01-01T00:00:00",
                            "end": "2025-01-31T23:59:59",
                            "days": 30,
                        },
                        "requests": {"total": 15000, "successful": 14850, "failed": 150},
                        "tokens": {"total": 1500000, "average_per_request": 100},
                        "cost": {"total": 15.50, "currency": "USD"},
                    },
                }
            ]
        },
    )

    id: int = Field(..., examples=[1])
    display_name: str = Field(..., examples=["Internal BI Team"])
    platform_name: str = Field(..., examples=["Internal-BI"])
    monthly_quota: Optional[int] = Field(None, examples=[100000])
    daily_quota: Optional[int] = Field(None, examples=[5000])
    is_active: bool = Field(..., examples=[True])
    api_key_prefix: Optional[str] = Field(None, examples=["ark_1234"])
    api_key_last_used: Optional[datetime] = Field(None, examples=["2025-01-15T14:30:00"])
    created_at: datetime
    updated_at: datetime
    usage: Optional[Dict[str, Any]] = Field(
        None,
        description="Usage statistics for the team (last 30 days by default)",
    )


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
                    "display_name": "تیم هوش مصنوعی داخلی",
                    "platform_name": "Internal-BI",
                    "monthly_quota": 100000,
                    "daily_quota": 5000,
                    "is_active": True,
                    "created_at": "2025-01-15T10:00:00",
                    "api_key": "ark_1234567890abcdef1234567890abcdef12345678",
                    "warning": "Save this API key securely. It will not be shown again.",
                }
            ]
        }
    )

    id: int = Field(..., examples=[1])
    display_name: str = Field(..., examples=["تیم هوش مصنوعی داخلی", "Internal BI Team"])
    platform_name: str = Field(..., examples=["Internal-BI"])
    monthly_quota: Optional[int] = Field(None, examples=[100000])
    daily_quota: Optional[int] = Field(None, examples=[5000])
    is_active: bool = Field(..., examples=[True])
    created_at: datetime
    api_key: str = Field(
        ...,
        description="Full API key - shown only once!",
        examples=["ark_1234567890abcdef1234567890abcdef12345678"],
    )
    warning: str = "Save this API key securely. It will not be shown again."


class UsageStatsResponse(BaseModel):
    """Response model for usage statistics (team-based only, no api_key_id)

    Note: team_name contains the team's display_name (supports Persian/Farsi)
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "team_id": 1,
                    "team_name": "تیم هوش مصنوعی داخلی",
                    "period": {
                        "start": "2025-01-01T00:00:00",
                        "end": "2025-01-31T23:59:59",
                        "days": 30,
                    },
                    "requests": {"total": 15000, "successful": 14850, "failed": 150},
                    "tokens": {"total": 1500000, "average_per_request": 100},
                    "cost": {"total": 15.50, "currency": "USD"},
                    "performance": {"average_response_time_ms": 850, "p95_response_time_ms": 1200},
                    "models": [
                        {"model": "Gemini 2.0 Flash", "requests": 8000, "percentage": 53.3},
                        {"model": "GPT-5 Chat", "requests": 5000, "percentage": 33.3},
                        {"model": "DeepSeek v3", "requests": 2000, "percentage": 13.3},
                    ],
                }
            ]
        }
    )

    team_id: Optional[int] = Field(None, examples=[1])
    team_name: Optional[str] = Field(
        None,
        description="Team display name (supports Persian/Farsi)",
        examples=["تیم هوش مصنوعی داخلی", "Internal BI Team"],
    )
    period: dict
    requests: dict
    tokens: dict
    cost: dict
    performance: dict
    models: List[dict]


# ===========================
# Platform Information & Statistics (Admin Only)
# ===========================


class AdminDashboardResponse(BaseModel):
    """
    Unified admin dashboard response with platform info and statistics

    Combines health check, platform configurations, and statistics into a single endpoint
    """
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "service": "Arash External API Service",
                    "version": "1.1.0",
                    "status": "healthy",
                    "timestamp": "2025-01-15T14:30:00",
                    "platforms": {
                        "telegram": {
                            "type": "public",
                            "model": "Gemini 2.0 Flash",
                            "rate_limit": 20,
                            "commands": ["start", "help", "model", "clear"],
                            "max_history": 10,
                            "features": {
                                "model_switching": False,
                                "requires_auth": True
                            }
                        },
                        "internal": {
                            "type": "private",
                            "default_model": "Gemini 2.0 Flash",
                            "available_models": ["Gemini 2.0 Flash", "GPT-5 Chat", "DeepSeek v3"],
                            "rate_limit": 60,
                            "commands": ["start", "help", "model", "models", "clear", "status"],
                            "max_history": 30,
                            "features": {
                                "model_switching": True,
                                "requires_auth": True
                            }
                        }
                    },
                    "statistics": {
                        "total_sessions": 150,
                        "active_sessions": 25,
                        "telegram": {
                            "sessions": 10,
                            "messages": 500,
                            "active": 5,
                            "model": "Gemini 2.0 Flash"
                        },
                        "internal": {
                            "sessions": 140,
                            "messages": 5000,
                            "active": 20,
                            "models_used": {
                                "Gemini 2.0 Flash": 80,
                                "GPT-5 Chat": 40,
                                "DeepSeek v3": 20
                            },
                            "team_breakdown": [
                                {
                                    "team_id": 1,
                                    "team_name": "Internal BI",
                                    "sessions": 100,
                                    "messages": 3000,
                                    "active": 15,
                                    "models_used": {"Gemini 2.0 Flash": 60}
                                }
                            ]
                        }
                    }
                }
            ]
        }
    )

    service: str = Field(..., examples=["Arash External API Service"])
    version: str = Field(..., examples=["1.1.0"])
    status: str = Field(..., examples=["healthy"])
    timestamp: datetime
    platforms: Dict[str, Dict[str, Any]]
    statistics: Dict[str, Any]


@router.get("/", response_model=AdminDashboardResponse)
async def admin_dashboard(
    api_key=Depends(require_admin_access),
):
    """
    Unified admin dashboard with platform info and statistics (ADMIN ONLY)

    Returns comprehensive information including:
    - Service health and version
    - Platform configurations (Telegram + Internal)
    - Session statistics (overall + per team)

    SECURITY: Exposes Telegram platform details - Admin access required
    """
    db = get_db_session()

    # Get platform configurations
    telegram_config = platform_manager.get_config("telegram")
    internal_config = platform_manager.get_config("internal")

    # Get team name mapping for statistics
    teams = APIKeyManager.list_all_teams(db)
    team_name_map = {team.id: team.display_name for team in teams}

    # Calculate statistics
    total_sessions = len(session_manager.sessions)
    active_sessions = session_manager.get_active_session_count(minutes=5)

    telegram_stats = {
        "sessions": 0,
        "messages": 0,
        "active": 0,
        "model": get_friendly_model_name(telegram_config.model),
    }

    internal_stats = {
        "sessions": 0,
        "messages": 0,
        "active": 0,
        "models_used": defaultdict(int),
    }

    team_stats = defaultdict(
        lambda: {
            "team_id": None,
            "team_name": "Unknown",
            "sessions": 0,
            "messages": 0,
            "active": 0,
            "models_used": defaultdict(int),
        }
    )

    for session in session_manager.sessions.values():
        is_active = not session.is_expired(5)

        if session.platform == "telegram":
            telegram_stats["sessions"] += 1
            telegram_stats["messages"] += session.total_message_count
            if is_active:
                telegram_stats["active"] += 1
        elif session.team_id is not None:
            internal_stats["sessions"] += 1
            internal_stats["messages"] += session.total_message_count
            friendly_model = get_friendly_model_name(session.current_model)
            internal_stats["models_used"][friendly_model] += 1
            if is_active:
                internal_stats["active"] += 1

            team_id = session.team_id
            if team_id not in team_stats:
                team_stats[team_id]["team_id"] = team_id
                team_stats[team_id]["team_name"] = team_name_map.get(team_id, f"Team {team_id}")

            team_stats[team_id]["sessions"] += 1
            team_stats[team_id]["messages"] += session.total_message_count
            team_stats[team_id]["models_used"][friendly_model] += 1
            if is_active:
                team_stats[team_id]["active"] += 1

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
    team_breakdown.sort(key=lambda x: x["sessions"], reverse=True)

    return AdminDashboardResponse(
        service="Arash External API Service",
        version="1.1.0",
        status="healthy",
        timestamp=datetime.now(),
        platforms={
            "telegram": {
                "type": "public",
                "model": get_friendly_model_name(telegram_config.model),
                "rate_limit": telegram_config.rate_limit,
                "commands": telegram_config.commands,
                "max_history": telegram_config.max_history,
                "features": {
                    "model_switching": telegram_config.allow_model_switch,
                    "requires_auth": telegram_config.requires_auth,
                },
            },
            "internal": {
                "type": "private",
                "default_model": get_friendly_model_name(internal_config.model),
                "available_models": [
                    get_friendly_model_name(m) for m in internal_config.available_models
                ],
                "rate_limit": internal_config.rate_limit,
                "commands": internal_config.commands,
                "max_history": internal_config.max_history,
                "features": {
                    "model_switching": internal_config.allow_model_switch,
                    "requires_auth": internal_config.requires_auth,
                },
            },
        },
        statistics={
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "telegram": telegram_stats,
            "internal": {
                **internal_stats,
                "models_used": dict(internal_stats["models_used"]),
                "team_breakdown": team_breakdown,
            },
        },
    )


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
                        "warning": "Save this API key securely. It will not be shown again.",
                    }
                }
            },
        },
        401: {
            "description": "Authentication required",
            "content": {"application/json": {"example": {"detail": "Authentication required"}}},
        },
        403: {
            "description": "Invalid super admin API key",
            "content": {"application/json": {"example": {"detail": "Invalid super admin API key"}}},
        },
    },
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
            detail=f"Team with platform name '{team_data.platform_name}' already exists",
        )

    # Create team with auto-generated API key
    team, api_key_string = APIKeyManager.create_team_with_key(
        db=db,
        platform_name=team_data.platform_name,
        display_name=team_data.display_name,
        monthly_quota=team_data.monthly_quota,
        daily_quota=team_data.daily_quota,
    )

    return TeamCreateResponse(
        id=team.id,
        display_name=team.display_name,
        platform_name=team.platform_name,
        monthly_quota=team.monthly_quota,
        daily_quota=team.daily_quota,
        is_active=team.is_active,
        created_at=team.created_at,
        api_key=api_key_string,
    )


class TeamsListResponse(BaseModel):
    """Response model for teams listing with optional total report"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "teams": [
                        {
                            "id": 1,
                            "display_name": "Internal BI Team",
                            "platform_name": "Internal-BI",
                            "monthly_quota": 100000,
                            "daily_quota": 5000,
                            "is_active": True,
                            "api_key_prefix": "ark_1234",
                            "usage": {
                                "requests": {"total": 15000, "successful": 14850}
                            }
                        }
                    ],
                    "total_report": {
                        "total_teams": 5,
                        "active_teams": 4,
                        "total_requests": 75000,
                        "total_successful": 74250,
                        "total_failed": 750,
                        "total_cost": 75.50
                    }
                }
            ]
        }
    )

    teams: List[TeamResponse]
    total_report: Optional[Dict[str, Any]] = Field(
        None,
        description="Total aggregated report across all teams (included when totally=true)",
    )


@router.get("/teams")
async def get_teams(
    team_id: Optional[int] = None,
    active_only: bool = True,
    days: int = 30,
    totally: bool = False,
    api_key=Depends(require_admin_access),
):
    """
    Get teams with usage statistics (Admin only)

    Parameters:
    - team_id: Optional team ID to get specific team (returns single item list)
    - active_only: Filter active teams only (default: True)
    - days: Number of days for usage statistics (default: 30)
    - totally: Include total aggregated report across all teams (default: False)

    Returns:
    - List of teams with usage data
    - Optional total report when totally=true

    Examples:
    - GET /admin/teams - List all active teams with usage
    - GET /admin/teams?team_id=1 - Get specific team with usage
    - GET /admin/teams?totally=true - List all teams with total report
    - GET /admin/teams?active_only=false&days=7 - All teams with 7-day usage
    """
    db = get_db_session()

    # Get teams based on filter
    if team_id:
        team = APIKeyManager.get_team_by_id(db, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        teams = [team]
    else:
        teams = APIKeyManager.list_all_teams(db, active_only=active_only)

    # Calculate start date for usage statistics
    start_date = datetime.utcnow() - timedelta(days=days)

    # Build response with API key prefix and usage for each team
    responses = []
    total_requests = 0
    total_successful = 0
    total_failed = 0
    total_cost = 0.0

    for team in teams:
        # Get the team's API key (one per team)
        api_key_obj = db.query(APIKey).filter(APIKey.team_id == team.id).first()

        # Get usage statistics for the team
        try:
            usage_stats = UsageTracker.get_team_usage_stats(db, team.id, start_date)
            # Remove team_id and team_name from usage stats (already in TeamResponse)
            usage_stats.pop("team_id", None)
            usage_stats.pop("team_name", None)

            # Aggregate for total report
            if totally:
                total_requests += usage_stats.get("requests", {}).get("total", 0)
                total_successful += usage_stats.get("requests", {}).get("successful", 0)
                total_failed += usage_stats.get("requests", {}).get("failed", 0)
                total_cost += usage_stats.get("cost", {}).get("total", 0.0)
        except Exception as e:
            logger.warning(f"Failed to get usage stats for team {team.id}: {e}")
            usage_stats = None

        responses.append(
            TeamResponse(
                id=team.id,
                display_name=team.display_name,
                platform_name=team.platform_name,
                monthly_quota=team.monthly_quota,
                daily_quota=team.daily_quota,
                is_active=team.is_active,
                api_key_prefix=api_key_obj.key_prefix if api_key_obj else None,
                api_key_last_used=api_key_obj.last_used_at if api_key_obj else None,
                created_at=team.created_at,
                updated_at=team.updated_at,
                usage=usage_stats,
            )
        )

    # Build total report if requested
    total_report = None
    if totally:
        total_report = {
            "total_teams": len(responses),
            "active_teams": sum(1 for r in responses if r.is_active),
            "total_requests": total_requests,
            "total_successful": total_successful,
            "total_failed": total_failed,
            "total_cost": round(total_cost, 2),
            "currency": "USD",
            "period": {
                "start": start_date.isoformat(),
                "end": datetime.utcnow().isoformat(),
                "days": days,
            },
        }

    return TeamsListResponse(
        teams=responses,
        total_report=total_report,
    )


@router.patch("/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_data: TeamUpdate,
    days: int = 30,
    api_key=Depends(require_admin_access),
):
    """
    Update team settings (Admin only)

    Returns updated team with usage statistics.

    Parameters:
    - days: Number of days for usage statistics (default: 30)
    """
    db = get_db_session()

    team = APIKeyManager.update_team(
        db=db,
        team_id=team_id,
        display_name=team_data.display_name,
        platform_name=team_data.platform_name,
        monthly_quota=team_data.monthly_quota,
        daily_quota=team_data.daily_quota,
        is_active=team_data.is_active,
    )

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Get the team's API key
    api_key_obj = db.query(APIKey).filter(APIKey.team_id == team.id).first()

    # Get usage statistics
    start_date = datetime.utcnow() - timedelta(days=days)
    try:
        usage_stats = UsageTracker.get_team_usage_stats(db, team.id, start_date)
        usage_stats.pop("team_id", None)
        usage_stats.pop("team_name", None)
    except Exception as e:
        logger.warning(f"Failed to get usage stats for team {team.id}: {e}")
        usage_stats = None

    return TeamResponse(
        id=team.id,
        display_name=team.display_name,
        platform_name=team.platform_name,
        monthly_quota=team.monthly_quota,
        daily_quota=team.daily_quota,
        is_active=team.is_active,
        api_key_prefix=api_key_obj.key_prefix if api_key_obj else None,
        api_key_last_used=api_key_obj.last_used_at if api_key_obj else None,
        created_at=team.created_at,
        updated_at=team.updated_at,
        usage=usage_stats,
    )
