from __future__ import annotations

import sqlite3
from pathlib import Path

from app.corpus.chroma_index import ChromaCorpusIndex
from app.corpus.chunker import combine_chunks_for_document
from app.corpus.corpus_store import (
    ensure_author,
    insert_chunk_with_style,
    insert_corpus_document,
    write_clean_jsonl_snapshot,
)
from app.corpus.ingest_loader import list_author_txt_files, load_txt_file_safe
from app.corpus.text_cleaner import clean_document_text, split_paragraphs
from app.settings import ChunkYamlConfig


def index_author_from_raw_dir(
    conn: sqlite3.Connection,
    chroma: ChromaCorpusIndex,
    *,
    author_slug: str,
    raw_root: Path,
    clean_root: Path,
    chunk_cfg: ChunkYamlConfig,
) -> dict:
    """
    从 data/raw/<author>/ 扫描 txt，清洗、切块、写 SQLite 风格特征与 Chroma 向量。
    返回统计信息（测试与 CLI 可用）。
    """
    ensure_author(conn, author_slug)
    files = list_author_txt_files(raw_root, author_slug)
    chroma.reset_collection(author_slug)

    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict] = []
    processed = 0
    skipped: list[str] = []

    clean_dir = clean_root / author_slug
    clean_dir.mkdir(parents=True, exist_ok=True)

    for path in files:
        res = load_txt_file_safe(path)
        if res.skipped or res.text is None:
            skipped.append(f"{path.name}:{res.skip_reason}")
            continue
        title, body = clean_document_text(res.text)
        if not body.strip():
            skipped.append(f"{path.name}:empty_after_clean")
            continue
        paras = split_paragraphs(body)
        drafts = combine_chunks_for_document(
            paras,
            body,
            slide_min_chars=chunk_cfg.slide_min_chars,
            slide_max_chars=chunk_cfg.slide_max_chars,
            overlap_min_chars=chunk_cfg.overlap_min_chars,
            overlap_max_chars=chunk_cfg.overlap_max_chars,
        )
        rel = f"{author_slug}/{path.name}"
        snap_path = clean_dir / f"{path.stem}.jsonl"
        write_clean_jsonl_snapshot(
            snap_path,
            {
                "author_slug": author_slug,
                "source": path.name,
                "title": title,
                "paragraphs": paras,
                "body": body,
            },
        )
        doc_id = insert_corpus_document(
            conn,
            author_slug=author_slug,
            source_relpath=rel,
            title=title,
            body_text=body,
            clean_jsonl_path=str(snap_path),
        )

        for d in drafts:
            cid = insert_chunk_with_style(conn, document_id=doc_id, author_slug=author_slug, draft=d)
            ids.append(str(cid))
            docs.append(d.text)
            metas.append({"chunk_id": str(cid), "author_slug": author_slug, "kind": d.kind})

        processed += 1

    if ids:
        chroma.upsert_chunks(author_slug, ids=ids, documents=docs, metadatas=metas, reset=False)

    return {
        "author_slug": author_slug,
        "files_found": len(files),
        "files_processed": processed,
        "chunks_indexed": len(ids),
        "skipped": skipped,
    }
