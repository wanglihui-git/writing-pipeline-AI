from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.task_store import TaskStore
from app.settings import get_app_config

from .fixtures import sample_brief, seed_ready_task_with_article


def test_partial_section_rewrite(client: TestClient) -> None:
    r = client.post("/tasks/", json={"author": "t", "brief": sample_brief()})
    tid = r.json()["task_id"]
    store = TaskStore(client.app.state.db_conn)
    seed_ready_task_with_article(store, get_app_config(), tid)
    rsp = client.post(
        f"/tasks/{tid}/rewrite/partial",
        json={"instruction": "扩写开场", "section_id": 0, "paragraph_range": None, "apply_context_bridge": False},
    )
    assert rsp.status_code == 200
    body = rsp.json()
    assert body["article_version"] >= 2
    out = store.fetch_latest_article_bundle(tid)
    assert out is not None and "扩写开场" in out.concatenated_polished


def test_partial_paragraph_range_rewrite(client: TestClient) -> None:
    r = client.post("/tasks/", json={"author": "t", "brief": sample_brief()})
    tid = r.json()["task_id"]
    store = TaskStore(client.app.state.db_conn)
    seed_ready_task_with_article(store, get_app_config(), tid)
    rsp = client.post(
        f"/tasks/{tid}/rewrite/partial",
        json={"instruction": "强调论据", "section_id": None, "paragraph_range": [0, 0], "apply_context_bridge": False},
    )
    assert rsp.status_code == 200
    latest = store.fetch_latest_article_bundle(tid)
    assert latest is not None


def test_partial_invalid_range_blocked(client: TestClient) -> None:
    r = client.post("/tasks/", json={"author": "t", "brief": sample_brief()})
    tid = r.json()["task_id"]
    store = TaskStore(client.app.state.db_conn)
    seed_ready_task_with_article(store, get_app_config(), tid)
    rsp = client.post(
        f"/tasks/{tid}/rewrite/partial",
        json={
            "instruction": "noop",
            "section_id": None,
            "paragraph_range": [99, 100],
            "apply_context_bridge": False,
        },
    )
    assert rsp.status_code == 400


def test_partial_both_section_and_range_rejected(client: TestClient) -> None:
    r = client.post("/tasks/", json={"author": "t", "brief": sample_brief()})
    tid = r.json()["task_id"]
    store = TaskStore(client.app.state.db_conn)
    seed_ready_task_with_article(store, get_app_config(), tid)
    rsp = client.post(
        f"/tasks/{tid}/rewrite/partial",
        json={
            "instruction": "noop",
            "section_id": 0,
            "paragraph_range": [0, 0],
            "apply_context_bridge": False,
        },
    )
    assert rsp.status_code == 400
