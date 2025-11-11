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
from app.api.dependencies import require_team_access, optional_team_access

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post("/chat", response_model=BotResponse)
async def chat(
    message: IncomingMessage,
    api_key: Optional[APIKey] = Depends(optional_team_access),
):
    """
    Process a chat message - supports both public and private access (modular endpoint).

    MODES:
    1. PUBLIC MODE (Telegram bot - no authentication):
       - No Authorization header required
       - Uses platform="telegram" with no team_id
       - Session keys: telegram:chat_id (no team isolation)

    2. PRIVATE MODE (Authenticated teams):
       - Requires valid API key in Authorization header
       - Platform auto-detected from team.platform_name
       - Session keys: platform_name:team_id:chat_id (team isolation enforced)

    AUTHENTICATION:
    - Optional: No auth header → Public Telegram bot
    - Optional: Valid auth header → Private authenticated team
    - Error: Invalid auth header → 403 Forbidden

    PUBLIC REQUEST (Telegram):
    {
      "user_id": "telegram_user_id",
      "text": "Hello",
      "chat_id": "telegram_chat_id"
    }

    PRIVATE REQUEST (Authenticated):
    Authorization: Bearer <your-api-key>
    {
      "user_id": "user123",
      "text": "Hello",
      "chat_id": "optional-for-continuation"
    }

    RESPONSE:
    {
      "success": true,
      "response": "Hi! How can I help?",
      "chat_id": "chat-id",
      "session_id": "platform:chat_id OR platform:team_id:chat_id",
      "model": "Model Name",
      "message_count": 1
    }

    SECURITY:
    - Public: No team isolation (Telegram only)
    - Private: Complete team isolation via session tagging
    - Invalid keys rejected (no fallback to public)
    """
    import uuid

    # Auto-generate chat_id if not provided (new conversation)
    chat_id = message.chat_id or str(uuid.uuid4())

    # Auto-generate message_id internally
    message_id = str(uuid.uuid4())

    # Determine mode based on API key presence
    if api_key is None:
        # PUBLIC MODE: Telegram bot (no authentication)
        platform_name = "telegram"
        team_id = None
        api_key_id = None
        api_key_prefix = None

        logger.info(
            f"[PUBLIC] telegram_request user_id={message.user_id} chat_id={chat_id}"
        )
    else:
        # PRIVATE MODE: Authenticated team
        platform_name = api_key.team.platform_name
        team_id = api_key.team_id
        api_key_id = api_key.id
        api_key_prefix = api_key.key_prefix

        logger.info(
            f"[PRIVATE] chat_request platform={platform_name} team_id={team_id} "
            f"user_id={message.user_id} chat_id={chat_id}"
        )

    # Process message (handles both modes)
    return await message_processor.process_message_simple(
        platform_name=platform_name,
        team_id=team_id,
        api_key_id=api_key_id,
        api_key_prefix=api_key_prefix,
        user_id=message.user_id,
        chat_id=chat_id,
        message_id=message_id,
        text=message.text,
    )
