from __future__ import annotations

import time

import pytest

from app.pipeline.draft_generator import draft_sections_async
from app.pipeline.models import JudgeScores, OutlineDocument, OutlineParagraph, OutlineSection
from app.pipeline.request_normalizer import normalize_article_brief
from app.pipeline.rewrite_service import split_paragraphs
from app.pipeline.scoring.fusion_layer import fuse_three_dimensions


def test_split_paragraphs_large_document_under_budget() -> None:
    body = ("\n\n".join(f"段落{n}：" + ("字" * 80) for n in range(400))).encode().decode()
    t0 = time.perf_counter()
    paras = split_paragraphs(body)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert len(paras) == 400
    assert elapsed_ms < 350.0, f"too slow: {elapsed_ms:.1f}ms"


def test_normalize_brief_and_fuse_dimensions_fast() -> None:
    brief = normalize_article_brief(
        {"topic": "t", "angle": "a", "thesis": "th", "argument_framework": "af", "narrative_skeleton": "ns", "target_audience": "rd"},
    )
    assert brief.topic == "t"
    t0 = time.perf_counter()
    for _ in range(300):
        s = fuse_three_dimensions(
            JudgeScores(
                style_similarity_0_100=80.0,
                structure_completeness_0_100=77.0,
                naturalness_0_100=73.0,
            )
        )
        assert s > 0
    assert (time.perf_counter() - t0) * 1000 < 120.0


@pytest.mark.asyncio
async def test_draft_sections_stub_parallel_under_budget() -> None:
    outline = OutlineDocument(
        title="快测",
        sections=[
            OutlineSection(
                section_title=f"§{k}",
                section_goal="目标",
                paragraphs=[OutlineParagraph(purpose="写", evidence_slots=[])],
            )
            for k in range(6)
        ],
    )

    class StubClient:
        def complete(self, **kwargs: object) -> str:
            return "占位正文块\n\n第二段."

    t0 = time.perf_counter()
    pairs = await draft_sections_async(outline, StubClient(), model_id="stub", topic_hint="demo", max_concurrency=3)
    elapsed = time.perf_counter() - t0
    assert len(pairs) == 6
    assert elapsed < 3.5, f"stub 并发草稿过慢：{elapsed:.2f}s"
