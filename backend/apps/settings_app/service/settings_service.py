from django.conf import settings as django_settings

from apps.common.util.logging_util import log_method
from apps.settings_app.dao.settings_dao import SettingsDao, get_agent_llm_config, get_feishu_chat_group_id, get_feishu_default_project_id, get_feishu_ws_enabled, get_feishu_ws_require_mention, get_user_llm_setting, save_user_llm_setting


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 12:
        return "*" * len(value)
    return f"{value[:8]}...{value[-4:]}"


class SettingsService:
    @staticmethod
    @log_method
    def get_settings(user):
        rows = SettingsDao.get_all()
        setting = get_user_llm_setting(user.id)
        llm = get_agent_llm_config(user.id)
        api_key = llm["api_key"]
        source = "user" if api_key else "none"
        if api_key and user.username == "admin" and getattr(django_settings, "ANTHROPIC_AUTH_TOKEN", ""):
            if api_key == django_settings.ANTHROPIC_AUTH_TOKEN:
                source = "env_migrated"
        default_project_id = get_feishu_default_project_id()
        chat_group_id = get_feishu_chat_group_id()
        if not chat_group_id and default_project_id:
            from apps.project.dao.project_dao import ProjectDao

            project = ProjectDao.get_by_id(default_project_id)
            if project and project.chat_group_id:
                chat_group_id = project.chat_group_id
        return {
            "AGENT_LLM": {
                "apiKey": "",
                "apiKeyMasked": _mask_secret(api_key),
                "hasApiKey": bool(api_key),
                "baseUrl": llm["base_url"],
                "model": llm["model"],
                "source": source,
            },
            "FEISHU": {
                "appId": rows.get("feishu_app_id", ""),
                "appSecret": "",
                "appSecretMasked": _mask_secret(rows.get("feishu_app_secret", "")),
                "hasAppSecret": bool(rows.get("feishu_app_secret")),
                "wsEnabled": get_feishu_ws_enabled(),
                "requireMention": get_feishu_ws_require_mention(),
                "chatGroupId": chat_group_id,
                "defaultProjectId": default_project_id,
            },
        }

    @staticmethod
    @log_method
    def save_settings(user, data: dict):
        saved_keys = []

        agent = data.get("AGENT_LLM") or {}
        if isinstance(agent, dict):
            save_user_llm_setting(
                user.id,
                api_key=agent.get("apiKey") or None,
                base_url=agent.get("baseUrl") if "baseUrl" in agent else None,
                model=agent.get("model") if "model" in agent else None,
            )
            if agent.get("apiKey"):
                saved_keys.append("user_llm.api_key")
            if "baseUrl" in agent:
                saved_keys.append("user_llm.base_url")
            if "model" in agent:
                saved_keys.append("user_llm.model")

        feishu = data.get("FEISHU") or {}
        ws_changed = False
        if isinstance(feishu, dict):
            feishu_db = {}
            if "appId" in feishu:
                feishu_db["feishu_app_id"] = feishu["appId"]
            if feishu.get("appSecret"):
                feishu_db["feishu_app_secret"] = feishu["appSecret"]
            if "wsEnabled" in feishu:
                feishu_db["feishu_ws_enabled"] = "true" if feishu["wsEnabled"] else "false"
                ws_changed = True
            if "requireMention" in feishu:
                feishu_db["feishu_ws_require_mention"] = "true" if feishu["requireMention"] else "false"
                ws_changed = True
            if "chatGroupId" in feishu:
                feishu_db["feishu_chat_group_id"] = (feishu.get("chatGroupId") or "").strip()
            if "defaultProjectId" in feishu:
                pid = feishu.get("defaultProjectId")
                feishu_db["feishu_default_project_id"] = str(pid) if pid else ""
            if feishu_db:
                SettingsDao.set_many(feishu_db)
                saved_keys.extend(feishu_db.keys())

            chat_id = (feishu.get("chatGroupId") or "").strip() if "chatGroupId" in feishu else None
            project_id = feishu.get("defaultProjectId") if "defaultProjectId" in feishu else None
            if chat_id is not None and project_id:
                from apps.project.dao.project_dao import ProjectDao

                project = ProjectDao.get_by_id(int(project_id))
                if project:
                    ProjectDao.update(project, chat_group_id=chat_id)
                    saved_keys.append("project.chat_group_id")

        if ws_changed:
            from apps.webhook.service.feishu_ws_service import apply_feishu_ws_settings

            apply_feishu_ws_settings()
        elif isinstance(feishu, dict) and (
            "appId" in feishu or feishu.get("appSecret") or "requireMention" in feishu
        ):
            from apps.webhook.service.feishu_ws_service import restart_feishu_ws

            restart_feishu_ws()

        return {"saved_keys": saved_keys}

    @staticmethod
    @log_method
    def test_agent_llm(user):
        from apps.task.client.llm_client import AnthropicClient

        if not AnthropicClient.is_configured(user.id):
            raise ValueError("未配置 API Key，请先保存")
        cfg = AnthropicClient._config(user.id)
        reply = AnthropicClient.test_connection(user.id)
        return {
            "ok": True,
            "model": cfg["model"],
            "baseUrl": cfg["base_url"],
            "reply": reply[:200],
        }
