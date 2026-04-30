from __future__ import annotations

import re
from collections import Counter

from app.pipeline.models import ArticleBriefNormalized, JudgeScores, OutlineDocument


_TEMPLATE_PHRASES = ("综上所述", "总而言之", "在本文中", "首先，", "其次，", "最后，", "不可否认的是",)


def avg_sentence_length(text: str) -> float:
    sents = re.split(r"[。！？!?…]+", text)
    chunks = [s.strip() for s in sents if s.strip()]
    if not chunks:
        return 0.0
    return sum(len(s) for s in chunks) / len(chunks)


def style_rule_score(text: str) -> tuple[float, dict]:
    avg = avg_sentence_length(text)
    penalty = abs(avg - 45.0) / 120.0
    punct_hist = Counter(ch for ch in text if ch in "，。；：“”『』？！、…⋯")
    punct_var = punct_hist.most_common(1)[0][1] if punct_hist else 0
    richness = min(1.0, punct_var / max(40.0, len(text) / 25))
    base = max(45.0, 88.0 - penalty * 100 + richness * 12)
    return float(min(100.0, max(0.0, base))), {
        "avg_sentence_len_approx": avg,
        "punctuation_peak": punct_var,
    }


def structure_rule_score(text: str, outline: OutlineDocument, brief: ArticleBriefNormalized) -> tuple[float, dict]:
    headings = len(re.findall(r"^#\s+|^##\s+", text, flags=re.MULTILINE))
    expected_hints = []
    for s in outline.sections:
        if s.section_title.strip():
            expected_hints.append(s.section_title.strip()[:24])
            if s.section_title.strip() in text:
                headings += 1
    mentions = sum(1 for hint in expected_hints if hint and hint in text)
    denom = max(4, len(outline.sections) * 2)
    overlap = mentions / denom
    keyword_topic = brief.topic[:40] if brief.topic.strip() else ""
    topic_bonus = (keyword_topic and keyword_topic in text[: min(6000, len(text))])
    ratio = overlap + (0.15 if topic_bonus else 0.0)
    score = 55.0 + 45.0 * min(1.0, ratio * 2.8)
    return float(min(100.0, max(0.0, score))), {
        "outline_section_count": len(outline.sections),
        "title_mentions_approx": mentions,
        "markdown_headings_approx": headings,
        "keyword_topic_bonus": topic_bonus,
    }


def naturalness_rule_score(text: str) -> tuple[float, dict]:
    n = sum(text.count(ph) for ph in _TEMPLATE_PHRASES)
    density = n / max(1, len(text) / 500)
    base = max(52.0, 95.0 - density * 18.0 - (text.count("---") > 5) * 10)
    return float(min(100.0, max(0.0, base))), {
        "template_phrase_hits": n,
        "template_density_approx": density,
    }


def compute_rule_scores(text: str, outline: OutlineDocument, brief: ArticleBriefNormalized) -> tuple[JudgeScores, dict]:
    s_style, ev_s = style_rule_score(text)
    s_struct, ev_st = structure_rule_score(text, outline, brief)
    s_nat, ev_n = naturalness_rule_score(text)
    return (
        JudgeScores(
            style_similarity_0_100=s_style,
            structure_completeness_0_100=s_struct,
            naturalness_0_100=s_nat,
            rationales={"style": str(ev_s), "structure": str(ev_st), "naturalness": str(ev_n)},
        ),
        {"style": ev_s, "structure": ev_st, "naturalness": ev_n},
    )
