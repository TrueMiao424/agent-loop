import threading
import uuid

_trace_local = threading.local()


def new_trace_id(prefix: str = "bg") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def set_trace_id(trace_id: str):
    _trace_local.trace_id = trace_id


def get_trace_id() -> str:
    return getattr(_trace_local, "trace_id", "no-trace")


def run_with_trace(trace_id: str, fn, *args, **kwargs):
    """后台线程/调度器注入 TraceID。"""
    set_trace_id(trace_id)
    try:
        return fn(*args, **kwargs)
    finally:
        set_trace_id("no-trace")


class TraceLogFilter:
    def filter(self, record):
        record.trace_id = get_trace_id()
        return True
