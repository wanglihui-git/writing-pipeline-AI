from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError

from app.domain.pipeline_errors import categorize_pipeline_exception
from app.domain.state_machine import TaskState
from app.feishu.status_push import push_generation_percent, push_task_phase
from app.paths import task_workspace_dir
from app.pipeline.client_factory import get_default_chat_client
from app.pipeline.models import ArticleBriefNormalized, DraftBundle, OutlineDocument, ScoreCard
from app.pipeline.request_normalizer import normalize_article_brief
from app.pipeline.rewrite_service import (
    rewrite_full_text,
    rewrite_partial_by_paragraph_range,
    rewrite_partial_by_section,
    split_paragraphs,
)
from app.pipeline.scoring.fusion_layer import fuse_rule_and_llm
from app.pipeline.scoring.llm_judge import llm_judge_scores
from app.pipeline.scoring.rule_layer import compute_rule_scores
from app.services.task_store import TaskStore
from app.settings import AppYamlConfig, get_models_config

if TYPE_CHECKING:
    from app.pipeline.llm_protocol import ChatCompletionClient

logger = logging.getLogger(__name__)


def _score_after_rewrite(
    text: str,
    outline: OutlineDocument,
    brief: ArticleBriefNormalized,
    *,
    client: ChatCompletionClient | None,
    judge_model_id: str | None,
) -> ScoreCard:
    rule, explanations = compute_rule_scores(text, outline, brief)
    llm_score, llm_err = llm_judge_scores(
        text,
        outline_summary=outline.model_dump_json()[:8000],
        client=client,
        model_id=judge_model_id,
    )
    blended, fused, fused_breakdown = fuse_rule_and_llm(rule, llm=llm_score, rule_alpha=0.45)
    if llm_err:
        explanations["llm_judge_error"] = llm_err
    return ScoreCard(
        rule_scores=rule,
        llm_scores=llm_score,
        fused_total_0_100=fused,
        fused_breakdown=fused_breakdown,
        explanations=explanations,
    )


def run_full_rewrite(
    store: TaskStore,
    app_cfg: AppYamlConfig,
    task_id: str,
    *,
    instruction: str,
    keep_facts: bool,
    client: ChatCompletionClient | None = None,
    model_id: str | None = None,
) -> tuple[int, ScoreCard]:
    rec = store.get_task(task_id)
    if rec is None:
        raise KeyError(task_id)
    if rec.state != TaskState.READY:
        raise ValueError(f"task must be READY for rewrite, got {rec.state}")
    bundle = store.fetch_latest_article_bundle(task_id)
    if bundle is None:
        raise ValueError("no article snapshot for task")
    outline = store.fetch_latest_outline_document(task_id)
    if outline is None:
        raise ValueError("outline required for rescoring")

    cid = rec.feishu_chat_id

    push_task_phase(cid, task_id, "改写", "全文改写开始")
    cfg_models = get_models_config()
    effective_client = client or get_default_chat_client()
    effective_rewrite_model = model_id or cfg_models.polish_model

    store.set_state(task_id, TaskState.REWRITING)
    try:
        new_text = rewrite_full_text(
            bundle.concatenated_polished,
            instruction=instruction,
            keep_facts=keep_facts,
            client=effective_client,
            model_id=effective_rewrite_model,
        )
        new_bundle = DraftBundle(
            sections_body=[new_text],
            concatenated_raw=new_text,
            concatenated_polished=new_text,
        )
        artifact_root = task_workspace_dir(app_cfg, task_id)
        v_no, vid = store.persist_article_bundle(
            task_id,
            new_bundle,
            rewrite_mode="full",
            paragraphs_touched=None,
            artifact_dir=artifact_root,
        )
        try:
            brief = normalize_article_brief(rec.brief, app_defaults=app_cfg)
        except ValidationError as e:
            raise ValueError("task brief incompatible with scorer") from e

        push_task_phase(cid, task_id, "评分", f"改写版本 v{v_no} 已落库")
        push_generation_percent(cid, task_id, 62.5)
        push_generation_percent(cid, task_id, 100.0)

        store.set_state(task_id, TaskState.SCORING)
        card = _score_after_rewrite(
            new_bundle.concatenated_polished,
            outline,
            brief,
            client=effective_client,
            judge_model_id=cfg_models.judge_model,
        )
        store.persist_score_card(task_id, task_version_id=vid, card=card)
        store.set_state(task_id, TaskState.READY)
        return v_no, card
    except Exception as exc:
        logger.exception(
            "full rewrite failed for %s classified=%s",
            task_id,
            categorize_pipeline_exception(exc),
        )
        store.force_state(task_id, TaskState.FAILED)
        raise


