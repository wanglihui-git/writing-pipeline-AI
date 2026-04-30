from __future__ import annotations

from app.pipeline.models import JudgeScores


W_STYLE = 0.40
W_STRUCT = 0.35
W_NATURAL = 0.25


def fuse_three_dimensions(scores: JudgeScores) -> float:
    """技术方案三层综合：风格 40% / 结构 35% / 自然度 25%，输出 0~100。"""
    total = (
        W_STYLE * scores.style_similarity_0_100
        + W_STRUCT * scores.structure_completeness_0_100
        + W_NATURAL * scores.naturalness_0_100
    )
    return round(max(0.0, min(100.0, total)), 3)


def blend_dimension(rule_val: float, llm_val: float, *, rule_alpha: float) -> float:
    """单维度上将规则与 LLM 对齐；rule_alpha ∈ [0,1]。"""
    return float(max(0.0, min(100.0, rule_alpha * rule_val + (1.0 - rule_alpha) * llm_val)))


def fuse_rule_and_llm(
    rule: JudgeScores,
    llm: JudgeScores | None,
    *,
    rule_alpha: float = 0.45,
) -> tuple[JudgeScores, float, dict]:
    """
    先维度线性混合规则分与裁判分（可选），再走 40/35/25 综合；
    无 LLM 时混合层退化为 rule。
    """
    if llm is None:
        total = fuse_three_dimensions(rule)
        return rule, total, {}
    blended = JudgeScores(
        style_similarity_0_100=blend_dimension(rule.style_similarity_0_100, llm.style_similarity_0_100, rule_alpha=rule_alpha),
        structure_completeness_0_100=blend_dimension(
            rule.structure_completeness_0_100, llm.structure_completeness_0_100, rule_alpha=rule_alpha
        ),
        naturalness_0_100=blend_dimension(rule.naturalness_0_100, llm.naturalness_0_100, rule_alpha=rule_alpha),
        rationales={"blend_rule_alpha": str(rule_alpha)},
    )
    total = fuse_three_dimensions(blended)
    return blended, total, {"rule": rule.model_dump(), "llm_raw": llm.model_dump(), "blended_dims": blended.model_dump()}
