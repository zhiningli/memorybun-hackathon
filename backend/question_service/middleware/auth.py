"""
Authentication middleware for Admin APIs.
"""
from fastapi import Header, HTTPException, status
from typing import Optional
from config import settings

async def verify_admin_key(x_admin_key: Optional[str] = Header(None)) -> str:
    """
    Verify X-Admin-Key header against configured ADMIN_API_KEY.
    Raises 401 if invalid.
    """
    # Use .get_secret_value() to extract the actual key from SecretStr for comparison
    if x_admin_key != settings.admin_api_key.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Admin API Key"
        )
    return x_admin_key
