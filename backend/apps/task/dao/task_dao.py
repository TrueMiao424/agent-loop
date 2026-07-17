from typing import Optional

from django.db.models import Q

from apps.common.constant.task_constants import TaskStatus, TaskStep
from apps.common.util.logging_util import log_method
from apps.task.entity.models import Task, TaskIdempotency


class TaskDao:
    @staticmethod
    @log_method
    def list_by_project(project_id: int):
        return Task.objects.filter(project_id=project_id).select_related("created_by").order_by("-updated_at")

    @staticmethod
    @log_method
    def get_by_id(task_id: int):
        return Task.objects.select_related("project", "created_by").filter(id=task_id).first()

    @staticmethod
    @log_method
    def create(**kwargs):
        return Task.objects.create(**kwargs)

    @staticmethod
    @log_method
    def save(task: Task):
        task.save()
        return task

    @staticmethod
    @log_method
    def delete(task: Task):
        task.delete()

    @staticmethod
    @log_method
    def count_processing_sessions():
        from apps.session.entity.models import AgentSession

        return AgentSession.objects.filter(status=TaskStatus.PROCESSING).count()

    @staticmethod
    @log_method
    def find_init_tasks():
        return Task.objects.filter(current_status=TaskStatus.INIT).order_by("created_at")

    @staticmethod
    @log_method
    def get_idempotency(key: str):
        return TaskIdempotency.objects.filter(key=key).first()

    @staticmethod
    @log_method
    def save_idempotency(key: str, task_id: int):
        TaskIdempotency.objects.get_or_create(key=key, defaults={"task_id": task_id})

    @staticmethod
    @log_method
    def find_interrupted():
        return Task.objects.filter(
            Q(current_status=TaskStatus.INTERRUPTED) | Q(current_status=TaskStatus.FAILED)
        )

    @staticmethod
    @log_method
    def find_pending_review(project_id: int, task_id: Optional[int] = None):
        qs = (
            Task.objects.filter(
                project_id=project_id,
                current_status=TaskStatus.INIT,
                current_step__in=[TaskStep.HUMAN_REVIEW_1, TaskStep.HUMAN_REVIEW_2],
            )
            .select_related("project")
            .order_by("-updated_at")
        )
        if task_id:
            return qs.filter(id=task_id).first()
        return qs.first()

    @staticmethod
    @log_method
    def find_resumable(project_id: int, task_id: Optional[int] = None):
        qs = (
            Task.objects.filter(
                project_id=project_id,
                current_status__in=[TaskStatus.INTERRUPTED, TaskStatus.FAILED],
            )
            .select_related("project")
            .order_by("-updated_at")
        )
        if task_id:
            return qs.filter(id=task_id).first()
        return qs.first()

    @staticmethod
    @log_method
    def find_same_requirement(project_id: int, acceptance_criteria: str):
        """同项目下是否已有相同验收内容的未完成任务。"""
        import re

        normalized = re.sub(r"\s+", " ", (acceptance_criteria or "").strip())
        if not normalized:
            return None
        qs = (
            Task.objects.filter(project_id=project_id)
            .exclude(current_status__in=[TaskStatus.FINISHED, TaskStatus.CANCELLED])
            .order_by("-id")
        )
        for task in qs.iterator():
            existing = re.sub(r"\s+", " ", (task.acceptance_criteria or "").strip())
            if existing == normalized:
                return task
        return None