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
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid API key."
        )

    # Try database-based API key first
    db = get_db_session()
    try:
        api_key = APIKeyManager.validate_api_key(db, authorization.credentials)

        if api_key:
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
    except Exception as e:
        # If database is not available or API key validation fails, fall back to legacy auth
        pass

    # Fallback to legacy INTERNAL_API_KEY for backward compatibility
    # ⚠️ SECURITY WARNING: Legacy auth does NOT provide team isolation
    # TODO: Remove this fallback after all clients migrate to database API keys
    if authorization.credentials == settings.INTERNAL_API_KEY:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "⚠️ SECURITY: Legacy INTERNAL_API_KEY used - NO TEAM ISOLATION! "
            "Migrate to database-based API keys immediately."
        )
        # Return None to indicate legacy mode (no team isolation)
        return None

    raise HTTPException(
        status_code=403,
        detail="Invalid API key. Use database-based API keys for team isolation."
    )


def verify_internal_api_key(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> HTTPAuthorizationCredentials:
    """
    Verify internal API key (legacy support).
    For backward compatibility with existing code.

    ⚠️ WARNING: This function is deprecated. Use verify_api_key() instead for team isolation.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    # Check database API keys first
    db = get_db_session()
    try:
        api_key = APIKeyManager.validate_api_key(db, authorization.credentials)
        if api_key:
            return authorization
    except Exception:
        pass

    # Fallback to legacy key
    # ⚠️ SECURITY WARNING: Legacy auth does NOT provide team isolation
    if authorization.credentials != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key. Use database-based API keys for team isolation."
        )

    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        "⚠️ SECURITY: Legacy INTERNAL_API_KEY used via verify_internal_api_key() - "
        "NO TEAM ISOLATION! Migrate to verify_api_key() dependency."
    )

    return authorization


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


def verify_webhook_secret(webhook_secret: Optional[str]) -> bool:
    """Verify webhook secret"""
    if not settings.INTERNAL_WEBHOOK_SECRET:
        return True  # No secret configured

    return webhook_secret == settings.INTERNAL_WEBHOOK_SECRET