"""
API routes with team isolation and security

SECURITY NOTE: All endpoints that access sessions or stats MUST enforce team isolation.
Teams can ONLY see their own sessions and statistics.
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
    HealthCheckResponse,
)
from app.models.database import APIKey
from app.services.message_processor import message_processor
from app.services.session_manager import session_manager
from app.services.platform_manager import platform_manager
from app.services.ai_client import ai_client
from app.api.dependencies import (
    get_auth,
    verify_api_key,
    require_admin_access,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Public health check endpoint (no auth required)

    SECURITY: Does NOT expose platform details or Telegram info
    """
    ai_service_healthy = await ai_client.health_check()

    return {
        "status": "healthy" if ai_service_healthy else "degraded",
        "service": "Arash External API Service",
        "version": "1.1.0",
        "components": {
            "api": "healthy",
            "ai_service": "healthy" if ai_service_healthy else "unhealthy",
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/message", response_model=BotResponse)
async def process_message_endpoint(
    message: IncomingMessage,
    api_key: APIKey = Depends(verify_api_key),
):
    """
    Process message with REQUIRED authentication

    SECURITY:
    - API key authentication is REQUIRED
    - Team isolation enforced - session is tagged with team_id
    - Each team can only access their own sessions
    """
    # Only allow 'internal' platform for API-based access
    if message.platform != "internal":
        raise HTTPException(
            status_code=400,
            detail="Invalid platform. Use 'internal' for API access."
        )

    # Extract team info from validated API key
    team_id = api_key.team_id
    api_key_id = api_key.id
    api_key_prefix = api_key.key_prefix

    # SECURITY: Tag session with team info for isolation
    message.metadata["team_id"] = team_id
    message.metadata["api_key_id"] = api_key_id
    message.metadata["api_key_prefix"] = api_key_prefix

    return await message_processor.process_message(message)


# ==========================================
# WEBHOOK ENDPOINTS - CURRENTLY DISABLED
# ==========================================
# Webhooks are not in use yet. Uncomment when needed.
#
# @router.post("/webhook/{platform}", response_model=BotResponse)
# async def webhook_handler(
#     platform: str,
#     data: Dict[str, Any],
#     background_tasks: BackgroundTasks,
#     x_webhook_secret: Optional[str] = Header(None),
#     api_key: APIKey = Depends(verify_api_key),
# ):
#     """Platform webhook handler (DISABLED - not in use)"""
#     raise HTTPException(
#         status_code=501,
#         detail="Webhook functionality is not currently enabled"
#     )


@router.get("/sessions", response_model=SessionListResponse)
async def get_sessions(
    api_key: APIKey = Depends(verify_api_key),
):
    """
    Get active sessions for the authenticated team ONLY

    SECURITY:
    - REQUIRES authentication
    - Returns ONLY sessions belonging to the authenticated team
    - Complete team isolation enforced
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    team_id = api_key.team_id

    # SECURITY: Only get sessions for THIS team
    team_sessions = session_manager.get_sessions_by_team(team_id)

    sessions = []
    for session in team_sessions:
        from app.core.name_mapping import get_friendly_model_name

        session_info = {
            "session_id": session.session_id,
            "platform": session.platform,
            "current_model": get_friendly_model_name(session.current_model),
            "message_count": session.message_count,
            "last_activity": session.last_activity.isoformat(),
            "user_id": session.user_id,
            "chat_id": session.chat_id,
            "history_length": len(session.history),
        }

        sessions.append(session_info)

    return SessionListResponse(
        total=len(sessions),
        authenticated=True,
        sessions=sessions
    )


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    api_key: APIKey = Depends(verify_api_key),
):
    """
    Get specific session details

    SECURITY:
    - REQUIRES authentication
    - Only allows access to sessions owned by the authenticated team
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="Authentication required")

    team_id = api_key.team_id

    # Find the session
    for session in session_manager.sessions.values():
        if session.session_id == session_id:
            # SECURITY: Check team ownership
            if session.team_id != team_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: This session belongs to another team"
                )

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
    api_key: APIKey = Depends(verify_api_key),
):
    """
    Delete a session

    SECURITY:
    - REQUIRES authentication
    - Only allows deletion of sessions owned by the authenticated team
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="Authentication required")

    team_id = api_key.team_id

    # Find and delete the session
    for key, session in list(session_manager.sessions.items()):
        if session.session_id == session_id:
            # SECURITY: Check team ownership
            if session.team_id != team_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: This session belongs to another team"
                )

            del session_manager.sessions[key]
            logger.info(f"Session {session_id} deleted by team {team_id}")
            return {"success": True, "message": "Session deleted"}

    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/admin/clear-sessions")
async def clear_sessions(
    platform: Optional[str] = None,
    api_key: APIKey = Depends(require_admin_access),
):
    """
    Clear sessions (admin only)

    SECURITY: Admin-only endpoint
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

    logger.info(f"Admin cleared {len(keys_to_remove)} sessions")

    return {
        "success": True,
        "cleared": len(keys_to_remove),
        "message": f"Cleared {len(keys_to_remove)} sessions",
    }
