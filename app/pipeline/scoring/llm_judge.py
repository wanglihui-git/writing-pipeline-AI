from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from app.pipeline.models import JudgeScores

if TYPE_CHECKING:
    from app.pipeline.llm_protocol import ChatCompletionClient


JUDGE_PROMPT_SYSTEM = """你是独立裁判，只评分不扩写正文。按要求输出单行 JSON：
{"style_similarity_0_100":0-100,"structure_completeness_0_100":0-100,"naturalness_0_100":0-100,"notes":{"style":"","structure":"","naturalness":""}}
不要输出围栏。"""


def parse_judge_json(raw: str) -> JudgeScores:
    s = raw.strip()
    if s.startswith("```"):
        m = re.search(r"\{.*\}", s, flags=re.DOTALL)
        if not m:
            raise ValueError("judge:no_json_found")
        s = m.group(0)
    payload = json.loads(s)
    notes = payload.get("notes")
    rational: dict[str, str] = {}
    if isinstance(notes, dict):
        rational = {str(k): str(v) for k, v in notes.items()}
    return JudgeScores(
        style_similarity_0_100=float(payload["style_similarity_0_100"]),
        structure_completeness_0_100=float(payload["structure_completeness_0_100"]),
        naturalness_0_100=float(payload["naturalness_0_100"]),
        rationales=rational,
    )


def llm_judge_scores(
    article_excerpt: str,
    *,
    outline_summary: str,
    client: ChatCompletionClient | None,
    model_id: str | None,
) -> tuple[JudgeScores | None, str | None]:
    if client is None or not model_id:
        return None, None
    user_prompt = json.dumps({"outline_summary": outline_summary[:8000], "article": article_excerpt[:8000]}, ensure_ascii=False)
    raw = client.complete(
        system_prompt=JUDGE_PROMPT_SYSTEM,
        user_prompt=user_prompt,
        model_id=model_id,
    )
    try:
        score = parse_judge_json(raw)
    except Exception as exc:
        fallback = JudgeScores(
            style_similarity_0_100=52.0,
            structure_completeness_0_100=52.0,
            naturalness_0_100=52.0,
            rationales={"fallback": repr(exc)},
        )
        return fallback, repr(exc)
    return score, None


def fallback_judge_on_error(exc: BaseException | str) -> JudgeScores:
    return JudgeScores(
        style_similarity_0_100=52.0,
        structure_completeness_0_100=52.0,
        naturalness_0_100=52.0,
        rationales={"parse_error": str(exc)},
    )
