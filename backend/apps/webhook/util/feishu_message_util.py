"""飞书 IM 消息解析（Agent Loop 自研，不依赖 feishu_lark_channel）。"""
from __future__ import annotations

import json
import re
from typing import Any

_MENTION_RE = re.compile(r"@\S+\s*")


def strip_mentions(text: str) -> str:
    return _MENTION_RE.sub("", text or "").strip()


def _text_from_post_runs(rows: Any) -> str:
    if not isinstance(rows, list):
        return ""
    parts: list[str] = []
    for line in rows:
        if not isinstance(line, list):
            continue
        line_bits: list[str] = []
        for run in line:
            if not isinstance(run, dict):
                continue
            tag = str(run.get("tag") or "").strip().casefold()
            if tag in ("text", "md", "a"):
                line_bits.append(str(run.get("text") or run.get("href") or ""))
            elif tag == "at":
                name = str(run.get("user_name") or run.get("user_id") or "")
                if name.strip():
                    line_bits.append(f"@{name}")
        if line_bits:
            parts.append("".join(line_bits))
    return "\n".join(parts).strip()


def _plaintext_from_content(data: dict, message_type: str = "") -> str:
    mt = (message_type or "").strip().casefold()
    if mt == "text" or "text" in data:
        text = str(data.get("text") or "").strip()
        if text:
            return text

    block = None
    for key in ("zh_cn", "en_us", "ja_jp"):
        if isinstance(data.get(key), dict):
            block = data[key]
            break
    if block is None and isinstance(data.get("content"), list):
        block = data

    if block is not None:
        title = str(block.get("title") or "").strip()
        body = _text_from_post_runs(block.get("content"))
        if title and body:
            return f"{title}\n{body}".strip()
        return (body or title).strip()

    return str(data.get("text") or "").strip()


def extract_message_text(event: dict) -> str:
    """从飞书 event（含 message 字段）提取纯文本。"""
    message = event.get("message") or {}
    sdk_plain = str(message.get("_sdk_content_text") or "").strip()
    content = message.get("content")
    message_type = str(message.get("message_type") or "")

    if isinstance(content, str) and content.strip():
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                parsed = _plaintext_from_content(data, message_type)
                if parsed:
                    return strip_mentions(parsed)
        except json.JSONDecodeError:
            pass

    if sdk_plain:
        return strip_mentions(sdk_plain)
    if isinstance(content, str) and content.strip():
        return strip_mentions(content)
    return ""


def inbound_message_to_event(msg: Any) -> dict:
    """将 lark-oapi InboundMessage 转为 WebhookService 可处理的 event 结构。"""
    sender = getattr(msg, "sender", None)
    open_id = getattr(sender, "open_id", "") if sender else ""
    display_name = getattr(sender, "display_name", None) if sender else None
    text = strip_mentions(getattr(msg, "content_text", "") or "")

    message: dict[str, Any] = {
        "message_id": getattr(msg, "message_id", "") or getattr(msg, "id", ""),
        "chat_id": getattr(msg, "chat_id", ""),
        "message_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
        "_sdk_content_text": text,
    }
    reply_id = getattr(msg, "reply_to_message_id", None)
    if reply_id:
        message["parent_id"] = reply_id

    raw = getattr(msg, "raw", None)
    if isinstance(raw, dict):
        raw_msg = raw.get("message")
        if isinstance(raw_msg, dict):
            for key in ("message_type", "root_id", "parent_id"):
                if raw_msg.get(key) and not message.get(key):
                    message[key] = raw_msg[key]
            if not text and raw_msg.get("content"):
                message["content"] = raw_msg["content"]
                text = extract_message_text({"message": message})
                message["_sdk_content_text"] = text
                message["content"] = json.dumps({"text": text}, ensure_ascii=False)

    return {
        "message": message,
        "sender": {
            "sender_id": {"open_id": open_id},
            "sender_type": "user",
            "sender_name": display_name,
        },
    }


def p2_message_to_event(data: Any) -> dict:
    """将 lark-oapi P2ImMessageReceiveV1 转为 WebhookService 可处理的 event 结构。"""
    event = getattr(data, "event", None)
    message_obj = getattr(event, "message", None) if event else None
    sender_obj = getattr(event, "sender", None) if event else None

    message: dict[str, Any] = {}
    if message_obj is not None:
        message = {
            "message_id": message_obj.message_id or "",
            "chat_id": message_obj.chat_id or "",
            "message_type": message_obj.message_type or "text",
            "content": message_obj.content or "",
        }
        if message_obj.parent_id:
            message["parent_id"] = message_obj.parent_id
        if message_obj.root_id:
            message["root_id"] = message_obj.root_id
        text = extract_message_text({"message": message})
        message["_sdk_content_text"] = text
        message["content"] = json.dumps({"text": text}, ensure_ascii=False)

    sender: dict[str, Any] = {}
    if sender_obj is not None:
        sender_id = getattr(sender_obj, "sender_id", None)
        open_id = getattr(sender_id, "open_id", "") if sender_id else ""
        sender = {
            "sender_id": {"open_id": open_id},
            "sender_type": sender_obj.sender_type or "user",
        }

    return {"message": message, "sender": sender}


def message_mentions_bot(data: Any, bot_open_id: str) -> bool:
    """检查 P2 消息是否 @ 了机器人。"""
    if not bot_open_id:
        return True
    event = getattr(data, "event", None)
    message_obj = getattr(event, "message", None) if event else None
    if message_obj is None:
        return False
    for mention in message_obj.mentions or []:
        mention_id = getattr(mention, "id", None)
        if mention_id and getattr(mention_id, "open_id", "") == bot_open_id:
            return True
    return False


def json_message_to_event(payload: dict) -> dict:
    """将飞书 WS JSON 事件转为 WebhookService 可处理的 event 结构。"""
    event_body = payload.get("event") or {}
    message_raw = event_body.get("message") or {}
    sender_raw = event_body.get("sender") or {}

    message: dict[str, Any] = {
        "message_id": message_raw.get("message_id") or "",
        "chat_id": message_raw.get("chat_id") or "",
        "message_type": message_raw.get("message_type") or "text",
        "content": message_raw.get("content") or "",
    }
    for key in ("parent_id", "root_id"):
        if message_raw.get(key):
            message[key] = message_raw[key]

    text = extract_message_text({"message": message})
    message["_sdk_content_text"] = text
    message["content"] = json.dumps({"text": text}, ensure_ascii=False)

    sender_id = sender_raw.get("sender_id") or {}
    sender = {
        "sender_id": {"open_id": sender_id.get("open_id") or ""},
        "sender_type": sender_raw.get("sender_type") or "user",
    }
    return {"message": message, "sender": sender}


def message_mentions_bot_json(message: dict, bot_open_id: str) -> bool:
    """检查 JSON 消息是否 @ 了机器人。"""
    if not bot_open_id:
        return True
    for mention in message.get("mentions") or []:
        if not isinstance(mention, dict):
            continue
        mention_id = mention.get("id") or {}
        if isinstance(mention_id, dict) and mention_id.get("open_id") == bot_open_id:
            return True
    return False
