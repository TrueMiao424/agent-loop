import logging
import threading
import time

from django.conf import settings

from apps.common.constant.task_constants import TaskStep
from apps.common.middleware.trace import new_trace_id, run_with_trace
from apps.common.util.db_util import with_db_cleanup
from apps.common.util.logging_util import log_method
from apps.session.dao.session_dao import SessionDao
from apps.task.dao.task_dao import TaskDao
from apps.task.service.workflow_service import AgentOrchestrator

_scheduler_started = False
_scheduler_lock = threading.Lock()
_scheduler_logger = logging.getLogger("apps.scheduler")


def start_scheduler_daemon():
    global _scheduler_started
    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_started = True

    def loop():
        time.sleep(3)
        while True:
            trace_id = new_trace_id("scheduler")
            try:
                run_with_trace(trace_id, _scheduler_tick_safe)
            except Exception as exc:
                _scheduler_logger.warning("scheduler tick error: %s trace=%s", exc, trace_id)
            time.sleep(3)

    threading.Thread(target=loop, daemon=True, name="agent-scheduler").start()
    _scheduler_logger.info("agent scheduler started")


@with_db_cleanup
def _scheduler_tick_safe():
    _scheduler_tick()


def _scheduler_tick():
    active = SessionDao.count_processing()
    max_slots = settings.AGENT_MAX_CONCURRENT_SESSIONS
    if active >= max_slots:
        return
    dispatched = 0
    for task in TaskDao.find_init_tasks()[: max_slots - active]:
        if task.current_step in (
            TaskStep.REQUIREMENT_REFINEMENT,
            TaskStep.AUTO_DEVELOPMENT,
            TaskStep.COMMIT_PUSH,
        ):
            result = AgentOrchestrator.dispatch(task.id)
            if result:
                dispatched += 1
                _scheduler_logger.info(
                    "dispatched task_id=%s step=%s trace=%s",
                    task.id,
                    task.current_step,
                    get_trace_safe(),
                )
    if dispatched:
        _scheduler_logger.debug("scheduler tick dispatched=%s", dispatched)


def get_trace_safe():
    from apps.common.middleware.trace import get_trace_id

    return get_trace_id()


class SchedulerService:
    @staticmethod
    @log_method
    def tick():
        start_scheduler_daemon()
