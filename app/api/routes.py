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

from typing import Optional, Union
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
from app.api.dependencies import require_team_access, require_chat_access
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
                                "conversation_id": "conv_67890",
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
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Authentication required. Please provide an API key in the Authorization header."
                    }
                }
            }
        },
        403: {
            "description": "Invalid API key",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid API key. Please check your credentials."
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
    auth: Union[str, APIKey] = Depends(require_chat_access),
):
    """
    Process a chat message - **AUTHENTICATION REQUIRED**.

    ## Security Update (CRITICAL)
    **Authentication is now MANDATORY for all requests.**
    - Telegram bot: Must use TELEGRAM_SERVICE_KEY
    - External teams: Must use their team API keys
    - Unauthenticated requests: REJECTED with 401

    ## Authentication Modes

    ### 1. TELEGRAM MODE (Telegram bot service):
    - Telegram bot uses TELEGRAM_SERVICE_KEY in Authorization header
    - Platform="telegram", no team_id
    - Session keys: telegram:conversation_id

    ### 2. TEAM MODE (External authenticated teams):
    - External teams use their team API keys
    - Platform auto-detected from team.platform_name
    - Session keys: platform_name:team_id:conversation_id (team isolation enforced)

    ## Conversation ID Logic
    - **No conversation_id provided**: NEW conversation (auto-generated UUID)
    - **conversation_id provided**: CONTINUATION of existing conversation
    - Conversation IDs uniquely identify each multi-message dialogue

    ## Examples

    ### TELEGRAM BOT REQUEST:
    ```http
    Authorization: Bearer <TELEGRAM_SERVICE_KEY>
    ```
    ```json
    {
      "user_id": "telegram_user_12345",
      "text": "سلام، چطوری؟",
      "conversation_id": "existing_conv_id_or_null_for_new"
    }
    ```

    ### EXTERNAL TEAM REQUEST:
    ```http
    Authorization: Bearer ark_1234567890abcdef
    ```
    ```json
    {
      "user_id": "user123",
      "text": "چطور می‌تونم مدل رو عوض کنم؟",
      "conversation_id": null
    }
    ```
    **Response includes conversation_id** - use it for continuing the conversation.

    ## Security
    - Telegram traffic: Authenticated and logged as [TELEGRAM]
    - Team traffic: Authenticated and logged as [TEAM]
    - Unauthorized traffic: Blocked with 401/403
    - Super admins can now track ALL API usage
    """
    import uuid

    # Auto-generate conversation_id if not provided (NEW conversation)
    # If conversation_id is provided, it's a CONTINUATION of existing conversation
    conversation_id = message.conversation_id or str(uuid.uuid4())

    # Auto-generate message_id internally
    message_id = str(uuid.uuid4())

    # Determine mode based on authentication type
    if auth == "telegram":
        # TELEGRAM MODE: Telegram bot service
        platform_name = "telegram"
        team_id = None
        api_key_id = None
        api_key_prefix = None

        logger.info(
            f"[TELEGRAM] bot_request user_id={message.user_id} conversation_id={conversation_id} "
            f"new_conversation={message.conversation_id is None}"
        )
    else:
        # TEAM MODE: Authenticated external team
        platform_name = auth.team.platform_name
        team_id = auth.team_id
        api_key_id = auth.id
        api_key_prefix = auth.key_prefix

        logger.info(
            f"[TEAM] chat_request platform={platform_name} team_id={team_id} "
            f"user_id={message.user_id} conversation_id={conversation_id} "
            f"new_conversation={message.conversation_id is None}"
        )

    # Process message (handles both modes)
    return await message_processor.process_message_simple(
        platform_name=platform_name,
        team_id=team_id,
        api_key_id=api_key_id,
        api_key_prefix=api_key_prefix,
        user_id=message.user_id,
        conversation_id=conversation_id,
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
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Authentication required. Please provide an API key in the Authorization header."
                    }
                }
            }
        },
        403: {
            "description": "Invalid API key",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid API key. Please check your credentials."
                    }
                }
            }
        }
    }
)
async def get_commands(
    auth: Union[str, APIKey] = Depends(require_chat_access),
):
    """
    Get available commands with Persian descriptions - **AUTHENTICATION REQUIRED**.

    ## Security Update (CRITICAL)
    **Authentication is now MANDATORY for all requests.**
    - Telegram bot: Must use TELEGRAM_SERVICE_KEY
    - External teams: Must use their team API keys
    - Unauthenticated requests: REJECTED with 401

    ## Authentication Modes

    ### 1. TELEGRAM MODE:
    - Telegram bot uses TELEGRAM_SERVICE_KEY
    - Returns Telegram platform commands

    ### 2. TEAM MODE:
    - External teams use their team API keys
    - Returns commands for authenticated team's platform

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
    - Telegram traffic: Logged as [TELEGRAM]
    - Team traffic: Logged as [TEAM]
    - Unauthorized traffic: Blocked with 401/403
    """
    # Determine platform based on authentication type
    if auth == "telegram":
        # TELEGRAM MODE: Telegram bot service
        platform_name = "telegram"
        logger.info("[TELEGRAM] commands_request platform=telegram")
    else:
        # TEAM MODE: Authenticated external team
        platform_name = auth.team.platform_name
        logger.info(f"[TEAM] commands_request platform={platform_name} team_id={auth.team_id}")

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
