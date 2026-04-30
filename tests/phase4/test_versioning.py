from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.paths import task_workspace_dir
from app.services.task_store import TaskStore
from app.settings import get_app_config

from .fixtures import sample_brief, seed_ready_task_with_article


def test_article_versions_increment_and_v1_snapshot_read_only(client: TestClient) -> None:
    r = client.post("/tasks/", json={"author": "t", "brief": sample_brief()})
    tid = r.json()["task_id"]
    conn = client.app.state.db_conn
    store = TaskStore(conn)
    cfg = get_app_config()
    seed_ready_task_with_article(store, cfg, tid)
    b1 = store.fetch_article_bundle_version(tid, 1)
    assert b1 is not None
    v1_snap = (task_workspace_dir(cfg, tid) / "article_v1.txt").read_text(encoding="utf-8")

    r2 = client.post(f"/tasks/{tid}/rewrite/full", json={"instruction": "第二波", "keep_facts": False})
    assert r2.status_code == 200
    assert r2.json()["article_version"] == 2
    frozen = Path(task_workspace_dir(cfg, tid) / "article_v1.txt").read_text(encoding="utf-8")
    assert frozen == v1_snap
    assert store.latest_article_version_no(tid) == 2


def test_rewrite_diff_json_written(client: TestClient) -> None:
    r = client.post("/tasks/", json={"author": "t", "brief": sample_brief()})
    tid = r.json()["task_id"]
    store = TaskStore(client.app.state.db_conn)
    cfg = get_app_config()
    seed_ready_task_with_article(store, cfg, tid)
    rsp = client.post(f"/tasks/{tid}/rewrite/full", json={"instruction": "v2", "keep_facts": False})
    assert rsp.status_code == 200
    diff_path = task_workspace_dir(cfg, tid) / "rewrite_diff_v2.json"
    assert diff_path.is_file()
    raw = diff_path.read_text(encoding="utf-8")
    assert '"new_version_no"' in raw
    assert '"rewrite_mode"' in raw
