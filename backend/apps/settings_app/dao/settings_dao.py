import json
import os
from typing import Optional

from django.conf import settings

from apps.common.util.logging_util import log_method
from apps.settings_app.entity.models import SystemSetting, UserLlmSetting

DEFAULT_BASE_URL = "https://api.anthropic.com"
DEFAULT_MODEL = "claude-sonnet-4-6"


class SettingsDao:
    @staticmethod
    @log_method
    def get_all() -> dict:
        return {row.key: row.value for row in SystemSetting.objects.all()}

    @staticmethod
    @log_method
    def get(key: str, default: str = "") -> str:
        row = SystemSetting.objects.filter(key=key).first()
        return row.value if row else default

    @staticmethod
    @log_method
    def set_many(data: dict):
        for key, value in data.items():
            SystemSetting.objects.update_or_create(key=key, defaults={"value": str(value)})


def _bootstrap_admin_from_env(user_id: int) -> UserLlmSetting:
    """admin 首次打开配置页时，从 .env 迁移一次 Key（便于升级）。"""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.filter(pk=user_id).first()
    setting, _ = UserLlmSetting.objects.get_or_create(user_id=user_id)
    if user and user.username == "admin" and not setting.anthropic_auth_token:
        token = getattr(settings, "ANTHROPIC_AUTH_TOKEN", "")
        if token:
            setting.anthropic_auth_token = token
            setting.anthropic_base_url = getattr(settings, "ANTHROPIC_BASE_URL", "") or ""
            setting.anthropic_model = getattr(settings, "ANTHROPIC_MODEL", "") or ""
            setting.save(update_fields=["anthropic_auth_token", "anthropic_base_url", "anthropic_model", "updated_at"])
    return setting


@log_method
def get_user_llm_setting(user_id: int) -> UserLlmSetting:
    return _bootstrap_admin_from_env(user_id)


@log_method
def get_agent_llm_config(user_id: Optional[int] = None) -> dict:
    """按用户读取 Agent LLM 配置；未传 user_id 时返回空 Key（仅默认 URL/模型）。"""
    base_default = (getattr(settings, "ANTHROPIC_BASE_URL", "") or DEFAULT_BASE_URL).rstrip("/")
    model_default = getattr(settings, "ANTHROPIC_MODEL", "") or DEFAULT_MODEL

    if not user_id:
        return {"api_key": "", "base_url": base_default, "model": model_default}

    row = get_user_llm_setting(user_id)
    base = (row.anthropic_base_url or base_default).rstrip("/")
    return {
        "api_key": row.anthropic_auth_token or "",
        "base_url": base,
        "model": row.anthropic_model or model_default,
    }


@log_method
def save_user_llm_setting(
    user_id: int,
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
):
    row, _ = UserLlmSetting.objects.get_or_create(user_id=user_id)
    if api_key:
        row.anthropic_auth_token = api_key
    if base_url is not None:
        row.anthropic_base_url = base_url
    if model is not None:
        row.anthropic_model = model
    row.save()
    return row


def _parse_bool(value: str, default: bool) -> bool:
    if value is None or value == "":
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


@log_method
def get_feishu_ws_enabled() -> bool:
    db_val = SettingsDao.get("feishu_ws_enabled", "")
    if db_val != "":
        return _parse_bool(db_val, False)
    return getattr(settings, "FEISHU_WS_ENABLED", False)


@log_method
def get_feishu_ws_require_mention() -> bool:
    db_val = SettingsDao.get("feishu_ws_require_mention", "")
    if db_val != "":
        return _parse_bool(db_val, False)
    return getattr(settings, "FEISHU_WS_REQUIRE_MENTION", False)


@log_method
def get_feishu_chat_group_id() -> str:
    return SettingsDao.get("feishu_chat_group_id", "").strip()


@log_method
def get_feishu_default_project_id() -> Optional[int]:
    raw = SettingsDao.get("feishu_default_project_id", "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


@log_method
def read_claude_settings():
    """兼容旧版：读取 ~/.claude/settings.json（已不再在 UI 暴露）。"""
    path = settings.CLAUDE_SETTINGS_PATH
    if not path or not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
