"""飞书 WebSocket 长连接服务（Agent Loop 自研）。"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger("apps.webhook.feishu_ws")

_bridge_thread: Optional[threading.Thread] = None
_active_client = None
_restart_lock = threading.Lock()
_bridge_logs: list[str] = []
_bridge_status = "STOPPED"
_bridge_error = ""
_runtime_active = True
_seen_message_ids: dict[str, float] = {}
_seen_lock = threading.Lock()
_SEEN_TTL_SECONDS = 300


def _is_ws_enabled() -> bool:
    from apps.settings_app.dao.settings_dao import get_feishu_ws_enabled

    return get_feishu_ws_enabled()


def _append_log(line: str):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {line}"
    _bridge_logs.append(entry)
    if len(_bridge_logs) > 200:
        del _bridge_logs[:-200]
    logger.info(line)


def get_status() -> dict:
    enabled = _is_ws_enabled()
    if not enabled:
        status = "DISABLED"
    elif not _runtime_active:
        status = "DISABLED"
    else:
        status = _bridge_status
    return {
        "enabled": enabled and _runtime_active,
        "status": status,
        "error": _bridge_error,
        "endpoint": "wss://open.feishu.cn/open-apis/event/v1/outbound",
        "heartbeat": "Active" if status == "CONNECTED" else "Inactive",
        "using": "agent-loop-feishu-ws",
    }


def get_logs() -> list[str]:
    return list(_bridge_logs)


def _mark_message_seen(message_id: str) -> bool:
    """返回 True 表示首次见到该消息；False 表示重复应跳过。"""
    if not message_id:
        return True
    now = time.time()
    with _seen_lock:
        stale = [mid for mid, ts in _seen_message_ids.items() if now - ts > _SEEN_TTL_SECONDS]
        for mid in stale:
            _seen_message_ids.pop(mid, None)
        if message_id in _seen_message_ids:
            return False
        _seen_message_ids[message_id] = now
        return True


def _on_im_message(event: dict):
    if not _is_ws_enabled() or not _runtime_active:
        return

    from django.db import close_old_connections

    from apps.webhook.client.feishu_client import FeishuClient
    from apps.webhook.service.webhook_service import WebhookService

    close_old_connections()
    message = event.get("message") or {}
    chat_id = message.get("chat_id", "")
    message_id = message.get("message_id", "")
    text_preview = (message.get("_sdk_content_text") or "")[:80]

    if not _mark_message_seen(message_id):
        _append_log(f"忽略重复飞书消息 id={message_id}")
        return

    _append_log(f"收到飞书消息 chat={chat_id} 内容={text_preview!r}")

    try:
        result = WebhookService.handle_feishu_event({"event": event})
    except Exception as exc:
        _append_log(f"处理飞书消息失败 chat={chat_id}: {exc}")
        logger.exception("handle feishu message failed")
        return

    if isinstance(result, dict) and result.get("reply"):
        reply = str(result["reply"])
        FeishuClient.send_text(chat_id, reply)
        _append_log(f"已回复飞书 chat={chat_id}: {reply[:80]}")


def _on_im_reject(event) -> None:
    from django.db import close_old_connections

    from apps.webhook.client.feishu_client import FeishuClient

    close_old_connections()
    chat_id = getattr(event, "chat_id", "") or ""
    reason = getattr(event, "reason", "") or "unknown"
    hint = ""
    if reason == "policy_no_mention":
        hint = "（请 @ 机器人，或关闭「群聊需 @ 机器人」）"
        _append_log(f"收到群消息但被过滤 chat={chat_id} 原因={reason}{hint}")
        if chat_id:
            FeishuClient.send_text(
                chat_id,
                "未处理：请在消息中 @Agent Loop，或在 Agent Loop 配置管理里关闭「群聊需 @ 机器人」。",
            )
        return
    _append_log(f"收到群消息但被过滤 chat={chat_id} 原因={reason}{hint}")


def _run_bridge_loop():
    global _bridge_status, _bridge_error, _active_client
    try:
        from django.conf import settings

        from apps.settings_app.dao.settings_dao import SettingsDao, get_feishu_ws_require_mention
        from apps.webhook.client.feishu_ws_client import FeishuWsClient

        if not _is_ws_enabled() or not _runtime_active:
            _bridge_status = "DISABLED"
            return

        rows = SettingsDao.get_all()
        app_id = rows.get("feishu_app_id") or getattr(settings, "FEISHU_APP_ID", "")
        app_secret = rows.get("feishu_app_secret") or getattr(settings, "FEISHU_APP_SECRET", "")
        if not app_id or not app_secret:
            _bridge_status = "NOT_CONFIGURED"
            _bridge_error = "未配置飞书 App ID / Secret（请在配置管理填写）"
            _append_log(_bridge_error)
            return

        require_mention = get_feishu_ws_require_mention()
        _bridge_status = "CONNECTING"
        _append_log("飞书 WebSocket 连接中…")

        from apps.webhook.client.feishu_client import FeishuClient

        bot_open_id = FeishuClient.get_bot_open_id()
        if not bot_open_id:
            _append_log("警告：未能获取 bot open_id（发消息仍可用；@过滤将失效）")
        client = FeishuWsClient(
            app_id,
            app_secret,
            require_mention=require_mention,
            bot_open_id=bot_open_id,
        )
        _active_client = client
        _bridge_status = "CONNECTING"
        mention_tip = "需 @ 机器人" if require_mention else "无需 @ 机器人"
        _append_log(f"飞书 WebSocket 正在建立连接（{mention_tip}）…")

        def _mark_connected() -> None:
            global _bridge_status, _bridge_error
            _bridge_status = "CONNECTED"
            _bridge_error = ""
            _append_log("飞书 WebSocket 已连通，可接收群消息")

        client.run_blocking(
            _on_im_message,
            on_reject=_on_im_reject,
            on_trace=_append_log,
            on_connected=_mark_connected,
        )
    except ImportError:
        _bridge_status = "ERROR"
        _bridge_error = "缺少依赖 lark-oapi，请执行 pip install lark-oapi"
        _append_log(_bridge_error)
        logger.exception("feishu ws import failed")
    except Exception as exc:
        if "Event loop stopped" in str(exc):
            _append_log("飞书 WebSocket 已停止（热重连）")
        else:
            _bridge_status = "ERROR"
            _bridge_error = str(exc)
            _append_log(f"连接失败: {exc}")
            logger.exception("feishu ws bridge failed")
    finally:
        _active_client = None
        if _runtime_active and _is_ws_enabled() and _bridge_status == "CONNECTED":
            _bridge_status = "STOPPED"
            _append_log("飞书 WebSocket 连接已断开")


def stop_feishu_ws(*, wait_timeout: float = 8.0) -> bool:
    global _bridge_thread, _active_client

    client = _active_client
    if client is not None:
        _append_log("正在停止飞书 WebSocket…")
        client.stop()

    thread = _bridge_thread
    if thread and thread.is_alive():
        thread.join(timeout=wait_timeout)
        if thread.is_alive():
            _append_log("停止超时，将在下次重连时替换旧连接")
            return False

    _bridge_thread = None
    _active_client = None
    return True


def start_feishu_ws_daemon():
    global _bridge_thread, _runtime_active
    _runtime_active = True
    if not _is_ws_enabled():
        return
    if _bridge_thread and _bridge_thread.is_alive():
        return
    _append_log("启动 Agent Loop 飞书 WebSocket 服务")
    _bridge_thread = threading.Thread(target=_run_bridge_loop, name="feishu-ws", daemon=True)
    _bridge_thread.start()


def restart_feishu_ws():
    """热重连：停止当前 WS 线程并用最新配置重新连接。"""
    global _runtime_active, _bridge_status, _bridge_error, _bridge_thread

    with _restart_lock:
        if not _is_ws_enabled():
            _runtime_active = False
            stop_feishu_ws()
            _bridge_status = "DISABLED"
            _bridge_error = ""
            _append_log("飞书 WebSocket 已在配置中关闭")
            return

        _runtime_active = True
        stop_feishu_ws()
        _bridge_thread = None
        _bridge_status = "STOPPED"
        _bridge_error = ""
        _append_log("正在重新连接飞书 WebSocket（无需重启后端）…")
        start_feishu_ws_daemon()


def apply_feishu_ws_settings():
    """保存配置后应用长连接（支持热重连）。"""
    restart_feishu_ws()