def run_partial_rewrite(
    store: TaskStore,
    app_cfg: AppYamlConfig,
    task_id: str,
    *,
    instruction: str,
    section_id: int | None,
    paragraph_range: tuple[int, int] | None,
    apply_context_bridge: bool,
    client: ChatCompletionClient | None = None,
    model_id: str | None = None,
) -> tuple[int, ScoreCard]:
    if (section_id is None) == (paragraph_range is None):
        raise ValueError("specify exactly one of section_id or paragraph_range")

    rec = store.get_task(task_id)
    if rec is None:
        raise KeyError(task_id)
    if rec.state != TaskState.READY:
        raise ValueError(f"task must be READY for rewrite, got {rec.state}")
    bundle = store.fetch_latest_article_bundle(task_id)
    if bundle is None:
        raise ValueError("no article snapshot for task")
    outline = store.fetch_latest_outline_document(task_id)
    if outline is None:
        raise ValueError("outline required for rescoring")

    if section_id is not None:
        if section_id < 0 or section_id >= len(bundle.sections_body):
            raise ValueError("invalid section_id")
    elif paragraph_range is not None:
        paras = split_paragraphs(bundle.concatenated_polished)
        lo, hi = paragraph_range
        if lo < 0 or hi >= len(paras) or lo > hi:
            raise ValueError("invalid paragraph_range")

    cid = rec.feishu_chat_id

    push_task_phase(cid, task_id, "改写", "局部改写进行中")
    cfg_models = get_models_config()
    effective_client = client or get_default_chat_client()
    effective_rewrite_model = model_id or cfg_models.polish_model

    store.set_state(task_id, TaskState.REWRITING)
    try:
        touched: list[int]
        if section_id is not None:
            new_bundle, touched = rewrite_partial_by_section(
                bundle,
                section_id=section_id,
                instruction=instruction,
                apply_bridge=apply_context_bridge,
                client=effective_client,
                model_id=effective_rewrite_model,
            )
            mode = "partial_section"
        else:
            assert paragraph_range is not None
            new_bundle, touched = rewrite_partial_by_paragraph_range(
                bundle,
                paragraph_range=paragraph_range,
                instruction=instruction,
                apply_bridge=apply_context_bridge,
                client=effective_client,
                model_id=effective_rewrite_model,
            )
            mode = "partial_paragraph_range"

        artifact_root = task_workspace_dir(app_cfg, task_id)
        v_no, vid = store.persist_article_bundle(
            task_id,
            new_bundle,
            rewrite_mode=mode,
            paragraphs_touched=touched,
            artifact_dir=artifact_root,
        )
        try:
            brief = normalize_article_brief(rec.brief, app_defaults=app_cfg)
        except ValidationError as e:
            raise ValueError("task brief incompatible with scorer") from e

        store.set_state(task_id, TaskState.SCORING)
        card = _score_after_rewrite(
            new_bundle.concatenated_polished,
            outline,
            brief,
            client=effective_client,
            judge_model_id=cfg_models.judge_model,
        )
        store.persist_score_card(task_id, task_version_id=vid, card=card)
        push_task_phase(cid, task_id, "完成", f"局部改写 v{v_no} · 段落索引 {touched[:8]}...")
        store.set_state(task_id, TaskState.READY)
        return v_no, card
    except Exception as exc:
        logger.exception(
            "partial rewrite failed for %s classified=%s",
            task_id,
            categorize_pipeline_exception(exc),
        )
        store.force_state(task_id, TaskState.FAILED)
        raise
