from __future__ import annotations

from app.corpus.text_cleaner import (
    clean_document_text,
    dedupe_near_duplicate_paragraphs,
    normalize_unicode,
    remove_abnormal_symbols,
    split_paragraphs,
)


def test_normalize_nfkc_fullwidth_digits() -> None:
    assert "12" in normalize_unicode("１２")


def test_strip_zero_width_removed() -> None:
    raw = remove_abnormal_symbols("hello\u200b\u2060world")
    assert raw == "helloworld"


def test_near_duplicate_removed() -> None:
    paras = [
        "这是第一段。\n这里有细节。",
        "这是第一段。这里有细节。",
        "完全不同的段落。",
    ]
    dedup = dedupe_near_duplicate_paragraphs(paras, ratio=0.92)
    assert len(dedup) == 2


def test_title_body_split_short_title() -> None:
    raw = "短标题\n\n正文第一段。\n\n第二段。\n\n"
    title, body = clean_document_text(raw)
    assert title == "短标题"
    assert "第一段" in body


def test_split_paragraphs() -> None:
    body = "a。\n\nb。\n\n c "
    pars = split_paragraphs(body)
    assert len(pars) >= 2
