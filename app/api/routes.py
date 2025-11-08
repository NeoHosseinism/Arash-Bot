"""
Public API routes for external teams (clients)

TWO-TIER ACCESS CONTROL:
These endpoints are accessible to ALL valid API keys (both TEAM and ADMIN levels).
However, they are designed for external teams (clients) using the chatbot service.

PUBLIC ENDPOINTS (ALL VALID API KEYS):
- /api/v1/chat - Process chat messages

SECURITY MODEL:
- External teams (TEAM level) think they're using a simple chatbot API
- NO exposure of: sessions, teams, access levels, or other teams
- Complete transparency: teams don't know about our internal architecture
- Team isolation enforced via session tagging (transparent to clients)

WHAT EXTERNAL TEAMS SEE:
- Simple chatbot API with message in, response out
- No complexity, no admin features, no multi-tenancy visibility

WHAT THEY DON'T SEE:
- Access levels (ADMIN vs TEAM)
- Other teams or their usage
- Session management internals
- Platform configuration
- Admin endpoints
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
