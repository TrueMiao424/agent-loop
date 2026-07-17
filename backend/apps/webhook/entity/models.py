from django.db import models

from apps.project.entity.models import Project
from apps.task.entity.models import Task


class WebhookMessage(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    webhook_url = models.CharField(max_length=512, blank=True, default="")
    title = models.CharField(max_length=512, blank=True, default="")
    message = models.TextField(blank=True, default="")
    status = models.CharField(max_length=32, default="sent")
    is_human = models.BooleanField(default=False)
    sender_name = models.CharField(max_length=128, blank=True, default="")
    session_id = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        db_table = "webhook_messages"
        indexes = [
            models.Index(fields=["project", "task"]),
        ]
