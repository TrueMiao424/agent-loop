import os

from django.apps import AppConfig


class WebhookConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.webhook"
    label = "webhook"

    def ready(self):
        if os.environ.get("RUN_MAIN") != "true":
            return
        from apps.webhook.service.feishu_ws_service import start_feishu_ws_daemon

        start_feishu_ws_daemon()
