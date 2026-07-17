import uuid

from django.db import models

from apps.common.constant.task_constants import SessionStatus
from apps.task.entity.models import Task


class AgentSession(models.Model):
    session_id = models.CharField(max_length=64, primary_key=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="sessions")
    pid = models.CharField(max_length=32, blank=True, default="")
    project_name = models.CharField(max_length=255, blank=True, default="")
    project_path = models.CharField(max_length=512, blank=True, default="")
    command_line = models.CharField(max_length=512, blank=True, default="")
    inputs = models.TextField(blank=True, default="")
    logs = models.TextField(blank=True, default="")
    status = models.CharField(max_length=32, default=SessionStatus.PROCESSING)
    last_reported_log = models.TextField(blank=True, default="")
    last_reported_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agent_sessions"
        indexes = [models.Index(fields=["status"])]
