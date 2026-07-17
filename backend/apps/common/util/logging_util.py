import logging
import uuid
from functools import wraps

from apps.common.middleware.trace import get_trace_id

logger = logging.getLogger("apps")


def log_method(func):
    """Decorator: DEBUG entry/exit for service/dao/client methods."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        trace_id = get_trace_id()
        name = f"{func.__module__}.{func.__qualname__}"
        safe_kwargs = {k: v for k, v in kwargs.items() if k not in ("password", "api_key", "token")}
        logger.debug("ENTER %s trace=%s args=%s kwargs=%s", name, trace_id, len(args), safe_kwargs)
        try:
            result = func(*args, **kwargs)
            logger.debug("EXIT %s trace=%s success", name, trace_id)
            return result
        except Exception:
            logger.exception("ERROR %s trace=%s", name, trace_id)
            raise

    return wrapper


def log_external_call(service_name: str, url: str, request_body=None, response_body=None, duration_ms=0, error=None):
    """Log full external request/response."""
    ext_logger = logging.getLogger("external")
    ext_logger.info(
        "EXTERNAL_CALL service=%s url=%s duration_ms=%s request=%s response=%s error=%s trace=%s",
        service_name,
        url,
        duration_ms,
        _mask(request_body),
        _mask(response_body),
        error,
        get_trace_id(),
    )


def _mask(data):
    if data is None:
        return None
    text = str(data)
    for secret in ("password", "api_key", "token", "secret"):
        if secret in text.lower():
            return "[REDACTED]"
    return text[:2000]
