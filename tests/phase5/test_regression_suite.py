from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domain.state_machine import TaskState, assert_transition
from app.feishu.router import parse_command_text
from app.paths import task_workspace_dir
from app.pipeline.models import DraftBundle, ScoreCard
from app.pipeline.request_normalizer import normalize_article_brief
from app.pipeline.scoring.fusion_layer import fuse_rule_and_llm
from app.pipeline.scoring.rule_layer import compute_rule_scores
from app.services.task_store import TaskStore
from app.settings import get_app_config

from .helpers import minimal_brief, minimal_outline


def test_health_echo(client: TestClient) -> None:
    assert client.get("/health").status_code == 200


def test_phase1_style_task_roundtrip(client: TestClient) -> None:
    r = client.post("/tasks/", json={"author": "reg", "brief": {"topic": "x"}})
    assert r.status_code == 200 and "task_id" in r.json()
    tid = r.json()["task_id"]
    g = client.get(f"/tasks/{tid}")
    assert g.status_code == 200


def test_state_machine_core_transition() -> None:
    assert_transition(TaskState.RECEIVED, TaskState.OUTLINE_GENERATING)


def test_feishu_command_parse_outline() -> None:
    cmd = parse_command_text("/outline author=Lia topic=z")
    assert cmd.name == "outline"


@pytest.mark.manual_gate
def test_mvp_human_quality_gate_placeholder() -> None:
    """Phase 5 主观验收：在线下检查表填写；CI 不测人工「像」与 AI味。"""
    pytest.skip(
        "人工：主观「像」>=4、AI味可接受、结构完整率线下统计；不参与自动化 CI"
    )


def test_integration_stub_outline_score_rewrite_web(client: TestClient) -> None:
    """
    轻量化「飞书/task -> 大纲(落库) -> 正文占位 -> 规则评分 -> REST 改写」闭环。
    真实 LLM 与飞书网关不在 CI 激活，此用例锁住文件与路由契约。
    """
    rsp = client.post("/tasks/", json={"author": "int", "brief": minimal_brief()})
    tid = rsp.json()["task_id"]
    conn = client.app.state.db_conn
    store = TaskStore(conn)
    cfg = get_app_config()
    outline = minimal_outline()

    store.persist_outline_revision(tid, outline, model_id="stub")
    store.confirm_outline(tid)

    polished = "## 集成\n端到端链路正文第一段。\n\n第二段补充论据。\n\n"
    bundle = DraftBundle(sections_body=[polished], concatenated_raw=polished, concatenated_polished=polished)
    root = task_workspace_dir(cfg, tid)
    store.persist_article_bundle(tid, bundle, rewrite_mode="integration_stub", paragraphs_touched=None, artifact_dir=root)

    row = conn.execute(
        "SELECT id FROM task_versions WHERE task_id=? AND kind=? ORDER BY version_no DESC LIMIT 1",
        (tid, "article"),
    ).fetchone()
    assert row
    brief_norm = normalize_article_brief(store.get_task(tid).brief, app_defaults=cfg)
    rule, expl = compute_rule_scores(polished, outline, brief_norm)
    _, fused, bd = fuse_rule_and_llm(rule, llm=None)
    card = ScoreCard(rule_scores=rule, fused_total_0_100=fused, fused_breakdown=bd, explanations=expl)
    store.persist_score_card(tid, task_version_id=int(row["id"]), card=card)

    store.force_state(tid, TaskState.READY)
    rw = client.post(f"/tasks/{tid}/rewrite/full", json={"instruction": "润色收口", "keep_facts": False})
    assert rw.status_code == 200
    latest = store.fetch_latest_article_bundle(tid)
    assert latest is not None and "润色收口" in latest.concatenated_polished
    scores_n = conn.execute("SELECT COUNT(*) AS c FROM scores WHERE task_id=?", (tid,)).fetchone()["c"]
    assert scores_n >= 2
