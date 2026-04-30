from __future__ import annotations

from app.pipeline.scoring.llm_judge import fallback_judge_on_error, llm_judge_scores, parse_judge_json


def test_parse_valid_judge_json() -> None:
    raw = '{"style_similarity_0_100":70,"structure_completeness_0_100":65,"naturalness_0_100":80,"notes":{"style":"ok"}}'
    j = parse_judge_json(raw)
    assert j.style_similarity_0_100 == 70
    assert "style" in j.rationales


def test_parse_malformed_uses_fallback_path() -> None:
    fb, err = llm_judge_scores("x", outline_summary="", client=_BadJudge(), model_id="j")
    assert fb is not None
    assert err is not None
    assert fb.naturalness_0_100 == 52.0


class _BadJudge:
    def complete(self, *, system_prompt: str, user_prompt: str, model_id: str) -> str:
        return "not-json"


class _GoodJudge:
    def complete(self, *, system_prompt: str, user_prompt: str, model_id: str) -> str:
        return '{"style_similarity_0_100":71,"structure_completeness_0_100":72,"naturalness_0_100":73,"notes":{}}'


def test_llm_success_no_error() -> None:
    fb, err = llm_judge_scores("正文", outline_summary="摘要", client=_GoodJudge(), model_id="j")
    assert err is None
    assert fb is not None and fb.style_similarity_0_100 == 71


def test_fallback_constant() -> None:
    fb = fallback_judge_on_error("boom")
    assert fb.structure_completeness_0_100 == 52.0
