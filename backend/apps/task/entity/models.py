from django.conf import settings as django_settings
from django.db import models

from apps.common.constant.task_constants import TaskStatus, TaskStep
from apps.project.entity.models import Project


class Task(models.Model):
    id = models.BigAutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    created_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tasks",
    )
    title = models.CharField(max_length=512)
    acceptance_criteria = models.TextField(blank=True, default="")
    current_step = models.CharField(max_length=64, default=TaskStep.REQUIREMENT_REFINEMENT)
    current_status = models.CharField(max_length=32, default=TaskStatus.INIT)
    affected_files = models.JSONField(default=dict)
    sub_tasks = models.JSONField(default=list)
    execution_logs = models.TextField(blank=True, default="")
    code_diffs = models.JSONField(default=list, blank=True)
    manual_edits = models.JSONField(default=list, blank=True)
    fail_reason = models.TextField(blank=True, default="")
    review_opinion = models.TextField(blank=True, default="")
    checkpoint = models.JSONField(default=dict, blank=True)  # interrupt/resume checkpoint
    idempotency_key = models.CharField(max_length=128, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tasks"
        indexes = [
            models.Index(fields=["project", "current_step", "current_status"]),
        ]


class TaskIdempotency(models.Model):
    """任务创建幂等记录。"""
    key = models.CharField(max_length=128, unique=True)
    task_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "task_idempotency"
