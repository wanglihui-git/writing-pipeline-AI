from __future__ import annotations

import pytest

from app.db.sqlite_schema import get_connection, init_schema
from app.domain.state_machine import TaskState
from app.pipeline.models import OutlineDocument, OutlineParagraph, OutlineSection
from app.pipeline.outline_gate import OutlineNotConfirmedError, assert_can_generate_draft
from app.services.task_store import TaskStore


def _outline() -> OutlineDocument:
    return OutlineDocument(
        title="o",
        sections=[
            OutlineSection(
                section_title="一",
                section_goal="g",
                paragraphs=[OutlineParagraph(purpose="p", evidence_slots=["e"])],
            ),
        ],
    )


def test_draft_blocked_without_confirm(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "db.sqlite")
    init_schema(conn)
    store = TaskStore(conn)
    tid = store.create_task()
    store.force_state(tid, TaskState.WAIT_OUTLINE_CONFIRM)
    store.persist_outline_revision(tid, _outline(), model_id="stub")
    task = store.get_task(tid)
    assert task is not None
    assert task.outline_confirmed is False
    with pytest.raises(OutlineNotConfirmedError):
        assert_can_generate_draft(task)


def test_draft_allowed_after_confirm(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "db.sqlite")
    init_schema(conn)
    store = TaskStore(conn)
    tid = store.create_task()
    store.force_state(tid, TaskState.WAIT_OUTLINE_CONFIRM)
    store.persist_outline_revision(tid, _outline(), model_id="stub")
    store.confirm_outline(tid)
    task = store.get_task(tid)
    assert task is not None
    assert_can_generate_draft(task)


def test_outline_revision_increments_and_clears_confirm(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "db.sqlite")
    init_schema(conn)
    store = TaskStore(conn)
    tid = store.create_task()
    o1 = _outline()
    o2 = o1.model_copy(update={"title": "v2"})
    v1 = store.persist_outline_revision(tid, o1, model_id="m1")
    store.confirm_outline(tid)
    assert store.get_task(tid).outline_confirmed is True  # type: ignore[union-attr]
    v2 = store.persist_outline_revision(tid, o2, model_id="m2")
    assert v2 == v1 + 1
    assert store.get_task(tid).outline_confirmed is False  # type: ignore[union-attr]
