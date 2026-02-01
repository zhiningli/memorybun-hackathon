import contextvars
from uuid import uuid4

CORRELATION_ID_CTX_KEY = "correlation_id"
_correlation_id_ctx_var: contextvars.ContextVar[str] = contextvars.ContextVar(CORRELATION_ID_CTX_KEY, default=None)

def get_request_id() -> str:
    return _correlation_id_ctx_var.get() or "unknown"

def set_request_id(request_id: str = None) -> str:
    if not request_id:
        request_id = str(uuid4())
    _correlation_id_ctx_var.set(request_id)
    return request_id
