import json
import time
from typing import Optional

import requests
from django.conf import settings

from apps.common.util.circuit_breaker import CircuitOpenError, feishu_breaker
from apps.common.util.logging_util import log_external_call, log_method
from apps.settings_app.dao.settings_dao import SettingsDao

_NO_PROXY = {"http": None, "https": None}


class FeishuClient:
    _token_cache: Optional[str] = None
    _token_expire: float = 0

    @staticmethod
    @log_method
    def _credentials() -> dict:
        rows = SettingsDao.get_all()
        return {
            "app_id": rows.get("feishu_app_id") or getattr(settings, "FEISHU_APP_ID", ""),
            "app_secret": rows.get("feishu_app_secret") or getattr(settings, "FEISHU_APP_SECRET", ""),
        }

    @staticmethod
    @log_method
    def is_configured() -> bool:
        cred = FeishuClient._credentials()
        return bool(cred["app_id"] and cred["app_secret"])

    @staticmethod
    @log_method
    def _tenant_access_token() -> Optional[str]:
        if FeishuClient._token_cache and time.time() < FeishuClient._token_expire:
            return FeishuClient._token_cache
        cred = FeishuClient._credentials()
        if not cred["app_id"] or not cred["app_secret"]:
            return None
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        body = {"app_id": cred["app_id"], "app_secret": cred["app_secret"]}
        start = time.time()
        try:
            resp = feishu_breaker.call(requests.post, url, json=body, timeout=30, proxies=_NO_PROXY)
            duration = int((time.time() - start) * 1000)
            data = resp.json()
            log_external_call("feishu", url, {"app_id": cred["app_id"]}, str(data)[:500], duration)
            resp.raise_for_status()
            if data.get("code") != 0:
                raise RuntimeError(data.get("msg", "feishu auth failed"))
            FeishuClient._token_cache = data["tenant_access_token"]
            FeishuClient._token_expire = time.time() + int(data.get("expire", 7200)) - 60
            return FeishuClient._token_cache
        except CircuitOpenError:
            raise
        except Exception as exc:
            duration = int((time.time() - start) * 1000)
            log_external_call("feishu", url, body, None, duration, str(exc))
            return None

    @staticmethod
    @log_method
    def send_card(chat_id: str, title: str, task_title: str, phase: str):
        text = f"[{phase}] {title}: {task_title}"
        FeishuClient.send_text(chat_id, text)

    @staticmethod
    @log_method
    def send_text(chat_id: str, text: str):
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        body = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }
        start = time.time()

        if not FeishuClient.is_configured() or not chat_id:
            log_external_call("feishu", url, body, {"simulated": True, "reason": "not_configured"}, int((time.time() - start) * 1000))
            return

        token = FeishuClient._tenant_access_token()
        if not token:
            log_external_call("feishu", url, body, {"simulated": True, "reason": "no_token"}, int((time.time() - start) * 1000))
            return

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        params = {"receive_id_type": "chat_id"}
        try:
            resp = feishu_breaker.call(
                requests.post,
                url,
                params=params,
                json=body,
                headers=headers,
                timeout=30,
                proxies=_NO_PROXY,
            )
            duration = int((time.time() - start) * 1000)
            log_external_call("feishu", url, body, resp.text[:2000], duration)
            resp.raise_for_status()
        except CircuitOpenError as exc:
            duration = int((time.time() - start) * 1000)
            log_external_call("feishu", url, body, {"circuit_open": True}, duration, str(exc))
        except Exception as exc:
            duration = int((time.time() - start) * 1000)
            log_external_call("feishu", url, body, None, duration, str(exc))

    @staticmethod
    @log_method
    def classify_intent(text: str) -> str:
        """仅识别固定指令「新建任务：…」，避免歧义。"""
        from apps.webhook.service.feishu_review_service import parse_create_body

        if parse_create_body(text):
            return "CREATE_TASK"
        return "CHAT_COMMENT"

    @staticmethod
    @log_method
    def get_bot_open_id() -> str:
        if not FeishuClient.is_configured():
            return ""
        token = FeishuClient._tenant_access_token()
        if not token:
            return ""
        url = "https://open.feishu.cn/open-apis/bot/v3/info"
        headers = {"Authorization": f"Bearer {token}"}
        start = time.time()
        try:
            resp = feishu_breaker.call(requests.get, url, headers=headers, timeout=30, proxies=_NO_PROXY)
            duration = int((time.time() - start) * 1000)
            data = resp.json()
            log_external_call("feishu", url, {}, str(data)[:500], duration)
            resp.raise_for_status()
            if data.get("code") != 0:
                return ""
            bot = data.get("bot") or {}
            return bot.get("open_id") or ""
        except Exception as exc:
            duration = int((time.time() - start) * 1000)
            log_external_call("feishu", url, {}, None, duration, str(exc))
            return ""

    @staticmethod
    @log_method
    def list_bot_chats(*, page_size: int = 50) -> list[dict]:
        """获取机器人所在群列表（用于配置 chat_id）。"""
        if not FeishuClient.is_configured():
            raise ValueError("未配置飞书 App ID / Secret")

        token = FeishuClient._tenant_access_token()
        if not token:
            raise ValueError("飞书鉴权失败，请检查 App ID / Secret")

        url = "https://open.feishu.cn/open-apis/im/v1/chats"
        headers = {"Authorization": f"Bearer {token}"}
        items: list[dict] = []
        page_token = ""
        start = time.time()

        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            resp = feishu_breaker.call(requests.get, url, headers=headers, params=params, timeout=30, proxies=_NO_PROXY)
            duration = int((time.time() - start) * 1000)
            data = resp.json()
            log_external_call("feishu", url, params, str(data)[:2000], duration)
            resp.raise_for_status()
            if data.get("code") != 0:
                raise RuntimeError(data.get("msg") or "获取群列表失败")

            payload = data.get("data") or {}
            for row in payload.get("items") or []:
                chat_id = row.get("chat_id") or ""
                if not chat_id:
                    continue
                items.append(
                    {
                        "chatId": chat_id,
                        "name": row.get("name") or chat_id,
                        "description": row.get("description") or "",
                    }
                )

            if not payload.get("has_more"):
                break
            page_token = payload.get("page_token") or ""
            if not page_token:
                break

        return items
