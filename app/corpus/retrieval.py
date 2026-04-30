from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from app.corpus.chroma_index import ChromaCorpusIndex
from app.corpus.corpus_store import fetch_style_vectors_for_author, load_chunk_row
from app.corpus.style_features import cosine_similarity


@dataclass(frozen=True)
class StyleAnchor:
    chunk_id: int
    text: str
    semantic_rank: int
    semantic_score: float
    style_similarity: float
    fused_score: float
    explanation: dict[str, Any]


def _mean_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    acc = [0.0] * dim
    for v in vectors:
        if len(v) != dim:
            raise ValueError("向量维度不一致")
        for i, x in enumerate(v):
            acc[i] += x
    return [x / len(vectors) for x in acc]


def retrieve_style_anchors(
    conn: sqlite3.Connection,
    index: ChromaCorpusIndex,
    author_slug: str,
    query_text: str,
    *,
    top_k: int,
    top_n: int,
    semantic_weight: float,
) -> list[StyleAnchor]:
    pooled = fetch_style_vectors_for_author(conn, author_slug)
    if not pooled:
        return []
    centroid = _mean_vector([v for _, v in pooled])
    vec_by_chunk = {cid: v for cid, v in pooled}

    qr = index.query_semantic(author_slug, query_text, top_k)
    ids_outer = qr.get("ids") or [[]]
    metas_outer = qr.get("metadatas") or [[]]
    ids = ids_outer[0] if ids_outer else []
    metas = metas_outer[0] if metas_outer else []

    if not ids or not centroid:
        return []

    k_eff = len(ids)
    ranked: list[StyleAnchor] = []
    for rank, cid_chroma in enumerate(ids):
        md = metas[rank] if rank < len(metas) else {}
        raw_id = md.get("chunk_id") if isinstance(md, dict) else None
        if raw_id is None:
            continue
        try:
            cid = int(raw_id)
        except (TypeError, ValueError):
            continue
        cv = vec_by_chunk.get(cid)
        if cv is None:
            continue
        style_sim = cosine_similarity(cv, centroid)
        semantic_norm = 1.0 - (rank / max(1.0, float(k_eff - 1))) if k_eff > 1 else 1.0
        fused = semantic_weight * semantic_norm + (1.0 - semantic_weight) * max(0.0, style_sim)
        crow = load_chunk_row(conn, cid)
        text = crow["text"] if crow else ""

        ranked.append(
            StyleAnchor(
                chunk_id=cid,
                text=text,
                semantic_rank=rank + 1,
                semantic_score=semantic_norm,
                style_similarity=style_sim,
                fused_score=fused,
                explanation={
                    "semantic_weight": semantic_weight,
                    "fusion": "weighted_sum(semantic_rank_norm, cosine_style_vs_centroid)",
                },
            )
        )

    ranked.sort(key=lambda a: (-a.fused_score, a.chunk_id))
    return ranked[: max(1, top_n)]
