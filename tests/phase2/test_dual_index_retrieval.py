from __future__ import annotations

from pathlib import Path

from app.corpus.author_profile import build_author_profile
from app.corpus.chroma_index import ChromaCorpusIndex
from app.corpus.embeddings import DeterministicHashEmbedding
from app.corpus.ingest_pipeline import index_author_from_raw_dir
from app.corpus.retrieval import retrieve_style_anchors
from app.db.sqlite_schema import get_connection, init_schema
from app.settings import ChunkYamlConfig


def test_semantic_topk_and_rerank_stable(tmp_path: Path) -> None:
    author = "author_x"
    raw = tmp_path / "raw" / author
    raw.mkdir(parents=True)
    long_txt = ("关于人工智能写作的伦理边界。" + "句式变化与留白。" * 120)[:2500]
    (raw / "a.txt").write_text(long_txt, encoding="utf-8")

    db_path = tmp_path / "meta.db"
    conn = get_connection(db_path)
    init_schema(conn)

    ef = DeterministicHashEmbedding(dimension=96)
    chroma_root = tmp_path / "chroma_store"
    idx = ChromaCorpusIndex(chroma_root, ef)
    cfg = ChunkYamlConfig(
        slide_min_chars=200,
        slide_max_chars=400,
        overlap_min_chars=60,
        overlap_max_chars=100,
    )

    stats = index_author_from_raw_dir(
        conn,
        idx,
        author_slug=author,
        raw_root=tmp_path / "raw",
        clean_root=tmp_path / "clean",
        chunk_cfg=cfg,
    )
    assert stats["chunks_indexed"] > 0

    q = "伦理与写作的边界"
    a1 = retrieve_style_anchors(
        conn,
        idx,
        author,
        q,
        top_k=40,
        top_n=8,
        semantic_weight=0.5,
    )
    a2 = retrieve_style_anchors(
        conn,
        idx,
        author,
        q,
        top_k=40,
        top_n=8,
        semantic_weight=0.5,
    )
    assert len(a1) <= 8
    ids1 = [x.chunk_id for x in a1]
    ids2 = [x.chunk_id for x in a2]
    assert ids1 == ids2, "确定性重排应稳定"
    for anchor in a1:
        assert anchor.chunk_id > 0
        assert anchor.explanation


def test_profile_has_four_layers(tmp_path: Path) -> None:
    """复用 ingestion 后在 profile 上出现四层字段"""
    author = "author_y"
    raw = tmp_path / "raw" / author
    raw.mkdir(parents=True)
    (raw / "b.txt").write_text("第一段。\n\n第二段论述。" * 100, encoding="utf-8")
    conn = get_connection(tmp_path / "m.db")
    init_schema(conn)
    idx = ChromaCorpusIndex(tmp_path / "ch", DeterministicHashEmbedding(64))
    index_author_from_raw_dir(
        conn,
        idx,
        author_slug=author,
        raw_root=tmp_path / "raw",
        clean_root=tmp_path / "clean",
        chunk_cfg=ChunkYamlConfig(
            slide_min_chars=120,
            slide_max_chars=240,
            overlap_min_chars=40,
            overlap_max_chars=60,
        ),
    )
    prof = build_author_profile(conn, author)
    assert set(prof) >= {"author_slug", "lexical", "syntax", "structure", "tone"}
    assert prof["tone"]["transition_word_density_mean"] >= 0.0
