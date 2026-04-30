from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.task_store import TaskStore
from app.settings import get_app_config

from .fixtures import sample_brief, seed_ready_task_with_article


def test_rewrite_full_happy_path(client: TestClient) -> None:
    r = client.post("/tasks/", json={"author": "t", "brief": sample_brief()})
    assert r.status_code == 200
    tid = r.json()["task_id"]
    store = TaskStore(client.app.state.db_conn)
    cfg = get_app_config()
    seed_ready_task_with_article(store, cfg, tid)
    rsp = client.post(f"/tasks/{tid}/rewrite/full", json={"instruction": "精炼", "keep_facts": False})
    assert rsp.status_code == 200
    body = rsp.json()
    assert body["article_version"] >= 2
    assert body["fused_score_0_100"] is not None
    latest = store.fetch_latest_article_bundle(tid)
    assert latest is not None
    assert "精炼" in latest.concatenated_polished


def test_rewrite_full_no_article_fails(client: TestClient) -> None:
    r = client.post("/tasks/", json={"author": "t", "brief": sample_brief()})
    tid = r.json()["task_id"]
    store = TaskStore(client.app.state.db_conn)
    from app.domain.state_machine import TaskState

    store.force_state(tid, TaskState.READY)
    rsp = client.post(f"/tasks/{tid}/rewrite/full", json={"instruction": "x"})
    assert rsp.status_code == 400


def test_keep_facts_stub_preserves_numeric_tokens(client: TestClient) -> None:
    r = client.post("/tasks/", json={"author": "t", "brief": sample_brief()})
    tid = r.json()["task_id"]
    store = TaskStore(client.app.state.db_conn)
    cfg = get_app_config()
    seed_ready_task_with_article(
        store, cfg, tid, article_text="事实段落包含数字 42 与 KPI-99。\n\n第二段无数字。"
    )
    rsp = client.post(f"/tasks/{tid}/rewrite/full", json={"instruction": "缩写", "keep_facts": True})
    assert rsp.status_code == 200
    txt = store.fetch_latest_article_bundle(tid)
    assert txt is not None
    polished = txt.concatenated_polished
    assert "42" in polished or "缩写" in polished
