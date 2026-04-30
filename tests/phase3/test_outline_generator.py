from __future__ import annotations

import json

import pytest

from app.pipeline.models import ArticleBriefNormalized, OutlineDocument
from app.pipeline.outline_generator import generate_outline, validate_outline_structure


class _CapClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.last_model_id: str | None = None

    def complete(self, *, system_prompt: str, user_prompt: str, model_id: str) -> str:
        self.last_model_id = model_id
        return json.dumps(self.payload, ensure_ascii=False)


def _sample_payload() -> dict:
    return {
        "title": "测试标题",
        "sections": [
            {
                "section_title": "一、背景",
                "section_goal": "建立语境",
                "paragraphs": [
                    {"purpose": "交代问题", "evidence_slots": ["数据1"]},
                    {"purpose": "界定范围", "evidence_slots": ["引用A"]},
                ],
            },
            {
                "section_title": "二、展开",
                "section_goal": "论证主张",
                "paragraphs": [{"purpose": "提出论点", "evidence_slots": ["案例1"]}],
            },
        ],
        "closing_notes": "收束",
    }


def test_outline_structure_complete() -> None:
    req = ArticleBriefNormalized(
        topic="t",
        angle="a",
        thesis="th",
        argument_framework="af",
        narrative_skeleton="ns",
        target_audience="r",
    )
    client = _CapClient(_sample_payload())
    out = generate_outline(req, client, model_id="m-a")
    validate_outline_structure(out)
    assert out.title == "测试标题"
    assert len(out.sections) == 2
    assert out.flatten_evidence_placeholder_count() >= 3


def test_model_id_passed_through() -> None:
    req = ArticleBriefNormalized(
        topic="t",
        angle="a",
        thesis="th",
        argument_framework="af",
        narrative_skeleton="ns",
        target_audience="r",
    )
    client = _CapClient(_sample_payload())
    generate_outline(req, client, model_id="qwen-special")
    assert client.last_model_id == "qwen-special"


def test_json_fence_strip() -> None:
    class _Fence:
        def complete(self, *, system_prompt: str, user_prompt: str, model_id: str) -> str:
            return "```json\n" + json.dumps(_sample_payload()) + "\n```"

    req = ArticleBriefNormalized(
        topic="t",
        angle="a",
        thesis="th",
        argument_framework="af",
        narrative_skeleton="ns",
        target_audience="r",
    )
    out = generate_outline(req, _Fence(), model_id="m")
    assert out.title == "测试标题"


def test_validate_rejects_empty_sections() -> None:
    empty = OutlineDocument(title="x", sections=[])
    with pytest.raises(ValueError, match="缺少章节"):
        validate_outline_structure(empty)
