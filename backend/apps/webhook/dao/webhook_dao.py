import uuid

from apps.common.util.logging_util import log_method
from apps.webhook.entity.models import WebhookMessage


class WebhookDao:
    @staticmethod
    @log_method
    def list_all(limit=100):
        return WebhookMessage.objects.select_related("project", "task").order_by("-timestamp")[:limit]

    @staticmethod
    @log_method
    def list_queryset():
        return WebhookMessage.objects.select_related("project", "task").order_by("-timestamp")

    @staticmethod
    @log_method
    def create(**kwargs):
        if not kwargs.get("id"):
            kwargs["id"] = f"msg_{uuid.uuid4().hex[:12]}"
        return WebhookMessage.objects.create(**kwargs)
