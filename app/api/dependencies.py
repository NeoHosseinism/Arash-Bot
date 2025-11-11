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
            detail="احراز هویت مورد نیاز است"
        )

    # Check if super admin keys are configured
    super_admin_keys = settings.super_admin_keys_set
    if not super_admin_keys:
        logger.error("SUPER_ADMIN_API_KEYS not configured - admin endpoints unavailable")
        raise HTTPException(
            status_code=401,
            detail="احراز هویت مدیر کل پیکربندی نشده است"
        )

    # Validate against environment-based super admin keys
    provided_key = authorization.credentials
    if provided_key not in super_admin_keys:
        logger.warning(f"Invalid super admin API key attempted: {provided_key[:12]}...")
        raise HTTPException(
            status_code=403,
            detail="کلید API مدیر کل نامعتبر است"
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
            detail="احراز هویت مورد نیاز است"
        )

    db = get_db_session()
    try:
        api_key = APIKeyManager.validate_api_key(db, authorization.credentials)

        if not api_key:
            raise HTTPException(
                status_code=403,
                detail="کلید API نامعتبر است"
            )

        logger.debug(f"Team access granted to API key: {api_key.key_prefix} (Team: {api_key.team.name})")
        return api_key

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating team API key: {e}")
        raise HTTPException(
            status_code=500,
            detail="خطا در اعتبارسنجی کلید API"
        )


def optional_team_access(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[APIKey]:
    """
    Optional TEAM API key authentication - supports both public and private access

    MODES:
    1. PUBLIC MODE (No auth header):
       - Returns None
       - Used for public Telegram bot
       - No team isolation (platform:chat_id sessions)

    2. PRIVATE MODE (Auth header provided):
       - Returns APIKey object
       - Used for authenticated teams
       - Team isolation enforced (platform:team_id:chat_id sessions)

    AUTHENTICATION:
    - If auth header provided: Validates against database
    - If no auth header: Returns None (public access allowed)
    - If invalid auth header: Raises 403 error

    USAGE:
    - Used by: Modular /v1/chat endpoint
    - Returns: APIKey object (private) OR None (public)

    ERROR RESPONSES:
    - 403: Invalid API key (only if auth header provided but invalid)
    - No 401 error (public access allowed)

    SECURITY:
    - Public access only for Telegram bot (no team isolation)
    - Private access enforces team isolation via team_id
    - Invalid keys are rejected (no fallback to public)
    """
    if not authorization:
        # Public access (Telegram bot)
        logger.debug("Public access (no authentication)")
        return None

    # Private access - validate API key
    db = get_db_session()
    try:
        api_key = APIKeyManager.validate_api_key(db, authorization.credentials)

        if not api_key:
            raise HTTPException(
                status_code=403,
                detail="کلید API نامعتبر است"
            )

        logger.debug(f"Team access granted to API key: {api_key.key_prefix} (Team: {api_key.team.name})")
        return api_key

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating team API key: {e}")
        raise HTTPException(
            status_code=500,
            detail="خطا در اعتبارسنجی کلید API"
        )