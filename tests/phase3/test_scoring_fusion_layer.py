from __future__ import annotations

import pytest

from app.pipeline.models import JudgeScores
from app.pipeline.scoring.fusion_layer import blend_dimension, fuse_rule_and_llm, fuse_three_dimensions


def test_fixed_weight_fusion_formula() -> None:
    js = JudgeScores(
        style_similarity_0_100=80.0,
        structure_completeness_0_100=60.0,
        naturalness_0_100=40.0,
    )
    total = fuse_three_dimensions(js)
    assert total == pytest.approx(0.4 * 80 + 0.35 * 60 + 0.25 * 40)


def test_blend_then_fuse_changes_total() -> None:
    rule = JudgeScores(style_similarity_0_100=50, structure_completeness_0_100=50, naturalness_0_100=50)
    llm = JudgeScores(style_similarity_0_100=90, structure_completeness_0_100=90, naturalness_0_100=90)
    blended, total, dbg = fuse_rule_and_llm(rule, llm, rule_alpha=0.0)
    assert total == fuse_three_dimensions(llm)
    assert blended.style_similarity_0_100 == pytest.approx(90.0)
    assert "blended_dims" in dbg
    blended2, total2, _ = fuse_rule_and_llm(rule, llm, rule_alpha=1.0)
    assert total2 == fuse_three_dimensions(rule)
    assert blend_dimension(0, 100, rule_alpha=0.5) == 50.0
