"""
API dependencies for authentication and validation
"""
from typing import Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

# Security scheme
security = HTTPBearer(auto_error=False)


def get_auth(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[HTTPAuthorizationCredentials]:
    """Get authorization credentials (optional)"""
    return authorization


def verify_internal_api_key(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> HTTPAuthorizationCredentials:
    """Verify internal API key (required)"""
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    if authorization.credentials != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return authorization


def verify_webhook_secret(webhook_secret: Optional[str]) -> bool:
    """Verify webhook secret"""
    if not settings.INTERNAL_WEBHOOK_SECRET:
        return True  # No secret configured
    
    return webhook_secret == settings.INTERNAL_WEBHOOK_SECRET