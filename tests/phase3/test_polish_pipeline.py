from __future__ import annotations

from app.pipeline.polish_pipeline import glossary_unify, inject_logical_bridges_between_paragraph_blocks, polish_with_model


class _Echo:
    def complete(self, *, system_prompt: str, user_prompt: str, model_id: str) -> str:
        return "POLISHED:" + user_prompt[:200]


def test_glossary_unify() -> None:
    t = glossary_unify("使用 WORK 作为术语", {"WORK": "工作流", "使用": "使用"})
    assert "工作流" in t


def test_bridge_injection_increases_blocks() -> None:
    raw = "第一段内容。\n\n第二段内容。\n\n第三段。"
    out = inject_logical_bridges_between_paragraph_blocks(raw)
    assert "衔接" in out
    assert out.count("\n\n") >= raw.count("\n\n")


def test_polish_model_optional() -> None:
    base = "A段\n\nB段"
    out = polish_with_model(base, None, model_id=None, glossary={"A": "甲"}, apply_bridge=False)
    assert "甲" in out
