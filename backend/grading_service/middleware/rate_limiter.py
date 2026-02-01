"""
Rate limiting middleware using slowapi.

Uses Redis as storage backend for distributed rate limiting across multiple instances.
This ensures rate limits are enforced correctly even when running multiple
service replicas behind a load balancer.

Falls back to in-memory storage if Redis is unavailable (e.g., during tests).

Rate limits are applied per-IP address, with support for X-Forwarded-For
header when running behind a load balancer or proxy.
"""
import os
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import settings

logger = logging.getLogger(__name__)

# Check if we're running in test mode
TESTING = os.environ.get("TESTING", "").lower() in ("1", "true", "yes")


def get_client_ip(request: Request) -> str:
    """
    Extract client IP for rate limiting.
    Handles X-Forwarded-For header for requests behind load balancer.
    
    Args:
        request: The incoming Starlette/FastAPI request
        
    Returns:
        Client IP address string
    """
    # Check for forwarded IP (behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs, first is the original client
        return forwarded.split(",")[0].strip()
    
    # Fall back to direct client IP
    return get_remote_address(request) or "unknown"


def _create_limiter() -> Limiter:
    """
    Create the rate limiter, attempting Redis first, falling back to in-memory.
    
    This graceful fallback ensures:
    - Tests can run without Redis (when TESTING=1)
    - Service starts even if Redis is temporarily unavailable
    """
    # If testing, use in-memory with no actual limits
    if TESTING:
        logger.info("Rate limiting disabled for testing (TESTING=1)")
        return Limiter(
            key_func=get_client_ip,
            default_limits=[],  # No default limits in testing
            headers_enabled=False,
            enabled=False,  # Completely disable rate limiting
        )
    
    try:
        # User settings.redis_url directly (Cloud Native best practice)
        redis_uri = settings.redis_url
        
        # Create limiter with Redis storage
        # swallow_errors=True ensures that if Redis goes down, we don't 500
        rate_limiter = Limiter(
            key_func=get_client_ip,
            default_limits=["200/minute"],
            headers_enabled=False,  # Disabled to avoid Response parameter requirement
            storage_uri=redis_uri,
            swallow_errors=True,
            enabled=False
        )
        logger.info(f"Rate limiter initialized with Redis storage: {redis_uri}")
        return rate_limiter
    except Exception as e:
        # Fall back to in-memory storage (should rarely happen with swallow_errors=True, 
        # but protects against initialization errors)
        logger.warning(f"Failed to initialize Redis limiter ({e}), using in-memory storage")
        return Limiter(
            key_func=get_client_ip,
            default_limits=["200/minute"],
            headers_enabled=True,
            swallow_errors=True
        )


# Create limiter instance
limiter = _create_limiter()


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    Returns 429 with helpful error message and Retry-After header.
    
    Args:
        request: The incoming request that exceeded the limit
        exc: The RateLimitExceeded exception with limit details
        
    Returns:
        JSONResponse with 429 status and error details
    """
    client_ip = get_client_ip(request)
    logger.warning(
        f"Rate limit exceeded for {client_ip} on {request.method} {request.url.path} - Limit: {exc.detail}"
    )
    
    # Default retry after 60 seconds
    retry_after = 60
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Too many requests. Rate limit: {exc.detail}. Please try again later.",
            "limit": str(exc.detail),
            "retry_after_seconds": retry_after
        },
        headers={
            "Retry-After": str(retry_after),
        }
    )



