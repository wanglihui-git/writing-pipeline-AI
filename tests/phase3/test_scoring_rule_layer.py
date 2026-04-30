from __future__ import annotations

from app.pipeline.models import ArticleBriefNormalized, OutlineDocument, OutlineParagraph, OutlineSection
from app.pipeline.scoring.rule_layer import compute_rule_scores


def _brief() -> ArticleBriefNormalized:
    return ArticleBriefNormalized(
        topic="人工智能写作",
        angle="产品",
        thesis="需要约束",
        argument_framework="伦理-能力-用户",
        narrative_skeleton="起承转合",
        target_audience="产品经理",
    )


def _outline() -> OutlineDocument:
    return OutlineDocument(
        title="x",
        sections=[
            OutlineSection(
                section_title="人工智能写作",
                section_goal="g",
                paragraphs=[OutlineParagraph(purpose="p", evidence_slots=["e"])],
            ),
        ],
    )


def test_rule_scores_in_range() -> None:
    text = (
        "人工智能写作需要透明。" * 20
        + "\n## 人工智能写作\n"
        + "论证细节与节奏。" * 30
    )
    scores, ev = compute_rule_scores(text, _outline(), _brief())
    assert 0 <= scores.style_similarity_0_100 <= 100
    assert 0 <= scores.structure_completeness_0_100 <= 100
    assert 0 <= scores.naturalness_0_100 <= 100
    assert "style" in ev
