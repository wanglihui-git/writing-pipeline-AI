"""Phase 5 集成/冒烟用的小型夹具（避免与本仓库测试包导入顺序纠缠）。"""

from __future__ import annotations

from app.pipeline.models import OutlineDocument, OutlineParagraph, OutlineSection


def minimal_brief() -> dict[str, object]:
    return {
        "topic": "端到端链路",
        "angle": "验证",
        "thesis": "管线可连通",
        "argument_framework": "总-分-总",
        "narrative_skeleton": "递进",
        "target_audience": "维护者",
    }


def minimal_outline() -> OutlineDocument:
    return OutlineDocument(
        title="集成测",
        sections=[
            OutlineSection(
                section_title="一、背景",
                section_goal="交代问题",
                paragraphs=[OutlineParagraph(purpose="简述", evidence_slots=[])],
            ),
        ],
    )
