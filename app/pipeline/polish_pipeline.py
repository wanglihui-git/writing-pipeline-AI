from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.pipeline.llm_protocol import ChatCompletionClient


_TEMPLATE_BRIDGE = "\n（衔接）：保持语气一致，回扣核心命题。\n"


def glossary_unify(text: str, glossary: dict[str, str]) -> str:
    t = text
    for raw, canon in sorted(glossary.items(), key=lambda x: -len(x[0])):
        t = t.replace(raw, canon)
    return t


def inject_logical_bridges_between_paragraph_blocks(text: str) -> str:
    """在长段之间追加轻衔接句（占位实现，可被 polish_model 覆盖）。"""
    blocks = re.split(r"\n{2,}", text.strip())
    if len(blocks) < 2:
        return text
    out = [blocks[0]]
    for b in blocks[1:]:
        out.append(_TEMPLATE_BRIDGE.strip())
        out.append(b)
    return "\n\n".join(out)


def polish_with_model(
    text: str,
    client: ChatCompletionClient | None,
    *,
    model_id: str | None,
    glossary: dict[str, str] | None = None,
    apply_bridge: bool = True,
) -> str:
    base = glossary_unify(text, glossary or {})
    if apply_bridge:
        base = inject_logical_bridges_between_paragraph_blocks(base)
    if client is None or not model_id:
        return base
    return client.complete(
        system_prompt=(
            "你是中文润色编辑，保持事实与论点不变。"
            "要求：术语与前后章节一致；减少模板连接词堆砌；段落过渡自然。"
            "输出润色后的全文。"
        ),
        user_prompt=base[:120_000],
        model_id=model_id,
    ).strip()
