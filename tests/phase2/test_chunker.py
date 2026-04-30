from __future__ import annotations

import pytest

from app.corpus.chunker import (
    paragraph_chunks,
    sliding_character_chunks,
    combine_chunks_for_document,
)


def test_paragraph_boundaries() -> None:
    ch = paragraph_chunks([" 第一段 ", "", "第二段\n行内"])
    assert len(ch) == 2
    assert ch[0].kind == "paragraph" and ch[0].ordinal == 0
    assert ch[1].ordinal == 1


def test_sliding_length_and_overlap() -> None:
    # 足够长时，除末段外窗口长度落在 [min,max]
    t = ("块" + "字" * 499) * 6
    chunks = sliding_character_chunks(
        t,
        slide_min_chars=400,
        slide_max_chars=600,
        overlap_min_chars=80,
        overlap_max_chars=120,
    )
    assert len(chunks) >= 2
    for c in chunks[:-1]:
        assert chunk_cfg_bounds(c.char_len, 400, 600)
    merged = "".join(c.text for c in chunks)
    assert "块" in merged


def chunk_cfg_bounds(n: int, lo: int, hi: int) -> bool:
    return lo <= n <= hi


def test_sliding_invalid_overlap_raises() -> None:
    with pytest.raises(ValueError):
        sliding_character_chunks(
            "x" * 1000,
            slide_min_chars=100,
            slide_max_chars=500,
            overlap_min_chars=500,
            overlap_max_chars=500,
        )


def test_combine_dual_grain() -> None:
    paras = ["段落一内容。" * 20, "段落二更长。" * 80]
    body = "\n\n".join(paras)
    drafts = combine_chunks_for_document(
        paras,
        body,
        slide_min_chars=120,
        slide_max_chars=200,
        overlap_min_chars=40,
        overlap_max_chars=60,
    )
    kinds = [d.kind for d in drafts]
    assert kinds.count("paragraph") == 2
    assert any(k == "window" for k in kinds)
