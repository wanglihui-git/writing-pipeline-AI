from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from app.corpus.chunker import TextChunkDraft
from app.corpus.style_features import StyleFeatureVector, extract_style_features


def ensure_author(conn: sqlite3.Connection, slug: str, display_name: str | None = None) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO authors(slug, display_name) VALUES (?, ?)",
        (slug, display_name or slug),
    )
    conn.commit()


def insert_corpus_document(
    conn: sqlite3.Connection,
    *,
    author_slug: str,
    source_relpath: str,
    title: str | None,
    body_text: str,
    clean_jsonl_path: str | None = None,
) -> int:
    h = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
    cur = conn.execute(
        """
        INSERT INTO corpus_documents(author_slug, source_relpath, title, body_sha256, char_count, clean_jsonl_path)
        VALUES (?,?,?,?,?,?)
        """,
        (author_slug, source_relpath, title or "", h, len(body_text), clean_jsonl_path),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_chunk_with_style(
    conn: sqlite3.Connection,
    *,
    document_id: int,
    author_slug: str,
    draft: TextChunkDraft,
    style: StyleFeatureVector | None = None,
) -> int:
    sf = style or extract_style_features(draft.text)
    row = sf.to_db_row()
    cur = conn.execute(
        """
        INSERT INTO chunks(document_id, author_slug, kind, ordinal, text, char_len, meta_json)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            document_id,
            author_slug,
            draft.kind,
            draft.ordinal,
            draft.text,
            draft.char_len,
            None,
        ),
    )
    cid = int(cur.lastrowid)
    conn.execute(
        """
        INSERT INTO style_features(
            chunk_id, avg_sentence_len, long_short_ratio, punctuation_profile_json,
            transition_word_density, rhetoric_density, first_person_ratio, assertiveness_score
        )
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (cid, *row),
    )
    conn.commit()
    return cid


def fetch_style_vectors_for_author(conn: sqlite3.Connection, author_slug: str) -> list[tuple[int, list[float]]]:
    rows = conn.execute(
        """
        SELECT sf.chunk_id, sf.avg_sentence_len, sf.long_short_ratio, sf.punctuation_profile_json,
               sf.transition_word_density, sf.rhetoric_density, sf.first_person_ratio, sf.assertiveness_score
        FROM style_features sf
        JOIN chunks c ON sf.chunk_id = c.id
        WHERE c.author_slug = ?
        """,
        (author_slug,),
    ).fetchall()
    out: list[tuple[int, list[float]]] = []
    for r in rows:
        punct = json.loads(r["punctuation_profile_json"])
        keys = sorted(punct.keys())
        vec = [
            float(r["avg_sentence_len"]) / 80.0,
            float(r["long_short_ratio"]),
            float(r["transition_word_density"]),
            float(r["rhetoric_density"]),
            float(r["first_person_ratio"]),
            float(r["assertiveness_score"]),
        ]
        vec.extend(float(punct[k]) for k in keys)
        out.append((int(r["chunk_id"]), vec))
    return out


def load_chunk_row(conn: sqlite3.Connection, chunk_id: int):
    row = conn.execute("SELECT id, author_slug, kind, ordinal, text, char_len FROM chunks WHERE id=?", (chunk_id,)).fetchone()
    return row


def write_clean_jsonl_snapshot(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
