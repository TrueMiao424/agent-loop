import random
import uuid

from apps.common.constant.task_constants import SessionStatus
from apps.common.util.logging_util import log_method
from apps.session.entity.models import AgentSession
from apps.task.client.llm_client import ClaudeCodeClient


class SessionDao:
    @staticmethod
    @log_method
    def list_all():
        return AgentSession.objects.select_related("task", "task__project").order_by("-created_at")

    @staticmethod
    @log_method
    def count_processing():
        return AgentSession.objects.filter(status=SessionStatus.PROCESSING).count()

    @staticmethod
    @log_method
    def create_for_task(task):
        sid = f"SESS-{task.id}-{uuid.uuid4().hex[:6]}"
        return AgentSession.objects.create(
            session_id=sid,
            task=task,
            pid=str(random.randint(10000, 99999)),
            project_name=task.project.project_name,
            project_path=task.project.project_path,
            command_line=ClaudeCodeClient.build_command(task.created_by_id),
            status=SessionStatus.PROCESSING,
        )

    @staticmethod
    @log_method
    def finish(session_id: str):
        AgentSession.objects.filter(session_id=session_id).update(status=SessionStatus.FINISHED)

    @staticmethod
    @log_method
    def fail(session_id: str, reason: str):
        s = AgentSession.objects.filter(session_id=session_id).first()
        if s:
            s.status = SessionStatus.FAILED
            s.logs = (s.logs or "") + f"\nERROR: {reason}"
            s.save()

    @staticmethod
    @log_method
    def interrupt_by_task(task_id: int):
        AgentSession.objects.filter(task_id=task_id, status=SessionStatus.PROCESSING).update(
            status=SessionStatus.INTERRUPTED
        )

    @staticmethod
    @log_method
    def reset_all():
        AgentSession.objects.all().delete()
