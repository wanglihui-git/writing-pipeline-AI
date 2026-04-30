from __future__ import annotations

import re
import time

import pytest

from app.pipeline.draft_generator import draft_sections_async, merge_section_bodies
from app.pipeline.models import OutlineDocument, OutlineParagraph, OutlineSection


def _outline_three() -> OutlineDocument:
    return OutlineDocument(
        title="t",
        sections=[
            OutlineSection(
                section_title=f"第{i}章",
                section_goal=f"目标{i}",
                paragraphs=[OutlineParagraph(purpose=f"段{i}", evidence_slots=[f"e{i}"])],
            )
            for i in range(1, 4)
        ],
    )


class _SlowMock:
    finish_order: list[int]

    def __init__(self) -> None:
        self.finish_order = []

    def complete(self, *, system_prompt: str, user_prompt: str, model_id: str) -> str:
        m = re.search(r"章节 (\d+):", user_prompt)
        assert m
        idx = int(m.group(1))
        time.sleep((4 - idx) * 0.02)
        self.finish_order.append(idx)
        return f"SEC{idx}BODY"


@pytest.mark.asyncio
async def test_concurrent_sections_merge_in_order() -> None:
    mock = _SlowMock()
    out = _outline_three()
    pairs = await draft_sections_async(out, mock, model_id="m", topic_hint="主题", max_concurrency=3)
    assert [p[0] for p in pairs] == [0, 1, 2]
    bodies = [p[1] for p in pairs]
    assert bodies == ["SEC1BODY", "SEC2BODY", "SEC3BODY"]
    assert len(set(mock.finish_order)) == 3
    merged = merge_section_bodies(pairs, unify_terms_from={"SEC1": "第一章"})
    assert merged.startswith("第一章BODY")


def test_merge_glossary_order_longest_first() -> None:
    pairs = [(0, "AAAA 与 BBBB"), (1, "细")]
    m = merge_section_bodies(pairs, unify_terms_from={"AAAA": "甲", "BBBB": "乙"})
    assert "甲" in m and "乙" in m
