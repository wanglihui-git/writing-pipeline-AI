from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.pipeline.models import ArticleBriefNormalized, OutlineDocument

if TYPE_CHECKING:
    from app.pipeline.llm_protocol import ChatCompletionClient


OUTLINE_SYSTEM_PROMPT = """你是长文写作大纲编辑。只输出 JSON（无 Markdown 围栏），结构必须满足 schema：
{
  "title": "...",
  "sections": [
    {
      "section_title": "...",
      "section_goal": "...",
      "paragraphs": [
        { "purpose": "...", "evidence_slots": ["..."] }
      ]
    }
  ],
  "closing_notes": "..."
}
每个 section 至少一段；每段至少 one evidence_slot（可为占位符）。"""


def _user_prompt(req: ArticleBriefNormalized) -> str:
    return json.dumps(
        {
            "选题": req.topic,
            "切入角度": req.angle,
            "核心命题": req.thesis,
            "论证框架": req.argument_framework,
            "叙事骨架": req.narrative_skeleton,
            "目标读者": req.target_audience,
            "目标字数": req.target_word_count,
            "风格强度": req.style_intensity,
            "语气偏好": req.tone_preference,
        },
        ensure_ascii=False,
    )


def _strip_md_json_fence(raw: str) -> str:
    s = raw.strip()
    if not s.startswith("```"):
        return s
    body = s.split("\n", 1)[-1] if "\n" in s else s[3:]
    if "```" in body:
        body = body.split("```", 1)[0]
    return body.strip()


def generate_outline(
    req: ArticleBriefNormalized,
    client: ChatCompletionClient,
    *,
    model_id: str,
) -> OutlineDocument:
    raw = client.complete(
        system_prompt=OUTLINE_SYSTEM_PROMPT,
        user_prompt=_user_prompt(req),
        model_id=model_id,
    )
    raw = _strip_md_json_fence(raw)
    return OutlineDocument.model_validate_json(raw)


def validate_outline_structure(out: OutlineDocument) -> None:
    """显式校验大纲业务完整性（章节/段落目标/证据位）。"""
    if not out.sections:
        raise ValueError("大纲缺少章节")
    for s in out.sections:
        if not s.section_goal.strip():
            raise ValueError(f"章节无目标: {s.section_title}")
        if not s.paragraphs:
            raise ValueError(f"章节无段落: {s.section_title}")
        for p in s.paragraphs:
            if not p.purpose.strip():
                raise ValueError(f"段落无目的 under {s.section_title}")
            if not p.evidence_slots:
                raise ValueError(f"段落缺少证据占位 under {s.section_title}")
