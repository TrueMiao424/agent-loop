from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

from django.conf import settings

from apps.common.middleware.trace import new_trace_id, run_with_trace
from apps.common.util.db_util import with_db_cleanup

_pool: Optional[ThreadPoolExecutor] = None


def get_agent_executor() -> ThreadPoolExecutor:
    """统一 Agent 线程池，禁止裸 Thread。"""
    global _pool
    if _pool is None:
        workers = int(getattr(settings, "AGENT_EXECUTOR_WORKERS", 4))
        _pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="agent-worker")
    return _pool


def submit_agent_task(fn: Callable, *args, trace_prefix: str = "agent", **kwargs):
    trace_id = new_trace_id(trace_prefix)

    @with_db_cleanup
    def wrapped():
        run_with_trace(trace_id, fn, *args, **kwargs)

    return get_agent_executor().submit(wrapped)
