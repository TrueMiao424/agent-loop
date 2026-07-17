"""飞书 WebSocket 长连接客户端（基于 lark-oapi WS Client，Agent Loop 自研）。"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
from types import SimpleNamespace
from typing import Callable, Optional

logger = logging.getLogger("apps.webhook.feishu_ws_client")

OnMessageCallback = Callable[[dict], None]
OnRejectCallback = Callable[[object], None]
OnTraceCallback = Callable[[str], None]

_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="feishu-ws")

_FEISHU_HOST_MARKERS = ("feishu.cn", "larksuite.com", "larkoffice.com")


def _prepare_thread_event_loop() -> asyncio.AbstractEventLoop:
    """lark-oapi ws 模块在 import 时绑定全局 loop，须在独立线程里重建。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


def _ensure_feishu_bypass_proxy() -> None:
    """飞书长连接鉴权勿走本地 HTTP 代理（否则易 ProxyError / 假连接）。"""
    hosts = [
        "open.feishu.cn",
        "msg-frontier.feishu.cn",
        ".feishu.cn",
        ".larksuite.com",
        ".larkoffice.com",
    ]
    for key in ("NO_PROXY", "no_proxy"):
        cur = os.environ.get(key, "")
        parts = [p.strip() for p in cur.split(",") if p.strip()]
        changed = False
        for host in hosts:
            if host not in parts:
                parts.append(host)
                changed = True
        if changed:
            os.environ[key] = ",".join(parts)


def _install_feishu_requests_no_proxy():
    """临时让 requests 访问飞书域名时强制不走代理。"""
    import requests

    original_post = requests.post

    def post_no_proxy(*args, **kwargs):
        url = str(args[0] if args else kwargs.get("url") or "")
        if any(marker in url for marker in _FEISHU_HOST_MARKERS):
            kwargs = dict(kwargs)
            kwargs["proxies"] = {"http": None, "https": None}
        return original_post(*args, **kwargs)

    requests.post = post_no_proxy  # type: ignore[method-assign]
    return original_post


