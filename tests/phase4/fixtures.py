from __future__ import annotations

from app.domain.state_machine import TaskState
from app.pipeline.models import DraftBundle, OutlineDocument, OutlineParagraph, OutlineSection
from app.paths import task_workspace_dir
from app.services.task_store import TaskStore
from app.settings import AppYamlConfig


def sample_brief() -> dict:
    return {
        "topic": "人工智能与写作",
        "angle": "工程实践",
        "thesis": "管线化能提升稳定性",
        "argument_framework": "问题-方案-验证",
        "narrative_skeleton": "起承转合",
        "target_audience": "工程师",
    }


def sample_outline() -> OutlineDocument:
    return OutlineDocument(
        title="测",
        sections=[
            OutlineSection(
                section_title="一、背景",
                section_goal="铺垫",
                paragraphs=[OutlineParagraph(purpose="引子", evidence_slots=[])],
            ),
            OutlineSection(
                section_title="二、方案",
                section_goal="展开",
                paragraphs=[OutlineParagraph(purpose="细节", evidence_slots=[])],
            ),
        ],
    )


def seed_ready_task_with_article(
    store: TaskStore,
    app_cfg: AppYamlConfig,
    task_id: str,
    *,
    article_text: str | None = None,
) -> DraftBundle:
    store.persist_outline_revision(task_id, sample_outline(), model_id="stub")
    store.confirm_outline(task_id)
    bodies = ["第一段落α。\n\n第二段落β。", "第三段落γ。"] if article_text is None else [article_text]
    polished = "\n\n".join(bodies) if article_text is None else article_text
    bundle = DraftBundle(sections_body=bodies, concatenated_raw=polished, concatenated_polished=polished)
    root = task_workspace_dir(app_cfg, task_id)
    store.persist_article_bundle(
        task_id,
        bundle,
        rewrite_mode="seed",
        paragraphs_touched=None,
        artifact_dir=root,
    )
    store.force_state(task_id, TaskState.READY)
    return bundle
