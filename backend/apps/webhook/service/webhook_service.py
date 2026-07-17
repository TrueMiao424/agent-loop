from apps.common.constant.task_constants import TaskStatus
from apps.common.util.logging_util import log_method
from apps.project.dao.project_dao import ProjectDao
from apps.webhook.client.feishu_client import FeishuClient
from apps.webhook.dao.webhook_dao import WebhookDao
from apps.webhook.service.feishu_review_service import (
    USAGE_HELP,
    parse_create_body,
    pending_review_hint,
    try_handle_review_command,
)
from apps.webhook.util.feishu_message_util import extract_message_text
from apps.webhook.util.feishu_task_formatter import (
    format_task_alert_message,
    format_task_created_message,
    format_task_review_message,
)


def _duplicate_create_reply(task) -> dict:
    return {
        "ok": True,
        "taskId": task.id,
        "reply": (
            f"不可重复创建\n"
            f"项目中已有相同需求任务 #{task.id}（{task.title}）\n"
            f"状态：{task.current_step}/{task.current_status}\n"
            f"请使用任务号操作，例如：#{task.id} 同意动工 或 #{task.id} 续做"
        ),
        "action": "create_duplicate",
    }


class WebhookService:
    @staticmethod
    def _resolve_chat_id(task) -> str:
        chat_id = getattr(task.project, "chat_group_id", "") or ""
        if chat_id:
            return chat_id
        from apps.settings_app.dao.settings_dao import get_feishu_chat_group_id

        return get_feishu_chat_group_id()

    @staticmethod
    @log_method
    def list_messages():
        return WebhookDao.list_all()

    @staticmethod
    @log_method
    def list_messages_page(page: int, page_size: int):
        from apps.common.util.pagination import paginate_queryset

        return paginate_queryset(WebhookDao.list_queryset(), page, page_size)

    @staticmethod
    @log_method
    def notify_task_event(task, title: str, phase: str):
        chat_id = WebhookService._resolve_chat_id(task)
        if phase in ("Human_Review_1", "Human_Review_2"):
            message = format_task_review_message(task, phase)
        elif phase in ("Interrupted", "Failed"):
            message = format_task_alert_message(task, phase, title=title)
        else:
            message = f"任务 #{task.id} [{task.title}]\n{title}"

        WebhookDao.create(
            project=task.project,
            task=task,
            webhook_url=chat_id,
            title=title,
            message=message[:2000],
            status="sent",
            is_human=False,
            sender_name="System",
        )
        if chat_id:
            FeishuClient.send_text(chat_id, message)

    @staticmethod
    @log_method
    def inject_message(data: dict):
        return WebhookDao.create(
            project_id=data.get("projectId"),
            task_id=data.get("taskId"),
            webhook_url=data.get("webhookUrl", ""),
            title=data.get("title", "Manual"),
            message=data.get("message", ""),
            status="sent",
            is_human=data.get("isHuman", True),
            sender_name=data.get("senderName", "Web User"),
            session_id=data.get("sessionId", ""),
        )

    @staticmethod
    def _extract_message_text(event: dict) -> str:
        return extract_message_text(event)

    @staticmethod
    def _resolve_project(chat_id: str):
        project = ProjectDao.get_by_chat_group_id(chat_id)
        if project:
            return project
        from apps.settings_app.dao.settings_dao import get_feishu_chat_group_id, get_feishu_default_project_id

        configured_chat = get_feishu_chat_group_id()
        default_project_id = get_feishu_default_project_id()
        if configured_chat and chat_id == configured_chat and default_project_id:
            return ProjectDao.get_by_id(default_project_id)
        return None

    @staticmethod
    @log_method
    def handle_feishu_event(payload: dict):
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}

        event = payload.get("event", payload if payload.get("message") else {})
        message = event.get("message", {})
        chat_id = message.get("chat_id", "")
        text = WebhookService._extract_message_text(event)

        project = WebhookService._resolve_project(chat_id)
        if not project:
            WebhookDao.create(
                webhook_url=chat_id,
                title="未匹配项目",
                message=text,
                status="failed",
                is_human=True,
                sender_name=event.get("sender", {}).get("sender_id", {}).get("open_id", "unknown"),
            )
            return {"ok": True, "reply": "未找到匹配项目，请在配置管理 → 飞书集成中填写 chat_id 并选择关联项目"}

        command_result = try_handle_review_command(project.id, text)
        if command_result is not None:
            action = command_result.get("action", "command")
            WebhookDao.create(
                project=project,
                task_id=command_result.get("taskId"),
                webhook_url=chat_id,
                title=f"飞书操作: {action}",
                message=text,
                is_human=True,
                sender_name="Feishu User",
            )
            return command_result

        create_body = parse_create_body(text)
        if create_body:
            import hashlib
            import re

            from apps.auth_app.dao.user_dao import UserDao
            from apps.common.exception.biz_exception import BizException
            from apps.task.dao.task_dao import TaskDao
            from apps.task.service.task_service import TaskService

            admin = UserDao.get_by_username("admin")
            first_line = (create_body.splitlines()[0] if create_body else "").strip()
            title = (first_line or create_body[:80] or "飞书新需求")[:80]
            normalized = re.sub(r"\s+", " ", create_body.strip())
            idem_key = f"feishu:{project.id}:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:40]}"

            existing_idem = TaskDao.get_idempotency(idem_key)
            if existing_idem:
                existed = TaskDao.get_by_id(existing_idem.task_id)
                if existed and existed.current_status != TaskStatus.FINISHED:
                    return _duplicate_create_reply(existed)

            duplicate = TaskDao.find_same_requirement(project.id, create_body)
            if duplicate:
                return _duplicate_create_reply(duplicate)

            try:
                task = TaskService.create_task(
                    project.id,
                    title,
                    create_body,
                    idempotency_key=idem_key,
                    created_by=admin,
                )
            except BizException as exc:
                WebhookDao.create(
                    project=project,
                    webhook_url=chat_id,
                    title="飞书创建任务失败",
                    message=create_body,
                    status="failed",
                    is_human=True,
                    sender_name="Feishu PM",
                )
                return {
                    "ok": True,
                    "reply": f"指令有误\n创建任务失败：{exc}\n\n{USAGE_HELP}",
                    "action": "create_failed",
                }
            except Exception as exc:
                WebhookDao.create(
                    project=project,
                    webhook_url=chat_id,
                    title="飞书创建任务异常",
                    message=create_body,
                    status="failed",
                    is_human=True,
                    sender_name="Feishu PM",
                )
                return {
                    "ok": True,
                    "reply": f"指令有误\n创建任务异常：{exc}\n\n{USAGE_HELP}",
                    "action": "create_failed",
                }

            WebhookDao.create(
                project=project,
                task=task,
                webhook_url=chat_id,
                title="飞书创建任务",
                message=create_body,
                is_human=True,
                sender_name="Feishu PM",
            )
            TaskService._try_dispatch(task.id)
            return {
                "ok": True,
                "taskId": task.id,
                "reply": format_task_created_message(task.id),
            }

        hint = pending_review_hint(project.id)
        WebhookDao.create(
            project=project,
            webhook_url=chat_id,
            title="飞书消息",
            message=text,
            is_human=True,
            sender_name="Feishu User",
        )
        preview = (text or "").strip().replace("\n", "\\n")
        if len(preview) > 80:
            preview = preview[:79] + "…"
        if hint:
            return {
                "ok": True,
                "reply": f"指令有误\n你发送：{preview or '(空)'}\n未识别为有效指令。\n\n{hint}\n\n{USAGE_HELP}",
                "action": "command_unrecognized",
            }
        return {
            "ok": True,
            "reply": f"指令有误\n你发送：{preview or '(空)'}\n未识别为有效指令。\n\n{USAGE_HELP}",
            "action": "command_unrecognized",
        }
