from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.pipeline.models import DraftBundle

if TYPE_CHECKING:
    from app.pipeline.llm_protocol import ChatCompletionClient


PARA_SPLIT_RE = re.compile(r"\n\s*\n+")


def split_paragraphs(text: str) -> list[str]:
    parts = PARA_SPLIT_RE.split((text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def join_paragraphs(paras: list[str]) -> str:
    return "\n\n".join(p.strip() for p in paras if p.strip())


def _extract_facts_tokens(text: str) -> frozenset[str]:
    tokens: set[str] = set(re.findall(r"\d+[.\d/%]*|[A-Z]{2,}\d*", text))
    return frozenset(t for t in tokens if len(t) >= 1)


def rewrite_full_text(
    text: str,
    *,
    instruction: str,
    keep_facts: bool,
    client: ChatCompletionClient | None = None,
    model_id: str | None = None,
) -> str:
    if client is not None and model_id:
        system = (
            "你是中文写作编辑。根据用户指令改写全文；"
            + ("不得删除或编造关键事实与数字，仅调整表达。" if keep_facts else "可重组论述，但需自洽。")
        )
        return client.complete(
            system_prompt=system,
            user_prompt=f"【指令】{instruction}\n\n【原文】\n{text[:120_000]}",
            model_id=model_id,
        ).strip()
    if keep_facts:
        facts = _extract_facts_tokens(text)
        body = text + f"\n\n【按指令润色：{instruction}】"
        for t in sorted(facts, key=len, reverse=True):
            if t and t not in body:
                body = f"{t}\n" + body
        return body
    return f"【改写：{instruction}】\n\n{text}"


def rewrite_paragraph_slice(
    paras: list[str],
    start: int,
    end: int,
    *,
    instruction: str,
    client: ChatCompletionClient | None = None,
    model_id: str | None = None,
) -> tuple[list[str], list[int]]:
    """改写闭区间 [start, end] 段落，返回新段落列表与改写的全局下标。"""
    if start < 0 or end >= len(paras) or start > end:
        raise ValueError("invalid paragraph range")
    out = list(paras)
    changed: list[int] = []
    for i in range(start, end + 1):
        chunk = paras[i]
        if client is not None and model_id:
            new = client.complete(
                system_prompt="仅输出改写后的该段正文，不要标题或解释。",
                user_prompt=f"【指令】{instruction}\n\n【段落】\n{chunk[:40_000]}",
                model_id=model_id,
            ).strip()
        else:
            new = f"{chunk}\n（局部改写：{instruction}）"
        out[i] = new
        changed.append(i)
    return out, changed


def apply_context_bridge_paragraphs(
    paras: list[str],
    affected: list[int],
    *,
    client: ChatCompletionClient | None = None,
    model_id: str | None = None,
) -> tuple[list[str], list[int]]:
    """对受影响区间两侧的邻段做轻量衔接重写，弱化语气断层。"""
    if not affected:
        return paras, []
    lo, hi = min(affected), max(affected)
    bridge_idx: list[int] = []
    if lo > 0:
        bridge_idx.append(lo - 1)
    if hi + 1 < len(paras):
        bridge_idx.append(hi + 1)
    out = list(paras)
    extra_changed: list[int] = []
    for i in bridge_idx:
        chunk = out[i]
        ctx_center = paras[lo]
        center_hint = paras[hi] if hi != lo else ctx_center
        if client is not None and model_id:
            new = client.complete(
                system_prompt="你是衔接编辑，仅输出重写后的那一段，回扣相邻论述，口吻一致，不要复述标题。",
                user_prompt=(
                    f"【邻域参考段】{center_hint[:2000]}\n\n【待衔接段】\n{chunk[:20_000]}"
                ),
                model_id=model_id,
            ).strip()
        else:
            new = f"{chunk.strip()}衔接至改写段：{(center_hint or '')[:80]}…"
        out[i] = new
        extra_changed.append(i)
    return out, extra_changed


def replace_section_body(
    bundle: DraftBundle,
    section_id: int,
    new_section_text: str,
) -> DraftBundle:
    sections = list(bundle.sections_body)
    if section_id < 0 or section_id >= len(sections):
        raise ValueError("invalid section_id")
    sections[section_id] = new_section_text
    raw = "\n\n".join(sections)
    polished = join_paragraphs(split_paragraphs(raw))
    return DraftBundle(sections_body=sections, concatenated_raw=raw, concatenated_polished=polished)


def bundle_from_flat_paragraphs(
    paras: list[str],
    *,
    sections_body_template: list[str] | None = None,
) -> DraftBundle:
    polished = join_paragraphs(paras)
    if sections_body_template is None:
        return DraftBundle(sections_body=[polished], concatenated_raw=polished, concatenated_polished=polished)
    if len(sections_body_template) < 2:
        return DraftBundle(sections_body=[polished], concatenated_raw=polished, concatenated_polished=polished)
    nsec = len(sections_body_template)
    chunk = max(1, (len(paras) + nsec - 1) // nsec)
    buckets: list[list[str]] = [[] for _ in range(nsec)]
    for i, p in enumerate(paras):
        buckets[min(i // chunk, nsec - 1)].append(p)
    sections = [join_paragraphs(b) for b in buckets]
    raw = "\n\n".join(sections)
    return DraftBundle(sections_body=sections, concatenated_raw=raw, concatenated_polished=polished)


def rewrite_partial_by_section(
    bundle: DraftBundle,
    *,
    section_id: int,
    instruction: str,
    apply_bridge: bool,
    client: ChatCompletionClient | None = None,
    model_id: str | None = None,
) -> tuple[DraftBundle, list[int]]:
    if section_id < 0 or section_id >= len(bundle.sections_body):
        raise ValueError("invalid section_id")
    sec_text = bundle.sections_body[section_id]
    paras = split_paragraphs(sec_text)
    new_paras, _ = rewrite_paragraph_slice(
        paras, 0, len(paras) - 1, instruction=instruction, client=client, model_id=model_id
    )
    if apply_bridge and len(bundle.sections_body) > 1:
        flat_offsets = []
        acc = 0
        for j, sb in enumerate(bundle.sections_body):
            c = len(split_paragraphs(sb))
            if j == section_id:
                flat_offsets = list(range(acc, acc + c))
                break
            acc += c
        global_paras: list[str] = []
        for sb in bundle.sections_body:
            global_paras.extend(split_paragraphs(sb))
        g_lo = min(flat_offsets)
        g_hi = max(flat_offsets)
        for i, nv in enumerate(new_paras):
            if g_lo + i < len(global_paras):
                global_paras[g_lo + i] = nv
        global_paras2, bridged = apply_context_bridge_paragraphs(
            global_paras, list(range(g_lo, g_hi + 1)), client=client, model_id=model_id
        )
        b = bundle_from_flat_paragraphs(global_paras2, sections_body_template=bundle.sections_body)
        return b, sorted(set(range(g_lo, g_hi + 1)) | set(bridged))
    flat_off = sum(len(split_paragraphs(bundle.sections_body[j])) for j in range(section_id))
    if apply_bridge and new_paras:
        new_paras2, bridged_local = apply_context_bridge_paragraphs(
            new_paras, list(range(len(new_paras))), client=client, model_id=model_id
        )
        merged_sec = join_paragraphs(new_paras2)
        b = replace_section_body(bundle, section_id, merged_sec)
        touched = set(flat_off + i for i in range(len(new_paras2))) | {flat_off + i for i in bridged_local}
        return b, sorted(touched)
    merged_sec = join_paragraphs(new_paras)
    b = replace_section_body(bundle, section_id, merged_sec)
    return b, list(range(flat_off, flat_off + len(new_paras)))


def rewrite_partial_by_paragraph_range(
    bundle: DraftBundle,
    *,
    paragraph_range: tuple[int, int],
    instruction: str,
    apply_bridge: bool,
    client: ChatCompletionClient | None = None,
    model_id: str | None = None,
) -> tuple[DraftBundle, list[int]]:
    paras = split_paragraphs(bundle.concatenated_polished)
    start, end = paragraph_range
    new_paras, changed = rewrite_paragraph_slice(
        paras, start, end, instruction=instruction, client=client, model_id=model_id
    )
    bridged_idx: list[int] = []
    if apply_bridge:
        new_paras, bridged_idx = apply_context_bridge_paragraphs(new_paras, changed, client=client, model_id=model_id)
    merged = bundle_from_flat_paragraphs(new_paras, sections_body_template=bundle.sections_body)
    return merged, sorted(set(changed) | set(bridged_idx))
