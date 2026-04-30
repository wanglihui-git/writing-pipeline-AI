from __future__ import annotations

import json
from typing import Any

from lark_oapi.api.im.v1.model.p2_im_message_receive_v1 import P2ImMessageReceiveV1


def im_receive_v1_to_router_event(data: P2ImMessageReceiveV1) -> dict[str, Any]:
    """
    将 lark-oapi 的 P2ImMessageReceiveV1 转为与单测/HTTP 回调一致的 dict，
    供 `extract_im_text_event` / `process_im_event_v1` 使用。
    """
    if data.event is None or data.event.message is None:
        raise ValueError("im.message.receive_v1 缺少 event.message")
    msg = data.event.message
    content = msg.content
    if not content:
        raise ValueError("消息 content 为空")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"message.content 不是合法 JSON: {e}") from e
    if isinstance(parsed, dict) and "text" not in parsed:
        raise ValueError("非文本类消息（需要 content.text）")

    sender_block: dict[str, Any] = {}
    if data.event.sender and data.event.sender.sender_id:
        uid = data.event.sender.sender_id
        inner: dict[str, str] = {}
        if uid.open_id:
            inner["open_id"] = uid.open_id
        if uid.user_id:
            inner["user_id"] = uid.user_id
        if inner:
            sender_block["sender_id"] = inner

    cid = msg.chat_id or ""
    inner_event: dict[str, Any] = {
        "message": {
            "content": content,
            "chat_id": msg.chat_id,
        },
        "sender": sender_block,
        "chat_id": cid,
    }
    return {"event": inner_event}
