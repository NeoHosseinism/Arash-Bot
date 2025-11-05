"""
API dependencies for authentication and validation

SECURITY MODEL:
- Admin Access: Only for service owner team (access_level = ADMIN)
- Team Access: For external teams using the API (any valid API key)
- External teams should NOT know about access levels or other teams
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
    Require ADMIN access - only for service owner team

    SECURITY:
    - Validates API key from database
    - Checks access_level == ADMIN
    - Returns validated API key object
    - Used for: team management, API key creation, webhook configuration, etc.
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

        # Check if admin
        if AccessLevel(api_key.access_level) != AccessLevel.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Admin access required"
            )

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
    Require valid team API key - for external teams using the API

    SECURITY:
    - Validates any valid API key from database
    - Does NOT expose access levels or team information
    - External teams think they're using a simple chatbot API
    - Returns validated API key object (contains team_id for isolation)
    - Used for: /chat endpoint (message processing)
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

        return api_key

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating team API key: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error validating API key"
        )