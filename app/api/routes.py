"""
Public API routes for external teams (clients)

TWO-TIER ACCESS CONTROL:
These endpoints are accessible to ALL valid API keys (both TEAM and ADMIN levels).
However, they are designed for external teams (clients) using the chatbot service.

PUBLIC ENDPOINTS (ALL VALID API KEYS):
- /v1/chat - Process chat messages

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
from app.services.platform_manager import platform_manager
from app.api.dependencies import require_team_access, optional_team_access
from app.core.constants import COMMAND_DESCRIPTIONS

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post(
    "/chat",
    response_model=BotResponse,
    responses={
        200: {
            "description": "Successful chat response",
            "content": {
                "application/json": {
                    "examples": {
                        "successful_response": {
                            "summary": "Successful chat response",
                            "value": {
                                "success": True,
                                "response": "سلام! چطور می‌تونم کمکتون کنم؟",
                                "chat_id": "chat_67890",
                                "session_id": "internal:1:chat_67890",
                                "model": "Gemini 2.0 Flash",
                                "message_count": 1
                            }
                        },
                        "rate_limit_exceeded": {
                            "summary": "Rate limit exceeded",
                            "value": {
                                "success": False,
                                "error": "rate_limit_exceeded",
                                "response": "⚠️ محدودیت سرعت. لطفاً قبل از ارسال پیام بعدی کمی صبر کنید.\n\nمحدودیت: 60 پیام در دقیقه"
                            }
                        },
                        "ai_service_error": {
                            "summary": "AI service unavailable",
                            "value": {
                                "success": False,
                                "error": "ai_service_unavailable",
                                "response": "متأسفم، سرویس هوش مصنوعی در حال حاضر در دسترس نیست. لطفاً چند لحظه دیگر دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
                            }
                        }
                    }
                }
            }
        },
        403: {
            "description": "Invalid API key",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid API key"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Error validating API key"
                    }
                }
            }
        }
    }
)
async def chat(
    message: IncomingMessage,
    api_key: Optional[APIKey] = Depends(optional_team_access),
):
    """
    Process a chat message - supports both public and private access (modular endpoint).

    ## Modes

    ### 1. PUBLIC MODE (Telegram bot - no authentication):
    - No Authorization header required
    - Uses platform="telegram" with no team_id
    - Session keys: telegram:chat_id (no team isolation)

    ### 2. PRIVATE MODE (Authenticated teams):
    - Requires valid API key in Authorization header
    - Platform auto-detected from team.platform_name
    - Session keys: platform_name:team_id:chat_id (team isolation enforced)

    ## Authentication
    - ✅ No auth header → Public Telegram bot
    - ✅ Valid auth header → Private authenticated team
    - ❌ Invalid auth header → 403 Forbidden

    ## Examples

    ### PUBLIC REQUEST (Telegram):
    ```json
    {
      "user_id": "telegram_user_id",
      "text": "سلام",
      "chat_id": "telegram_chat_id"
    }
    ```

    ### PRIVATE REQUEST (Authenticated):
    ```http
    Authorization: Bearer ark_1234567890abcdef
    ```
    ```json
    {
      "user_id": "user123",
      "text": "چطور می‌تونم مدل رو عوض کنم؟",
      "chat_id": "optional-for-continuation"
    }
    ```

    ## Security
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


@router.get(
    "/commands",
    responses={
        200: {
            "description": "List of available commands",
            "content": {
                "application/json": {
                    "examples": {
                        "telegram_commands": {
                            "summary": "Telegram (public) commands",
                            "value": {
                                "success": True,
                                "platform": "telegram",
                                "commands": [
                                    {
                                        "command": "start",
                                        "description": "شروع ربات و دریافت پیام خوش‌آمدگویی",
                                        "usage": "/start"
                                    },
                                    {
                                        "command": "help",
                                        "description": "نمایش راهنمای استفاده و دستورات موجود",
                                        "usage": "/help"
                                    },
                                    {
                                        "command": "clear",
                                        "description": "پاک کردن تاریخچه گفتگو و شروع مجدد",
                                        "usage": "/clear"
                                    }
                                ]
                            }
                        },
                        "internal_commands": {
                            "summary": "Internal (private) commands",
                            "value": {
                                "success": True,
                                "platform": "Internal-BI",
                                "commands": [
                                    {
                                        "command": "start",
                                        "description": "شروع ربات و دریافت پیام خوش‌آمدگویی",
                                        "usage": "/start"
                                    },
                                    {
                                        "command": "help",
                                        "description": "نمایش راهنمای استفاده و دستورات موجود",
                                        "usage": "/help"
                                    },
                                    {
                                        "command": "model",
                                        "description": "تغییر مدل هوش مصنوعی",
                                        "usage": "/model"
                                    },
                                    {
                                        "command": "models",
                                        "description": "نمایش لیست تمام مدل‌های موجود",
                                        "usage": "/models"
                                    },
                                    {
                                        "command": "clear",
                                        "description": "پاک کردن تاریخچه گفتگو و شروع مجدد",
                                        "usage": "/clear"
                                    },
                                    {
                                        "command": "status",
                                        "description": "نمایش وضعیت نشست و اطلاعات جاری",
                                        "usage": "/status"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
        403: {
            "description": "Invalid API key",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid API key"
                    }
                }
            }
        }
    }
)
async def get_commands(
    api_key: Optional[APIKey] = Depends(optional_team_access),
):
    """
    Get available commands with Persian descriptions - supports both public and private access.

    ## Modes

    ### 1. PUBLIC MODE (No authentication):
    - Returns Telegram commands
    - Platform: telegram

    ### 2. PRIVATE MODE (Authenticated):
    - Returns commands for authenticated team's platform
    - Platform: Based on team.platform_name

    ## Response Format
    ```json
    {
      "success": true,
      "platform": "telegram",
      "commands": [
        {
          "command": "start",
          "description": "شروع ربات و دریافت پیام خوش‌آمدگویی",
          "usage": "/start"
        }
      ]
    }
    ```

    ## Security
    - Public: Returns Telegram commands only
    - Private: Returns commands for user's platform
    """
    # Determine platform based on authentication
    if api_key is None:
        # PUBLIC MODE: Telegram bot
        platform_name = "telegram"
        logger.info("[PUBLIC] commands_request platform=telegram")
    else:
        # PRIVATE MODE: Authenticated team
        platform_name = api_key.team.platform_name
        logger.info(f"[PRIVATE] commands_request platform={platform_name} team_id={api_key.team_id}")

    # Get allowed commands for this platform
    allowed_commands = platform_manager.get_allowed_commands(platform_name)

    # Build command list with descriptions
    commands_list = []
    for cmd in allowed_commands:
        if cmd in COMMAND_DESCRIPTIONS:
            commands_list.append({
                "command": cmd,
                "description": COMMAND_DESCRIPTIONS[cmd],
                "usage": f"/{cmd}"
            })

    return {
        "success": True,
        "platform": platform_name,
        "commands": commands_list
    }
