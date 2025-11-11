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


@router.post("/telegram", response_model=BotResponse)
async def telegram_chat(
    message: IncomingMessage,
):
    """
    Process a Telegram bot message (public, no authentication required).

    SECURITY:
    - No API key required (public Telegram bot)
    - Uses platform="telegram" with no team_id
    - Session keys: telegram:chat_id (no team isolation)

    Request:
    {
      "user_id": "telegram_user_id",
      "text": "Hello",
      "chat_id": "telegram_chat_id"
    }

    Response:
    {
      "success": true,
      "response": "Hi! How can I help?",
      "chat_id": "telegram_chat_id",
      "session_id": "telegram:chat_id",
      "model": "Gemini 2.0 Flash",
      "message_count": 1
    }
    """
    import uuid

    # Auto-generate chat_id if not provided (new conversation)
    chat_id = message.chat_id or str(uuid.uuid4())

    # Auto-generate message_id internally
    message_id = str(uuid.uuid4())

    logger.info(
        f"telegram_request user_id={message.user_id} chat_id={chat_id}"
    )

    # Process message for Telegram platform (no team_id, no API key)
    return await message_processor.process_message_simple(
        platform_name="telegram",
        team_id=None,  # Telegram doesn't use teams
        api_key_id=None,
        api_key_prefix=None,
        user_id=message.user_id,
        chat_id=chat_id,
        message_id=message_id,
        text=message.text,
    )


@router.post("/chat", response_model=BotResponse)
async def chat(
    message: IncomingMessage,
    api_key: APIKey = Depends(require_team_access),
):
    """
    Process a chat message (simplified interface).

    CHANGES FROM PREVIOUS VERSION:
    - Platform auto-detected from API key's team.platform_name
    - chat_id auto-generated if not provided (for new conversations)
    - message_id auto-generated internally
    - No metadata, type, or attachments (text-only in this version)

    SECURITY:
    - Requires valid API key (team or super admin)
    - Team isolation enforced via session keys (platform_name:team_id:chat_id)
    - Each team thinks only they exist

    Request:
    {
      "user_id": "user123",
      "text": "Hello",
      "chat_id": "optional-for-continuation"
    }

    Response:
    {
      "success": true,
      "response": "Hi! How can I help?",
      "chat_id": "generated-or-provided",
      "session_id": "Internal-BI:5:chat-id",
      "model": "GPT-5 Chat",
      "message_count": 1
    }
    """
    import uuid

    # Auto-generate chat_id if not provided (new conversation)
    chat_id = message.chat_id or str(uuid.uuid4())

    # Auto-generate message_id internally
    message_id = str(uuid.uuid4())

    # Extract platform from API key's team
    # This is transparent to the client - they don't know about platforms
    platform_name = api_key.team.platform_name
    team_id = api_key.team_id
    api_key_id = api_key.id
    api_key_prefix = api_key.key_prefix

    logger.info(
        f"chat_request platform={platform_name} team_id={team_id} "
        f"user_id={message.user_id} chat_id={chat_id}"
    )

    # Process message with simplified parameters
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
