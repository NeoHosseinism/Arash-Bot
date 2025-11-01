"""
Public API routes for external teams

SECURITY MODEL:
- External teams should think they're using a simple chatbot API
- NO exposure of: sessions, teams, access levels, or other teams
- Complete transparency: teams don't know about our internal architecture
"""

from typing import Optional
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import (
    IncomingMessage,
    BotResponse,
    HealthCheckResponse,
)
from app.models.database import APIKey
from app.services.message_processor import message_processor
from app.services.ai_client import ai_client
from app.api.dependencies import require_team_access

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Public health check endpoint (no authentication required)

    SECURITY: Does NOT expose any internal details
    """
    ai_service_healthy = await ai_client.health_check()

    return {
        "status": "healthy" if ai_service_healthy else "degraded",
        "service": "Arash External API Service",
        "version": "1.1.0",
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/chat", response_model=BotResponse)
async def chat(
    message: IncomingMessage,
    api_key: APIKey = Depends(require_team_access),
):
    """
    Process a chat message

    SECURITY:
    - Requires valid API key (any team)
    - Team isolation enforced internally via session tagging
    - External teams don't see team_id or internal metadata
    - Simple chatbot interface - no exposure of architecture

    External teams only see:
    - Input: message content
    - Output: bot response

    They DON'T see:
    - Session management
    - Team isolation
    - Access levels
    - Other teams
    """
    # Only allow 'internal' platform for API-based access
    if message.platform != "internal":
        raise HTTPException(
            status_code=400,
            detail="Invalid platform. Use 'internal' for API access."
        )

    # SECURITY: Tag session with team info for isolation (transparent to external teams)
    team_id = api_key.team_id
    api_key_id = api_key.id
    api_key_prefix = api_key.key_prefix

    message.metadata["team_id"] = team_id
    message.metadata["api_key_id"] = api_key_id
    message.metadata["api_key_prefix"] = api_key_prefix

    return await message_processor.process_message(message)
