"""
API routes
"""

from typing import Optional, Dict, Any
from datetime import datetime
from collections import defaultdict
import logging

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Header
from fastapi.security import HTTPAuthorizationCredentials

from app.models.schemas import (
    IncomingMessage,
    BotResponse,
    SessionListResponse,
    StatsResponse,
    HealthCheckResponse,
)
from app.services.message_processor import message_processor
from app.services.session_manager import session_manager
from app.services.platform_manager import platform_manager
from app.services.ai_client import ai_client
from app.api.dependencies import (
    get_auth,
    verify_internal_api_key,
    verify_webhook_secret,
)
from app.utils.parsers import parse_webhook_data
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/", response_model=HealthCheckResponse)
async def root():
    """Health check with platform information"""
    telegram_config = platform_manager.get_config("telegram")
    internal_config = platform_manager.get_config("internal")

    return HealthCheckResponse(
        service="Arash External API Service",
        version="1.0.0",
        status="healthy",
        platforms={
            "telegram": {
                "type": "public",
                "model": telegram_config.model,
                "rate_limit": telegram_config.rate_limit,
                "model_switching": False,
            },
            "internal": {
                "type": "private",
                "models": internal_config.available_models,
                "rate_limit": internal_config.rate_limit,
                "model_switching": True,
            },
        },
        active_sessions=len(session_manager.sessions),
        timestamp=datetime.now(),
    )


@router.get("/health")
async def health_check():
    """Detailed health check"""
    ai_service_healthy = await ai_client.health_check()

    return {
        "status": "healthy" if ai_service_healthy else "degraded",
        "service": "Arash External API Service",
        "version": "1.0.0",
        "components": {
            "api": "healthy",
            "ai_service": "healthy" if ai_service_healthy else "unhealthy",
            "sessions": "healthy",
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/message", response_model=BotResponse)
async def process_message_endpoint(
    message: IncomingMessage,
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(get_auth),
):
    """Process message with optional authentication"""

    # Add auth token to message if provided
    if authorization:
        message.auth_token = authorization.credentials

    return await message_processor.process_message(message)


@router.post("/webhook/{platform}", response_model=BotResponse)
async def webhook_handler(
    platform: str,
    data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    x_webhook_secret: Optional[str] = Header(None),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(get_auth),
):
    """Platform webhook handler"""

    # Verify webhook secret for internal platform
    if platform == "internal":
        if not verify_webhook_secret(x_webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    # Parse webhook data based on platform
    message = parse_webhook_data(platform, data)
    if not message:
        return BotResponse(success=True, response="Webhook processed")

    # Add auth token if provided
    if authorization:
        message.auth_token = authorization.credentials

    # Process message
    result = await message_processor.process_message(message)

    # Clean old sessions in background
    background_tasks.add_task(session_manager.clear_old_sessions)

    return result


@router.get("/platforms")
async def get_platforms():
    """Get platform configurations"""
    telegram_config = platform_manager.get_config("telegram")
    internal_config = platform_manager.get_config("internal")

    return {
        "telegram": {
            "type": "public",
            "model": telegram_config.model,
            "rate_limit": telegram_config.rate_limit,
            "commands": telegram_config.commands,
            "max_history": telegram_config.max_history,
            "features": {"model_switching": False, "requires_auth": False},
        },
        "internal": {
            "type": "private",
            "default_model": internal_config.model,
            "available_models": internal_config.available_models,
            "rate_limit": internal_config.rate_limit,
            "commands": internal_config.commands,
            "max_history": internal_config.max_history,
            "features": {"model_switching": True, "requires_auth": True},
        },
    }


@router.get("/sessions", response_model=SessionListResponse)
async def get_sessions(
    platform: Optional[str] = Query(
        None, description="Filter by platform (telegram/internal)"
    ),
    type: Optional[str] = Query(None, description="Filter by type (public/private)"),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(get_auth),
):
    """Get active sessions"""

    # Check if requester has access to detailed info
    is_authenticated = False
    if authorization:
        internal_config = platform_manager.get_config("internal")
        if authorization.credentials == internal_config.api_key:
            is_authenticated = True

    sessions = []
    for session in session_manager.sessions.values():
        # Apply filters
        if platform and session.platform != platform:
            continue
        if type and session.platform_config.get("type") != type:
            continue

        session_info = {
            "session_id": session.session_id,
            "platform": session.platform,
            "platform_type": session.platform_config.get("type"),
            "current_model": session.current_model,
            "message_count": session.message_count,
            "last_activity": session.last_activity.isoformat(),
        }

        # Add sensitive info only if authenticated
        if is_authenticated:
            session_info.update(
                {
                    "user_id": session.user_id,
                    "chat_id": session.chat_id,
                    "history_length": len(session.history),
                    "is_admin": session.is_admin,
                }
            )

        sessions.append(session_info)

    return SessionListResponse(
        total=len(sessions), authenticated=is_authenticated, sessions=sessions
    )


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(get_auth),
):
    """Get specific session details"""

    for session in session_manager.sessions.values():
        if session.session_id == session_id:
            # Check if requester has access
            if session.platform == "internal":
                if not verify_internal_api_key(authorization):
                    raise HTTPException(status_code=403, detail="Access denied")

            return {
                "session": {
                    **session.dict(exclude={"history"}),
                    "uptime_seconds": session.get_uptime_seconds(),
                },
                "history_length": len(session.history),
                "platform_config": session.platform_config,
            }

    raise HTTPException(status_code=404, detail="Session not found")


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    authorization: HTTPAuthorizationCredentials = Depends(verify_internal_api_key),
):
    """Delete a session"""

    for key, session in list(session_manager.sessions.items()):
        if session.session_id == session_id:
            del session_manager.sessions[key]
            logger.info(f"Session {session_id} deleted by admin")
            return {"success": True, "message": "Session deleted"}

    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/stats", response_model=StatsResponse)
async def get_statistics():
    """Get service statistics"""

    total_sessions = len(session_manager.sessions)
    active_sessions = session_manager.get_active_session_count(minutes=5)

    # Statistics by platform
    telegram_stats = {
        "sessions": 0,
        "messages": 0,
        "active": 0,
        "model": platform_manager.get_config("telegram").model,
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
            internal_stats["models_used"][session.current_model] += 1
            if is_active:
                internal_stats["active"] += 1

    return StatsResponse(
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        telegram=telegram_stats,
        internal={**internal_stats, "models_used": dict(internal_stats["models_used"])},
        uptime_seconds=0,  # Will be set by main app
    )


@router.post("/admin/clear-sessions")
async def clear_sessions(
    platform: Optional[str] = None,
    authorization: HTTPAuthorizationCredentials = Depends(verify_internal_api_key),
):
    """Clear sessions (admin only)"""

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

    logger.info(f"Admin cleared {len(keys_to_remove)} sessions")

    return {
        "success": True,
        "cleared": len(keys_to_remove),
        "message": f"Cleared {len(keys_to_remove)} sessions",
    }