class FeishuWsClient:
    """封装飞书官方 lark-oapi WS Client，直接接收 im.message.receive_v1 事件。"""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        *,
        require_mention: bool = False,
        bot_open_id: str = "",
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.require_mention = require_mention
        self.bot_open_id = bot_open_id
        self._ws_client = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def stop(self) -> None:
        ws = self._ws_client
        loop = self._loop
        if ws is not None:
            ws._auto_reconnect = False
        if loop is None or loop.is_closed() or not loop.is_running():
            return

        try:
            future = asyncio.run_coroutine_threadsafe(ws._disconnect(), loop)
            future.result(timeout=5)
        except Exception:
            logger.exception("FeishuWsClient disconnect failed")
        try:
            loop.call_soon_threadsafe(loop.stop)
        except RuntimeError:
            pass

    def run_blocking(
        self,
        on_message: OnMessageCallback,
        *,
        on_reject: Optional[OnRejectCallback] = None,
        on_trace: Optional[OnTraceCallback] = None,
        on_connected: Optional[Callable[[], None]] = None,
    ) -> None:
        """阻塞运行 WebSocket（须在独立线程中调用）。"""
        _ensure_feishu_bypass_proxy()
        original_post = _install_feishu_requests_no_proxy()
        loop = _prepare_thread_event_loop()
        self._loop = loop

        import lark_oapi.ws.client as lark_ws_client

        lark_ws_client.loop = loop

        from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
        from lark_oapi.ws.client import Client as LarkWsClient

        from apps.webhook.util.feishu_message_util import (
            json_message_to_event,
            message_mentions_bot_json,
        )

        def _trace(line: str) -> None:
            if on_trace is not None:
                on_trace(line)
            logger.info(line)

        def _submit(fn, *args) -> None:
            """在独立线程执行 Django/HTTP，避免阻塞 WS asyncio loop。"""

            def _run() -> None:
                try:
                    fn(*args)
                except Exception as exc:
                    _trace(f"处理飞书消息异常: {exc}")
                    logger.exception("FeishuWsClient dispatch failed")

            _EXECUTOR.submit(_run)

        def _dispatch_json(payload: dict) -> None:
            header = payload.get("header") or {}
            event_type = header.get("event_type") or "unknown"
            _trace(f"处理 WS 事件: {event_type}")

            if event_type != "im.message.receive_v1":
                return

            event_body = payload.get("event") or {}
            sender = event_body.get("sender") or {}
            if sender.get("sender_type") == "app":
                _trace("忽略机器人自身消息")
                return

            message_raw = event_body.get("message") or {}
            message_id = message_raw.get("message_id") or ""
            if not message_id:
                _trace("消息缺少 message_id，已跳过")
                return

            chat_id = message_raw.get("chat_id") or ""
            parsed = json_message_to_event(payload)
            text_preview = (parsed.get("message") or {}).get("_sdk_content_text") or ""
            text_preview = text_preview[:80]

            if self.require_mention and not message_mentions_bot_json(message_raw, self.bot_open_id):
                _trace(f"消息被 @ 过滤 chat={chat_id} 内容={text_preview!r}")
                if on_reject is not None:
                    _submit(
                        on_reject,
                        SimpleNamespace(
                            chat_id=chat_id,
                            reason="policy_no_mention",
                            message_id=message_id,
                        ),
                    )
                return

            _trace(f"收到飞书消息 chat={chat_id} 内容={text_preview!r}")
            _submit(on_message, parsed)

        def _handle_p2(_data) -> None:
            """SDK 回调占位：业务已在 JSON 帧路径处理，避免重复执行。"""
            return

        class _LoggingWsClient(LarkWsClient):
            async def _connect(self):  # noqa: ANN001
                await super()._connect()
                _trace(f"飞书 WS 底层已连通 conn_id={getattr(self, '_conn_id', '')}")
                if on_connected is not None:
                    try:
                        on_connected()
                    except Exception:
                        logger.exception("on_connected callback failed")

            async def _handle_data_frame(self, frame):  # noqa: ANN001
                pl = frame.payload
                try:
                    from lark_oapi.ws.client import (
                        HEADER_MESSAGE_ID,
                        HEADER_SEQ,
                        HEADER_SUM,
                        HEADER_TYPE,
                        _get_by_key,
                    )
                    from lark_oapi.ws.enum import MessageType

                    hs = frame.headers
                    msg_id = _get_by_key(hs, HEADER_MESSAGE_ID)
                    sum_ = _get_by_key(hs, HEADER_SUM)
                    seq = _get_by_key(hs, HEADER_SEQ)
                    type_ = _get_by_key(hs, HEADER_TYPE)
                    if int(sum_) > 1:
                        pl = self._combine(msg_id, int(sum_), int(seq), pl)
                        if pl is None:
                            return await super()._handle_data_frame(frame)

                    if MessageType(type_) == MessageType.EVENT:
                        try:
                            payload = json.loads(pl.decode("utf-8"))
                            event_type = (payload.get("header") or {}).get("event_type") or "unknown"
                            _trace(f"WS 原始事件: {event_type} id={msg_id}")
                            _dispatch_json(payload)
                        except Exception as exc:
                            _trace(f"WS 事件解析失败 id={msg_id}: {exc}")
                            logger.exception("FeishuWsClient raw frame dispatch failed")
                except Exception:
                    logger.exception("FeishuWsClient raw frame log failed")
                await super()._handle_data_frame(frame)

        event_handler = (
            EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(_handle_p2)
            .build()
        )

        ws = _LoggingWsClient(self.app_id, self.app_secret, event_handler=event_handler)
        self._ws_client = ws
        _trace(
            f"FeishuWsClient 启动 app_id={self.app_id} "
            f"require_mention={self.require_mention} bot={self.bot_open_id[:12] if self.bot_open_id else 'n/a'}"
        )
        try:
            ws.start()
        finally:
            import requests

            requests.post = original_post  # type: ignore[method-assign]
            self._ws_client = None
            self._loop = None
