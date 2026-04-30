from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.sqlite_schema import get_connection, init_schema
from app.services.task_store import TaskStore


def test_rest_feedback_aggregate(client: TestClient) -> None:
    r = client.post("/tasks/", json={"brief": {}, "author": "x"})
    assert r.status_code == 200
    tid = r.json()["task_id"]
    assert client.post(f"/tasks/{tid}/feedback", json={"score_1_5": 5, "comment": "很棒"}).status_code == 200
    assert client.post(f"/tasks/{tid}/feedback", json={"score_1_5": 3}).status_code == 200
    s = client.get(f"/tasks/{tid}/feedback/stats")
    assert s.status_code == 200
    payload = s.json()
    assert payload["count"] == 2
    assert payload["avg_1_5"] is not None
    assert payload["distribution"].get("5") == 1
    assert len(payload["latest"]) >= 1


def test_task_store_feedback_range(tmp_path: Path) -> None:
    db = tmp_path / "fdb.sqlite"
    conn = get_connection(db)
    init_schema(conn)
    store = TaskStore(conn)
    tid = store.create_task()
    store.add_human_feedback(tid, 4, "尚可")
    with pytest.raises(ValueError):
        store.add_human_feedback(tid, 6)
    stats = store.feedback_stats(tid)
    assert stats["count"] == 1
    assert stats["avg_1_5"] == 4.0
