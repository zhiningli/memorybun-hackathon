from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from .request_id import set_request_id

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        header_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID")
        request_id = set_request_id(header_id)
        
        response = await call_next(request)
        
        response.headers["X-Correlation-ID"] = request_id
        return response
