from __future__ import annotations

import json

import pytest
from lark_oapi.api.im.v1.model.p2_im_message_receive_v1 import P2ImMessageReceiveV1

from app.feishu.event_adapter import im_receive_v1_to_router_event
from app.feishu.router import extract_im_text_event


def test_im_receive_v1_adapter_extract_aligns_with_router() -> None:
    raw = {
        "event": {
            "sender": {"sender_id": {"open_id": "ou_demo", "user_id": "u1"}},
            "message": {
                "chat_id": "oc_demo",
                "content": json.dumps({"text": "/outline author=Lia topic=AI"}, ensure_ascii=False),
                "chat_type": "group",
            },
        }
    }
    data = P2ImMessageReceiveV1(raw)
    ev = im_receive_v1_to_router_event(data)
    text, cid, oid = extract_im_text_event(ev)
    assert "/outline" in text
    assert cid == "oc_demo"
    assert oid == "ou_demo"


def test_adapter_rejects_missing_text_payload() -> None:
    raw = {
        "event": {
            "sender": {},
            "message": {
                "chat_id": "oc_x",
                "content": json.dumps({"foo": "bar"}),
            },
        }
    }
    data = P2ImMessageReceiveV1(raw)
    with pytest.raises(ValueError, match="非文本"):
        im_receive_v1_to_router_event(data)
