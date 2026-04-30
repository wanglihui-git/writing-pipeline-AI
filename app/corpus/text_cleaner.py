from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_MULTI_NL = re.compile(r"\n{3,}")


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def strip_control_chars(text: str) -> str:
    return _CTRL_RE.sub("", text)


def collapse_blank_lines(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = _MULTI_NL.sub("\n\n", t)
    return t.strip()


def remove_abnormal_symbols(text: str) -> str:
    """去掉零宽字符等常见异常符号，保留中英文与常规标点。"""
    return re.sub(r"[\u200b-\u200f\u2060-\u206f\ufeff\u202a-\u202e]", "", text)


def split_title_body(text: str) -> tuple[str | None, str]:
    """首行较短且后接空行时视为标题。"""
    lines = text.split("\n")
    if len(lines) >= 2 and lines[0].strip() and len(lines[0].strip()) <= 80 and not lines[1].strip():
        title = lines[0].strip()
        body = "\n".join(lines[2:]).strip()
        return title, body or text
    return None, text


def split_paragraphs(body: str) -> list[str]:
    parts = re.split(r"\n\s*\n+", body)
    return [p.strip() for p in parts if p.strip()]


def _norm_para(p: str) -> str:
    return re.sub(r"\s+", "", p.casefold())


def dedupe_near_duplicate_paragraphs(paragraphs: list[str], *, ratio: float = 0.92) -> list[str]:
    kept: list[str] = []
    norms: list[str] = []
    for p in paragraphs:
        pn = _norm_para(p)
        if len(pn) < 8:
            kept.append(p)
            norms.append(pn)
            continue
        dup = False
        for prev in norms:
            if len(prev) < 8:
                continue
            sm = SequenceMatcher(None, pn, prev)
            if sm.quick_ratio() >= ratio - 0.05 and sm.ratio() >= ratio:
                dup = True
                break
        if not dup:
            kept.append(p)
            norms.append(pn)
    return kept


def clean_document_text(raw: str) -> tuple[str | None, str]:
    """返回 (可选标题, 正文清洗结果)。"""
    t = normalize_unicode(raw)
    t = strip_control_chars(t)
    t = remove_abnormal_symbols(t)
    t = collapse_blank_lines(t)
    title, body = split_title_body(t)
    paras = split_paragraphs(body)
    paras = dedupe_near_duplicate_paragraphs(paras)
    merged = "\n\n".join(paras)
    return title, merged


def clean_full_text(raw: str) -> str:
    title, body = clean_document_text(raw)
    if title:
        return f"{title}\n\n{body}"
    return body
