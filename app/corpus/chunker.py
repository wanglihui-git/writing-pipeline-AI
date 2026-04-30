from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunkDraft:
    kind: str  # "paragraph" | "window"
    ordinal: int
    text: str
    char_len: int


def paragraph_chunks(paragraphs: list[str]) -> list[TextChunkDraft]:
    out: list[TextChunkDraft] = []
    for p in paragraphs:
        s = p.strip()
        if not s:
            continue
        out.append(TextChunkDraft("paragraph", len(out), s, len(s)))
    return out


def sliding_character_chunks(
    text: str,
    *,
    slide_min_chars: int,
    slide_max_chars: int,
    overlap_min_chars: int,
    overlap_max_chars: int,
) -> list[TextChunkDraft]:
    """
    滑窗切块：长度在 [slide_min_chars, slide_max_chars]（除末段可适当缩短并合并）。
    重叠取 overlap_min/overlap_max 的中点，保证确定性。
    """
    if slide_min_chars > slide_max_chars or slide_min_chars < 1:
        raise ValueError("无效窗口参数：slide_min_chars / slide_max_chars")
    overlap = (overlap_min_chars + overlap_max_chars) // 2
    if overlap >= slide_max_chars:
        raise ValueError("重叠长度必须小于 slide_max_chars")
    if overlap_min_chars > overlap_max_chars:
        raise ValueError("overlap_min_chars 不可大于 overlap_max_chars")

    t = text.strip()
    if not t:
        return []
    if len(t) <= slide_max_chars:
        return [TextChunkDraft("window", 0, t, len(t))]

    chunks: list[str] = []
    start = 0
    wmax = slide_max_chars
    wmin = slide_min_chars

    while start < len(t):
        end = min(start + wmax, len(t))
        segment_len = end - start
        if segment_len < wmin:
            tail = t[start:end]
            if tail.strip() and chunks:
                chunks[-1] += tail
            elif tail.strip():
                chunks.append(tail)
            break
        chunks.append(t[start:end])
        if end >= len(t):
            break
        stride = max(1, segment_len - overlap)
        start += stride

    merged: list[str] = []
    for c in chunks:
        c = c.strip()
        if not c:
            continue
        if merged and len(c) < wmin:
            merged[-1] = (merged[-1] + "\n" + c).strip()
        else:
            merged.append(c)

    return [TextChunkDraft("window", i, blk, len(blk)) for i, blk in enumerate(merged) if blk]


def combine_chunks_for_document(
    paragraph_texts: list[str],
    full_body: str,
    *,
    slide_min_chars: int,
    slide_max_chars: int,
    overlap_min_chars: int,
    overlap_max_chars: int,
) -> list[TextChunkDraft]:
    """双粒度：先段落块，再对全文做滑窗。"""
    para = paragraph_chunks(paragraph_texts)
    win = sliding_character_chunks(
        full_body,
        slide_min_chars=slide_min_chars,
        slide_max_chars=slide_max_chars,
        overlap_min_chars=overlap_min_chars,
        overlap_max_chars=overlap_max_chars,
    )
    offset = len(para)
    win_renumbered = [TextChunkDraft(c.kind, offset + i, c.text, c.char_len) for i, c in enumerate(win)]
    return para + win_renumbered
