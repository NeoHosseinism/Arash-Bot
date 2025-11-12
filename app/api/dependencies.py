"""
API dependencies for authentication and validation

TWO-PATH AUTHENTICATION SYSTEM:

1. SUPER ADMINS (Infrastructure Level):
   - Authentication: Environment variable SUPER_ADMIN_API_KEYS
   - NOT stored in database
   - Can access: ALL /v1/admin/* endpoints
   - Purpose: Internal team managing the service infrastructure
   - Completely separate from client database

2. TEAM API KEYS (Application Level):
   - Authentication: Database-backed API keys
   - Stored in api_keys table
   - Can access: ONLY /v1/chat endpoint
   - Purpose: External clients using the chatbot service
   - No admin access whatsoever

SECURITY:
- Complete separation: Admin auth (env vars) vs Team auth (database)
- External teams cannot access admin endpoints (no way to get super admin keys)
- External teams don't know about super admins or access levels
- Team isolation via session tagging
"""
from typing import Optional, Union
import logging
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.models.database import APIKey, get_db_session
from app.services.api_key_manager import APIKeyManager

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


def require_admin_access(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Require SUPER ADMIN access - infrastructure level (environment-based authentication)

    This dependency protects ALL /v1/admin/* endpoints.
    Authentication via SUPER_ADMIN_API_KEYS environment variable (NOT database).

    AUTHENTICATION:
    - Checks Authorization header against SUPER_ADMIN_API_KEYS environment variable
    - NO database lookup
    - Completely separate from team API keys

    USAGE:
    - Used by: All admin endpoints (/v1/admin/*)
    - Authentication: Environment variable (infrastructure level)
    - Returns: The validated super admin API key string

    ENDPOINTS PROTECTED:
    - Team management (create, list, update, delete teams)
    - API key management (create, list, revoke API keys for clients)
    - Usage statistics (view ALL teams' usage)
    - Platform information (Telegram + Internal config)
    - System administration (clear sessions, etc.)

    ERROR RESPONSES:
    - 401: No authorization header provided OR super admin keys not configured
    - 403: Invalid super admin API key

    SECURITY:
    - Super admin keys set via SUPER_ADMIN_API_KEYS environment variable
    - External teams have no way to obtain these keys
    - Complete separation from client database
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    # Check if super admin keys are configured
    super_admin_keys = settings.super_admin_keys_set
    if not super_admin_keys:
        logger.error("SUPER_ADMIN_API_KEYS not configured - admin endpoints unavailable")
        raise HTTPException(
            status_code=401,
            detail="Super admin authentication not configured"
        )

    # Validate against environment-based super admin keys
    provided_key = authorization.credentials
    if provided_key not in super_admin_keys:
        logger.warning(f"Invalid super admin API key attempted: {provided_key[:12]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid super admin API key"
        )

    logger.info(f"Super admin access granted (key: {provided_key[:12]}...)")
    return provided_key


def require_team_access(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> APIKey:
    """
    Require valid TEAM API key - application level (database-based authentication)

    This dependency protects the /v1/chat endpoint.
    Authentication via database-backed API keys (api_keys table).

    AUTHENTICATION:
    - Checks Authorization header against database (api_keys table)
    - Validates key hash, expiration, active status
    - Returns APIKey object with team_id for isolation

    USAGE:
    - Used by: /v1/chat endpoint
    - Authentication: Database lookup (application level)
    - Returns: Validated APIKey object (includes team_id for session isolation)

    SECURITY & TRANSPARENCY:
    - External teams think they're using a simple chatbot API
    - No exposure of super admins or admin endpoints
    - Complete team isolation via session tagging (transparent to clients)
    - No way to access admin functionality

    WHAT EXTERNAL TEAMS SEE:
    - Input: Message content
    - Output: Bot response
    - Simple API, no complexity

    WHAT THEY DON'T SEE:
    - Super admin authentication
    - Other teams or their usage
    - Session management internals
    - Admin endpoints existence
    - Platform configuration

    ERROR RESPONSES:
    - 401: No authorization header provided
    - 403: Invalid API key (doesn't exist, inactive, or expired)

    SECURITY:
    - Database API keys are ONLY for external teams
    - Cannot access /v1/admin/* endpoints (requires super admin key)
    - Team isolation enforced via team_id in sessions
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    db = get_db_session()
    try:
        api_key = APIKeyManager.validate_api_key(db, authorization.credentials)

        if not api_key:
            raise HTTPException(
                status_code=403,
                detail="Invalid API key"
            )

        logger.debug(f"Team access granted to API key: {api_key.key_prefix} (Team: {api_key.team.name})")
        return api_key

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating team API key: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error validating API key"
        )


def require_chat_access(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Union[str, APIKey]:
    """
    Require authentication for chat and commands endpoints

    AUTHENTICATION MODES:
    1. TELEGRAM MODE (Telegram bot service):
       - API key matches TELEGRAM_SERVICE_KEY environment variable
       - Returns "telegram" string marker
       - Used ONLY for the integrated Telegram bot service

    2. TEAM MODE (External teams):
       - API key validated against database
       - Returns APIKey object
       - Used for authenticated external teams

    SECURITY:
    - NO unauthenticated access allowed
    - Telegram bot must use TELEGRAM_SERVICE_KEY
    - External teams must use their team API keys
    - Super admins can distinguish Telegram traffic from external team traffic in logs

    USAGE:
    - Used by: /v1/chat and /v1/commands endpoints
    - Returns: "telegram" (Telegram bot) OR APIKey object (external teams)

    ERROR RESPONSES:
    - 401: No authorization header provided
    - 403: Invalid API key (neither Telegram service key nor team key)

    WHY THIS CHANGE:
    - Previous optional authentication allowed unauthenticated access
    - Unauthorized users could pretend to be Telegram bot traffic
    - Super admins couldn't track who was using the API
    - This fix ensures ALL traffic is authenticated and traceable
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide an API key in the Authorization header."
        )

    provided_key = authorization.credentials

    # Check if it's the Telegram bot service key
    if provided_key == settings.TELEGRAM_SERVICE_KEY:
        logger.info("[TELEGRAM] Bot service access granted")
        return "telegram"

    # Check if it's a valid team API key
    db = get_db_session()
    try:
        api_key = APIKeyManager.validate_api_key(db, provided_key)

        if not api_key:
            logger.warning(f"Invalid API key attempted: {provided_key[:12]}...")
            raise HTTPException(
                status_code=403,
                detail="Invalid API key. Please check your credentials."
            )

        logger.info(f"[TEAM] API access granted to: {api_key.key_prefix} (Team: {api_key.team.platform_name})")
        return api_key

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error validating API key"
        )