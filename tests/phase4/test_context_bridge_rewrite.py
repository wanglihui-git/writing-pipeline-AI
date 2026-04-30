from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.task_store import TaskStore
from app.settings import get_app_config

from .fixtures import sample_brief, seed_ready_task_with_article


def test_neighbor_paragraph_bridge_stub(client: TestClient) -> None:
    """局部改写启用衔接；邻段包含衔接标记（stub LLM）。"""
    r = client.post("/tasks/", json={"author": "t", "brief": sample_brief()})
    tid = r.json()["task_id"]
    store = TaskStore(client.app.state.db_conn)
    seed_ready_task_with_article(store, get_app_config(), tid)
    rsp = client.post(
        f"/tasks/{tid}/rewrite/partial",
        json={
            "instruction": "强化转折",
            "section_id": None,
            "paragraph_range": [1, 1],
            "apply_context_bridge": True,
        },
    )
    assert rsp.status_code == 200
    text = store.fetch_latest_article_bundle(tid)
    assert text is not None
    assert "衔接" in text.concatenated_polished
