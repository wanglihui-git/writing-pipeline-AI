from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.pipeline.models import OutlineDocument, OutlineSection

if TYPE_CHECKING:
    from app.pipeline.llm_protocol import ChatCompletionClient


def _section_prompt(norm_topic: str, sec: OutlineSection, sec_index: int) -> str:
    lines = [f"# 章节 {sec_index + 1}: {sec.section_title}", f"本章目标：{sec.section_goal}", "段落拆解："]
    for j, p in enumerate(sec.paragraphs):
        lines.append(f"  - [{j}] {p.purpose}；证据占位: {','.join(p.evidence_slots) or '[无]'}" )
    lines.append("\n按要求写本章正文（中文）：保持目标读者口吻，承接叙事骨架命题。" )
    lines.append(f"上下文主题复述：{norm_topic}" )
    return "\n".join(lines)


async def draft_sections_async(
    outline: OutlineDocument,
    client: ChatCompletionClient,
    *,
    model_id: str,
    topic_hint: str,
    max_concurrency: int = 3,
) -> list[tuple[int, str]]:
    """章节 2~4 路并发受限；输出 (顺序索引, 正文)。"""
    if max_concurrency < 1 or max_concurrency > 8:
        raise ValueError("max_concurrency 应在 1..8")

    pairs = list(enumerate(outline.sections))
    sem = asyncio.Semaphore(min(max_concurrency, len(pairs)))

    async def _one(ix: int, sec: OutlineSection) -> tuple[int, str]:
        prompt = _section_prompt(topic_hint, sec, ix)

        async with sem:

            def _call() -> str:
                return client.complete(
                    system_prompt="你是中文长文写手，只输出本章正文 Markdown 小节，不写无关总结。",
                    user_prompt=prompt,
                    model_id=model_id,
                )

            body = await asyncio.to_thread(_call)
            return ix, body.strip()

    results = await asyncio.gather(*(_one(i, s) for i, s in pairs))
    return sorted(results, key=lambda x: x[0])


def merge_section_bodies(indices_bodies: list[tuple[int, str]], *, unify_terms_from: dict[str, str]) -> str:
    """章节后处理：术语表替换 + 轻量段落衔接占位。"""
    parts: list[str] = []
    for _, body in sorted(indices_bodies, key=lambda x: x[0]):
        patched = body
        for k, v in unify_terms_from.items():
            patched = patched.replace(k, v)
        parts.append(patched.strip())
    return "\n\n".join(parts)
