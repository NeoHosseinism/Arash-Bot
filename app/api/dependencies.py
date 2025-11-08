"""
API dependencies for authentication and validation

TWO-TIER ACCESS CONTROL SYSTEM:

1. SUPER ADMINS (Internal Team):
   - Access Level: ADMIN
   - Can access: ALL /api/v1/admin/* endpoints
   - Purpose: Service owners who manage teams, API keys, and monitor usage
   - These are YOUR internal team members

2. TEAM API KEYS (External Clients):
   - Access Level: TEAM
   - Can access: ONLY /api/v1/chat endpoint
   - Purpose: External teams using your chatbot service
   - These are your CLIENTS

SECURITY:
- External teams (TEAM level) cannot access admin endpoints
- External teams don't know about access levels or other teams
- Complete isolation between teams via session tagging
"""
from typing import Optional
import logging
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.models.database import APIKey, AccessLevel, get_db_session
from app.services.api_key_manager import APIKeyManager

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


def require_admin_access(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> APIKey:
    """
    Require ADMIN access - ONLY for super admins (internal team)

    This dependency protects ALL /api/v1/admin/* endpoints.
    Only API keys with access_level=ADMIN can access these endpoints.

    USAGE:
    - Used by: All admin endpoints (/api/v1/admin/*)
    - Required access level: ADMIN (super admins only)
    - Returns: Validated APIKey object

    ENDPOINTS PROTECTED:
    - Team management (create, list, update, delete teams)
    - API key management (create, list, revoke API keys)
    - Usage statistics (view all team usage)
    - Platform information (Telegram + Internal config)
    - System administration (clear sessions, etc.)

    ERROR RESPONSES:
    - 401: No authorization header provided
    - 403: Invalid API key OR valid key but not ADMIN level
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

        # Check if admin (super admin access required)
        if AccessLevel(api_key.access_level) != AccessLevel.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Admin access required. This endpoint is only accessible to super admins (internal team)."
            )

        logger.info(f"Admin access granted to API key: {api_key.key_prefix} (Team: {api_key.team.name})")
        return api_key

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating admin API key: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error validating API key"
        )


def require_team_access(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> APIKey:
    """
    Require valid team API key - for external teams (clients) using the chatbot

    This dependency protects the /api/v1/chat endpoint.
    Any valid API key (TEAM or ADMIN level) can access this endpoint.

    USAGE:
    - Used by: /api/v1/chat endpoint
    - Required access level: Any valid API key (TEAM or ADMIN)
    - Returns: Validated APIKey object (includes team_id for isolation)

    SECURITY & TRANSPARENCY:
    - Accepts any valid API key (both TEAM and ADMIN levels)
    - External teams (TEAM level) don't know about access levels
    - External teams think they're using a simple chatbot API
    - Complete team isolation via session tagging (transparent to clients)
    - No exposure of internal architecture or other teams

    WHAT EXTERNAL TEAMS SEE:
    - Input: Message content
    - Output: Bot response

    WHAT THEY DON'T SEE:
    - Access levels
    - Other teams
    - Session management internals
    - Admin functionality

    ERROR RESPONSES:
    - 401: No authorization header provided
    - 403: Invalid API key (doesn't exist, inactive, or expired)
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