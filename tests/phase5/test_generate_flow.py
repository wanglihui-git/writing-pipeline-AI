from __future__ import annotations

from pathlib import Path

from app.db.sqlite_schema import get_connection, init_schema
from app.domain.state_machine import TaskState
from app.feishu.router import handle_feishu_text_message
from app.pipeline.models import OutlineDocument, OutlineParagraph, OutlineSection
from app.services.task_store import TaskStore
from app.workers.tasks import process_generate_task


def _outline() -> OutlineDocument:
    return OutlineDocument(
        title="o",
        sections=[
            OutlineSection(
                section_title="一",
                section_goal="g",
                paragraphs=[OutlineParagraph(purpose="p", evidence_slots=["e"])],
            )
        ],
    )


def test_feishu_generate_command_enqueues_when_callback_provided(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "fg.sqlite")
    init_schema(conn)
    store = TaskStore(conn)
    tid = store.create_task(
        author="a",
        brief={
            "topic": "t",
            "angle": "a",
            "thesis": "th",
            "argument_framework": "af",
            "narrative_skeleton": "ns",
            "target_audience": "aud",
        },
    )
    queued: list[tuple[str, str]] = []

    def _enqueue_outline(task_id: str, path: str) -> None:
        _ = (task_id, path)

    def _enqueue_generate(task_id: str, path: str) -> None:
        queued.append((task_id, path))

    r = handle_feishu_text_message(
        f"/generate task_id={tid}",
        chat_id="oc_x",
        open_id="ou_x",
        store=store,
        enqueue_outline=_enqueue_outline,
        sqlite_path=str(tmp_path / "fg.sqlite"),
        enqueue_generate=_enqueue_generate,
    )
    assert r.ok
    assert queued and queued[0][0] == tid


def test_worker_generate_task_persists_article_and_score(tmp_path: Path) -> None:
    db = tmp_path / "wg.sqlite"
    conn = get_connection(db)
    init_schema(conn)
    store = TaskStore(conn)
    tid = store.create_task(
        author="a",
        brief={
            "topic": "主题",
            "angle": "角度",
            "thesis": "命题",
            "argument_framework": "框架",
            "narrative_skeleton": "骨架",
            "target_audience": "读者",
        },
    )
    store.force_state(tid, TaskState.WAIT_OUTLINE_CONFIRM)
    store.persist_outline_revision(tid, _outline(), model_id="stub")
    store.confirm_outline(tid)

    process_generate_task(task_id=tid, sqlite_path=str(db))
    rec = store.get_task(tid)
    assert rec is not None and rec.state == TaskState.READY
    bundle = store.fetch_latest_article_bundle(tid)
    assert bundle is not None and bundle.concatenated_polished.strip()
    row = conn.execute("SELECT COUNT(*) AS c FROM scores WHERE task_id=?", (tid,)).fetchone()
    assert int(row["c"]) >= 1
