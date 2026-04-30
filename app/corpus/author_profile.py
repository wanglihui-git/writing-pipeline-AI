from __future__ import annotations

import json
import sqlite3
from collections import Counter


def build_author_profile(conn: sqlite3.Connection, author_slug: str, *, sample_bigrams_chars: int = 50000) -> dict:
    """
    四层摘要：词汇/句法/结构/语气，用于解释与可视化。
    chunks 采样合并后统计字符二元组作为弱「词汇指纹」占位（可不依赖分词）。
    """
    agg = conn.execute(
        """
        SELECT
          AVG(sf.avg_sentence_len) AS asn,
          AVG(sf.long_short_ratio) AS lr,
          AVG(sf.transition_word_density) AS td,
          AVG(sf.rhetoric_density) AS rd,
          AVG(sf.first_person_ratio) AS fp,
          AVG(sf.assertiveness_score) AS asr,
          COUNT(*) AS n_chunks,
          AVG(c.char_len) AS avg_chunk_len
        FROM style_features sf
        JOIN chunks c ON sf.chunk_id = c.id
        WHERE c.author_slug = ?
        """,
        (author_slug,),
    ).fetchone()

    chunks_meta = conn.execute(
        """
        SELECT kind, AVG(char_len) AS alen FROM chunks WHERE author_slug = ? GROUP BY kind
        """,
        (author_slug,),
    ).fetchall()

    texts_rows = conn.execute(
        """
        SELECT c.text FROM chunks c WHERE c.author_slug = ?
        ORDER BY c.id DESC LIMIT 200
        """,
        (author_slug,),
    ).fetchall()

    blob = "".join(r[0] for r in texts_rows if r[0])[:sample_bigrams_chars]
    bigrams = Counter()
    for i in range(len(blob) - 1):
        bg = blob[i : i + 2]
        if bg[0].isspace() or bg[1].isspace():
            continue
        bigrams[bg] += 1

    def _interesting(s: str) -> bool:
        return any("\u4e00" <= ch <= "\u9fff" or ch.isalpha() for ch in s)

    top_bg = [b for b, _ in bigrams.most_common() if _interesting(b)][:30]

    if not agg or (agg["n_chunks"] or 0) == 0:
        return {
            "author_slug": author_slug,
            "lexical": {"top_character_bigrams": [], "note": "暂无语料切块"},
            "syntax": {},
            "structure": {},
            "tone": {},
        }

    punctuation_means = _average_punctuation_profile(conn, author_slug)

    pr_row = conn.execute(
        "SELECT AVG(char_len) FROM chunks WHERE author_slug = ? AND kind = 'paragraph'",
        (author_slug,),
    ).fetchone()
    paragraph_avg = float(pr_row[0]) if pr_row and pr_row[0] is not None else 0.0
    w_row = conn.execute(
        "SELECT AVG(char_len) FROM chunks WHERE author_slug = ? AND kind = 'window'",
        (author_slug,),
    ).fetchone()
    window_avg = float(w_row[0]) if w_row and w_row[0] is not None else 0.0

    kind_stats: dict[str, float] = {}
    for row in chunks_meta:
        kind_stats[str(row["kind"])] = float(row["alen"])

    lexical = {
        "top_character_bigrams": top_bg,
        "approx_bigram_vocab": len(bigrams),
    }
    syntax = {
        "avg_sentence_len": float(agg["asn"] or 0.0),
        "long_short_ratio": float(agg["lr"] or 0.0),
        "punctuation_profile_mean": punctuation_means,
        "chunk_char_len_avg": float(agg["avg_chunk_len"] or 0.0),
        "chunks_by_kind_avg_len": kind_stats or {"paragraph": paragraph_avg, "window": window_avg},
    }
    structure = {
        "chunk_count": int(agg["n_chunks"] or 0),
        "paragraph_chunk_avg_chars": paragraph_avg,
        "sliding_chunk_avg_chars": window_avg,
    }
    tone = {
        "transition_word_density_mean": float(agg["td"] or 0.0),
        "rhetoric_density_mean": float(agg["rd"] or 0.0),
        "first_person_ratio_mean": float(agg["fp"] or 0.0),
        "assertiveness_score_mean": float(agg["asr"] or 0.0),
    }
    return {
        "author_slug": author_slug,
        "lexical": lexical,
        "syntax": syntax,
        "structure": structure,
        "tone": tone,
    }


def _average_punctuation_profile(conn: sqlite3.Connection, author_slug: str) -> dict[str, float]:
    rows = conn.execute(
        """
        SELECT sf.punctuation_profile_json
        FROM style_features sf JOIN chunks c ON sf.chunk_id = c.id
        WHERE c.author_slug = ?
        """,
        (author_slug,),
    ).fetchall()
    acc: dict[str, float] = {}
    count = 0
    for r in rows:
        pj = r["punctuation_profile_json"]
        d = json.loads(pj)
        if isinstance(d, dict):
            count += 1
            for k, v in d.items():
                if isinstance(v, (int, float)):
                    acc[k] = acc.get(k, 0.0) + float(v)
    if count == 0:
        return {}
    return {k: v / count for k, v in acc.items()}
