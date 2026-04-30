from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from app.corpus.text_cleaner import normalize_unicode


_SPLIT_SENT_RE = re.compile(r"(?<=[。！？!?…])[ \n　]*")


_TRANSITION = frozenset(
    """然而但是不过因此所以总之此外另外而且并且若如果虽然尽管于是从而乃至何况不仅而且并且""")

_STRONG_MARKERS = frozenset(("毫无疑问", "显然", "无疑", "必然", "必须", "肯定", "绝对", "不可能不"))
_SOFT_MARKERS = frozenset(("可能", "或许", "也许", "大概", "似乎", "未必", "不一定"))


@dataclass(frozen=True)
class StyleFeatureVector:
    avg_sentence_len: float
    long_short_ratio: float
    punctuation_profile: dict[str, float]
    transition_word_density: float
    rhetoric_density: float
    first_person_ratio: float
    assertiveness_score: float

    def to_db_row(self) -> tuple[float, float, str, float, float, float, float]:
        return (
            float(self.avg_sentence_len),
            float(self.long_short_ratio),
            json.dumps(self.punctuation_profile, ensure_ascii=False, sort_keys=True),
            float(self.transition_word_density),
            float(self.rhetoric_density),
            float(self.first_person_ratio),
            float(self.assertiveness_score),
        )


def split_sentences(text: str) -> list[str]:
    t = normalize_unicode(text.strip())
    if not t:
        return []
    parts = _SPLIT_SENT_RE.split(t)
    out = [p.strip() for p in parts if p.strip()]
    return out if out else [t]


def _punctuation_histogram(text: str) -> dict[str, float]:
    counts = dict.fromkeys(
        ("comma", "period", "question", "exclaim", "enumeration", "colon", "ellipsis"),
        0,
    )
    total_chars = max(1, len(text))
    for ch in text:
        if ch in ("，", ","):
            counts["comma"] += 1
        elif ch in ("。", "."):
            counts["period"] += 1
        elif ch in "？?":
            counts["question"] += 1
        elif ch in "！!":
            counts["exclaim"] += 1
        elif ch in "、；;":
            counts["enumeration"] += 1
        elif ch in "：:":
            counts["colon"] += 1
        elif ch in "…⋯":
            counts["ellipsis"] += 1
    return {k: v / total_chars for k, v in counts.items()}


def _transition_density(text: str) -> float:
    if not text:
        return 0.0
    n_hit = sum(1 for w in _TRANSITION if w in text)
    return min(1.0, n_hit / max(10.0, len(text) / 80.0))


def _first_person_ratio(text: str) -> float:
    if not text:
        return 0.0
    hits = sum(text.count(tok) for tok in ("我", "我们", "本人", "笔者", "咱"))
    return min(1.0, hits / max(30.0, len(text) / 40.0))


def _rhetoric_density(text: str, sentence_count: int) -> float:
    if sentence_count <= 0:
        return 0.0
    metaphors = len(re.findall(r"像[\u4e00-\u9fff]{0,16}一样|如同|犹如|仿佛|似的", text))
    rhetorical_q = len(re.findall(r"[难道岂][\u4e00-\u9fff]{0,20}[吗呢罢]", text))
    score = metaphors + rhetorical_q
    return min(1.0, score / max(3.0, sentence_count / 2.0))


def _assertiveness_score(text: str) -> float:
    strong = sum(1 for m in _STRONG_MARKERS if m in text)
    soft = sum(1 for m in _SOFT_MARKERS if m in text)
    return max(0.0, min(1.0, 0.5 + 0.1 * strong - 0.12 * soft))


def _long_short_ratio(sentences: list[str]) -> float:
    lens = [len(s) for s in sentences if s.strip()]
    if not lens:
        return 0.5
    med = sorted(lens)[len(lens) // 2]
    long_c = sum(1 for x in lens if x >= med)
    short_c = len(lens) - long_c + 1e-6
    return max(0.0, min(2.0, long_c / short_c))


def extract_style_features(text: str) -> StyleFeatureVector:
    sents = split_sentences(text)
    lens = [len(s) for s in sents if s.strip()]
    avg_len = float(sum(lens) / len(lens)) if lens else 0.0
    pn = len(sents) if sents else 1
    return StyleFeatureVector(
        avg_sentence_len=avg_len,
        long_short_ratio=_long_short_ratio(sents),
        punctuation_profile=_punctuation_histogram(text),
        transition_word_density=_transition_density(text),
        rhetoric_density=_rhetoric_density(text, pn),
        first_person_ratio=_first_person_ratio(text),
        assertiveness_score=_assertiveness_score(text),
    )


def style_feature_numeric_vector(sf: StyleFeatureVector) -> list[float]:
    """用于向量距离比较的稳定数值向量（与同序 profile 拼接）。"""
    p = sf.punctuation_profile
    keys = sorted(p.keys())
    return [
        sf.avg_sentence_len / 80.0,
        sf.long_short_ratio,
        sf.transition_word_density,
        sf.rhetoric_density,
        sf.first_person_ratio,
        sf.assertiveness_score,
    ] + [p[k] for k in keys]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("维度不一致")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))
