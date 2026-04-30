from __future__ import annotations

import asyncio
import json
import logging

from app.corpus.author_profile import build_author_profile
from app.corpus.chroma_index import ChromaCorpusIndex
from app.corpus.embeddings import DeterministicHashEmbedding
from app.corpus.ingest_pipeline import index_author_from_raw_dir
from app.db.sqlite_schema import get_connection, init_schema
from app.domain.state_machine import TaskState
from app.feishu.status_push import push_generation_percent, push_task_phase
from app.pipeline.client_factory import get_default_chat_client
from app.pipeline.draft_generator import draft_sections_async, merge_section_bodies
from app.pipeline.models import DraftBundle, OutlineDocument, OutlineParagraph, OutlineSection, ScoreCard
from app.pipeline.outline_generator import generate_outline, validate_outline_structure
from app.pipeline.polish_pipeline import polish_with_model
from app.pipeline.request_normalizer import normalize_article_brief
from app.pipeline.scoring.fusion_layer import fuse_rule_and_llm
from app.pipeline.scoring.llm_judge import llm_judge_scores
from app.pipeline.scoring.rule_layer import compute_rule_scores
from app.paths import chroma_root_path, corpus_clean_root, corpus_raw_root, task_workspace_dir
from app.services.task_store import TaskStore
from app.settings import get_app_config, get_models_config

logger = logging.getLogger(__name__)


def _fallback_outline_from_task(task_id: str, brief: dict) -> OutlineDocument:
    topic = str(brief.get("topic") or brief.get("选题") or "待补充选题")
    return OutlineDocument(
        title=f"{topic}（自动占位大纲）",
        sections=[
            OutlineSection(
                section_title="一、问题定义",
                section_goal="明确核心议题与读者关切",
                paragraphs=[OutlineParagraph(purpose="给出问题背景与边界", evidence_slots=[f"task:{task_id}:e1"])],
            ),
            OutlineSection(
                section_title="二、论证展开",
                section_goal="给出关键论据与方法路径",
                paragraphs=[OutlineParagraph(purpose="分点展开核心论证", evidence_slots=[f"task:{task_id}:e2"])],
            ),
            OutlineSection(
                section_title="三、结论与行动",
                section_goal="收束观点并给出可执行建议",
                paragraphs=[OutlineParagraph(purpose="总结并提出下一步", evidence_slots=[f"task:{task_id}:e3"])],
            ),
        ],
        closing_notes="该大纲为系统自动生成，可在确认前继续修订。",
    )


def _fallback_draft_from_outline(outline: OutlineDocument, topic: str) -> str:
    blocks: list[str] = []
    for sec in outline.sections:
        blocks.append(f"## {sec.section_title}\n\n{sec.section_goal}\n\n围绕“{topic}”展开论证。")
    return "\n\n".join(blocks)


def _score_article(
    article: str,
    *,
    outline: OutlineDocument,
    req,
    client,
    judge_model_id: str,
) -> ScoreCard:
    rule_scores, explanations = compute_rule_scores(article, outline, req)
    llm_scores, llm_err = llm_judge_scores(
        article,
        outline_summary=outline.model_dump_json()[:8000],
        client=client,
        model_id=judge_model_id,
    )
    _, fused, fused_breakdown = fuse_rule_and_llm(rule_scores, llm=llm_scores, rule_alpha=0.45)
    if llm_err:
        explanations["llm_judge_error"] = llm_err
    return ScoreCard(
        rule_scores=rule_scores,
        llm_scores=llm_scores,
        fused_total_0_100=fused,
        fused_breakdown=fused_breakdown,
        explanations=explanations,
    )


def _update_corpus_job(conn, job_id: str, *, status: str, payload: dict | None = None) -> None:
    payload = payload or {}
    conn.execute(
        """
        UPDATE corpus_jobs
        SET status = ?,
            files_found = COALESCE(?, files_found),
            files_processed = COALESCE(?, files_processed),
            chunks_indexed = COALESCE(?, chunks_indexed),
            skipped_json = COALESCE(?, skipped_json),
            profile_json = COALESCE(?, profile_json),
            error_message = COALESCE(?, error_message),
            updated_at = datetime('now')
        WHERE job_id = ?
        """,
        (
            status,
            payload.get("files_found"),
            payload.get("files_processed"),
            payload.get("chunks_indexed"),
            payload.get("skipped_json"),
            payload.get("profile_json"),
            payload.get("error_message"),
            job_id,
        ),
    )
    conn.commit()


