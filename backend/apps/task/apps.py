import os

from django.apps import AppConfig


class TaskConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.task"
    label = "task"

    def ready(self):
        # runserver 自动重载会启动两个进程，只在子进程启动调度器
        if os.environ.get("RUN_MAIN") != "true":
            return
        from apps.task.service.scheduler_service import start_scheduler_daemon

        start_scheduler_daemon()
