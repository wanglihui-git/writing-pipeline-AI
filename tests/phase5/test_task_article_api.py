from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.task_store import TaskStore
from app.settings import get_app_config
from tests.phase4.fixtures import sample_brief, seed_ready_task_with_article


def test_get_latest_article_endpoint(client: TestClient) -> None:
    r = client.post("/tasks/", json={"author": "t", "brief": sample_brief()})
    tid = r.json()["task_id"]
    store = TaskStore(client.app.state.db_conn)
    seed_ready_task_with_article(store, get_app_config(), tid)

    resp = client.get(f"/tasks/{tid}/article/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["task_id"] == tid
    assert body["article_version"] >= 1
    assert body["concatenated_polished"]


def test_get_latest_article_not_found(client: TestClient) -> None:
    resp = client.get("/tasks/00000000-0000-0000-0000-000000000000/article/latest")
    assert resp.status_code == 404