def process_received_task(task_id: str, sqlite_path: str) -> str:
    conn = get_connection(sqlite_path)
    init_schema(conn)
    store = TaskStore(conn)
    rec = store.get_task(task_id)
    cid = rec.feishu_chat_id if rec else None
    push_task_phase(cid, task_id, "大纲生成", "状态：OUTLINE_GENERATING")
    push_generation_percent(cid, task_id, 12.0)
    store.set_state(task_id, TaskState.OUTLINE_GENERATING)

    cfg_models = get_models_config()
    outline_model_id = cfg_models.outline_model
    client = get_default_chat_client()
    outline: OutlineDocument | None = None
    used_model = "local-fallback"
    try:
        if rec is None:
            raise KeyError(task_id)
        req = normalize_article_brief(rec.brief, app_defaults=get_app_config())
        if client is not None:
            outline = generate_outline(req, client, model_id=outline_model_id)
            validate_outline_structure(outline)
            used_model = outline_model_id
        else:
            outline = _fallback_outline_from_task(task_id, rec.brief)
    except Exception as exc:
        logger.warning("outline generation degraded for %s: %s", task_id, exc)
        outline = _fallback_outline_from_task(task_id, rec.brief if rec else {})
        used_model = "local-fallback"

    push_generation_percent(cid, task_id, 45.0)
    store.persist_outline_revision(task_id, outline, model_id=used_model)
    push_task_phase(cid, task_id, "大纲生成", "等待确认（WAIT_OUTLINE_CONFIRM）")
    store.set_state(task_id, TaskState.WAIT_OUTLINE_CONFIRM)
    push_generation_percent(cid, task_id, 100.0)
    logger.info("task %s reached WAIT_OUTLINE_CONFIRM", task_id)
    return task_id


def process_generate_task(task_id: str, sqlite_path: str) -> str:
    conn = get_connection(sqlite_path)
    init_schema(conn)
    store = TaskStore(conn)
    rec = store.get_task(task_id)
    if rec is None:
        raise KeyError(task_id)
    cid = rec.feishu_chat_id
    cfg = get_app_config()
    models = get_models_config()
    client = get_default_chat_client()

    if not rec.outline_confirmed:
        raise ValueError("outline not confirmed")
    outline = store.fetch_latest_outline_document(task_id)
    if outline is None:
        raise ValueError("outline missing")
    req = normalize_article_brief(rec.brief, app_defaults=cfg)

    push_task_phase(cid, task_id, "正文生成", "状态：DRAFT_GENERATING")
    store.set_state(task_id, TaskState.DRAFT_GENERATING)
    push_generation_percent(cid, task_id, 20.0)

    try:
        if client is not None:
            sections = asyncio.run(
                draft_sections_async(
                    outline,
                    client,
                    model_id=models.draft_model,
                    topic_hint=req.topic,
                    max_concurrency=3,
                )
            )
            raw = merge_section_bodies(sections, unify_terms_from={})
            sections_body = [body for _, body in sorted(sections, key=lambda x: x[0])]
        else:
            raw = _fallback_draft_from_outline(outline, req.topic)
            sections_body = [raw]

        push_generation_percent(cid, task_id, 60.0)
        polished = polish_with_model(raw, client, model_id=models.polish_model, glossary=None, apply_bridge=True)
        bundle = DraftBundle(sections_body=sections_body, concatenated_raw=raw, concatenated_polished=polished)
        artifact_dir = task_workspace_dir(cfg, task_id)
        _, version_id = store.persist_article_bundle(
            task_id,
            bundle,
            rewrite_mode="initial_generate",
            paragraphs_touched=None,
            artifact_dir=artifact_dir,
        )

        push_task_phase(cid, task_id, "评分", "状态：SCORING")
        store.set_state(task_id, TaskState.SCORING)
        card = _score_article(
            polished,
            outline=outline,
            req=req,
            client=client,
            judge_model_id=models.judge_model,
        )
        store.persist_score_card(task_id, task_version_id=version_id, card=card)
        store.set_state(task_id, TaskState.READY)
        push_generation_percent(cid, task_id, 100.0)
        push_task_phase(cid, task_id, "完成", "正文与评分已完成")
        return task_id
    except Exception:
        store.force_state(task_id, TaskState.FAILED)
        logger.exception("generate task failed: %s", task_id)
        raise


def process_corpus_ingest(job_id: str, author_slug: str, sqlite_path: str) -> str:
    cfg = get_app_config()
    conn = get_connection(sqlite_path)
    init_schema(conn)
    _update_corpus_job(conn, job_id, status="RUNNING")
    try:
        chroma = ChromaCorpusIndex(chroma_root_path(cfg), DeterministicHashEmbedding())
        summary = index_author_from_raw_dir(
            conn,
            chroma,
            author_slug=author_slug,
            raw_root=corpus_raw_root(cfg),
            clean_root=corpus_clean_root(cfg),
            chunk_cfg=cfg.chunk,
        )
        profile = build_author_profile(conn, author_slug)
        _update_corpus_job(
            conn,
            job_id,
            status="SUCCEEDED",
            payload={
                "files_found": int(summary.get("files_found", 0)),
                "files_processed": int(summary.get("files_processed", 0)),
                "chunks_indexed": int(summary.get("chunks_indexed", 0)),
                "skipped_json": json.dumps(summary.get("skipped", []), ensure_ascii=False),
                "profile_json": json.dumps(profile, ensure_ascii=False),
            },
        )
        return job_id
    except Exception as exc:
        _update_corpus_job(
            conn,
            job_id,
            status="FAILED",
            payload={"error_message": str(exc)},
        )
        logger.exception("corpus ingest failed job=%s author=%s", job_id, author_slug)
        raise


def flaky_demo_task() -> str:
    """历史测试兼容：执行即失败。"""
    raise RuntimeError("expected failure for tests")
