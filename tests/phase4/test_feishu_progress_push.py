from __future__ import annotations

from pathlib import Path

from app.feishu.status_push import (
    drain_pushed_messages,
    push_generation_percent,
    push_task_phase,
    reset_progress_notifications,
)


def test_push_task_phase_includes_keyword() -> None:
    drain_pushed_messages()
    push_task_phase("c1", "tid-111", "正文生成", "进入多段拼装")
    msgs = drain_pushed_messages()
    assert len(msgs) == 1
    assert msgs[0][0] == "c1"
    assert "正文生成" in msgs[0][1] and "tid-111" in msgs[0][1]


def test_percent_throttle_requires_step_or_elapsed() -> None:
    reset_progress_notifications()
    drain_pushed_messages()
    t = [0.0]

    def clock() -> float:
        return t[0]

    chat, tid = "c2", "tid-222"
    assert push_generation_percent(chat, tid, 10.0, now_mono=clock) is True
    assert push_generation_percent(chat, tid, 12.0, now_mono=clock) is False
    t[0] += 10.0
    assert push_generation_percent(chat, tid, 17.0, now_mono=clock) is True
    assert push_generation_percent(chat, tid, 100.0, now_mono=clock) is True
    payloads = drain_pushed_messages()
    assert len(payloads) == 3
    joined = "".join(p[1] for p in payloads)
    assert "正文进度" in joined


def test_feishu_feedback_requires_ids(tmp_path: Path) -> None:
    from app.db.sqlite_schema import get_connection, init_schema
    from app.feishu.router import handle_feishu_text_message
    from app.services.task_store import TaskStore

    drain_pushed_messages()
    db = tmp_path / "fdb.sqlite"
    conn = get_connection(db)
    init_schema(conn)
    store = TaskStore(conn)

    bad = handle_feishu_text_message(
        "/feedback score=4",
        chat_id="oc_x",
        open_id=None,
        store=store,
        enqueue_outline=lambda *_: None,
        sqlite_path=str(db),
    )
    assert not bad.ok


def test_feishu_feedback_happy(tmp_path: Path) -> None:
    from app.db.sqlite_schema import get_connection, init_schema
    from app.feishu.router import handle_feishu_text_message
    from app.services.task_store import TaskStore

    drain_pushed_messages()
    db = tmp_path / "fb2.sqlite"
    conn = get_connection(db)
    init_schema(conn)
    store = TaskStore(conn)
    tid = store.create_task(author="u", brief={})
    ok = handle_feishu_text_message(
        "/feedback score=5 task_id=" + tid,
        chat_id="oc_y",
        open_id=None,
        store=store,
        enqueue_outline=lambda *_: None,
        sqlite_path=str(db),
    )
    assert ok.ok
    msgs = drain_pushed_messages()
    assert any("人工评分 5/5" in m[1] for m in msgs)
    assert store.feedback_stats(tid)["count"] == 1

