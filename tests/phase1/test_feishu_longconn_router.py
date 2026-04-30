from __future__ import annotations

import json

import pytest

from app.db.sqlite_schema import get_connection, init_schema
from app.feishu.router import (
    extract_im_text_event,
    handle_feishu_text_message,
    parse_command_text,
    parse_kv_args,
)
from app.feishu.status_push import drain_pushed_messages
from app.services.task_store import TaskStore

from pathlib import Path


def test_parse_command_and_kv() -> None:
    cmd = parse_command_text("/outline author=鲁迅 topic=人工智能")
    assert cmd.name == "outline"
    kv = parse_kv_args(cmd.rest)
    assert kv["author"] == "鲁迅"
    assert kv["topic"] == "人工智能"


def test_parse_command_unknown_raises() -> None:
    with pytest.raises(ValueError):
        parse_command_text("/unknown")


def test_extract_im_text_event_minimal() -> None:
    event = {
        "event": {
            "chat_id": "oc_1",
            "message": {"content": json.dumps({"text": "/score task_id=abc"}, ensure_ascii=False)},
            "sender": {"sender_id": {"open_id": "ou_1"}},
        }
    }
    text, chat_id, open_id = extract_im_text_event(event)
    assert "/score" in text
    assert chat_id == "oc_1"
    assert open_id == "ou_1"


def test_handle_outline_requires_author(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "f.db")
    init_schema(conn)
    store = TaskStore(conn)

    def _noop(tid: str, path: str) -> None:
        return None

    r = handle_feishu_text_message(
        "/outline topic=x",
        chat_id="c1",
        open_id="u1",
        store=store,
        enqueue_outline=_noop,
        sqlite_path=str(tmp_path / "f.db"),
    )
    assert not r.ok
    conn.close()


def test_handle_outline_happy_path(tmp_path: Path) -> None:
    drain_pushed_messages()
    conn = get_connection(tmp_path / "f2.db")
    init_schema(conn)
    store = TaskStore(conn)
    pushed: list[tuple[str, str]] = []

    def _enqueue(tid: str, path: str) -> None:
        pushed.append((tid, path))

    r = handle_feishu_text_message(
        '/outline author=DemoUser topic="hello world"',
        chat_id="c2",
        open_id="u2",
        store=store,
        enqueue_outline=_enqueue,
        sqlite_path=str(tmp_path / "f2.db"),
    )
    assert r.ok and r.task_id
    assert pushed and pushed[0][0] == r.task_id
    msgs = drain_pushed_messages()
    assert msgs and "任务已创建" in msgs[0][1]
    conn.close()
