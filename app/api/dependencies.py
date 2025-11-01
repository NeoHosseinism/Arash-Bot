"""
API dependencies for authentication and validation
"""
from typing import Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.models.database import APIKey, AccessLevel, get_db_session
from app.services.api_key_manager import APIKeyManager

# Security scheme
security = HTTPBearer(auto_error=False)


def get_auth(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[HTTPAuthorizationCredentials]:
    """Get authorization credentials (optional)"""
    return authorization


def verify_api_key(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    min_access_level: AccessLevel = AccessLevel.USER,
) -> APIKey:
    """
    Verify API key and check access level.
    Returns the validated API key object.

    SECURITY: Only database-based API keys are supported for team isolation.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid API key."
        )

    # Validate database-based API key
    db = get_db_session()
    try:
        api_key = APIKeyManager.validate_api_key(db, authorization.credentials)

        if not api_key:
            raise HTTPException(
                status_code=403,
                detail="Invalid API key"
            )

        # Check access level
        key_level = AccessLevel(api_key.access_level)
        level_hierarchy = {
            AccessLevel.USER: 1,
            AccessLevel.TEAM_LEAD: 2,
            AccessLevel.ADMIN: 3,
        }

        if level_hierarchy[key_level] < level_hierarchy[min_access_level]:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {min_access_level.value}, "
                f"Your level: {key_level.value}"
            )

        return api_key

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error validating API key: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error validating API key. Please try again."
        )


def require_admin_access(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> APIKey:
    """
    Require admin-level access.
    Returns the validated API key object.
    """
    return verify_api_key(authorization, AccessLevel.ADMIN)


def require_team_lead_access(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> APIKey:
    """
    Require team-lead or admin-level access.
    Returns the validated API key object.
    """
    return verify_api_key(authorization, AccessLevel.TEAM_LEAD)