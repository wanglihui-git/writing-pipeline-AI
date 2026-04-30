from __future__ import annotations

from pathlib import Path

import chromadb

from app.corpus.chroma_index import ChromaCorpusIndex, chroma_collection_name
from app.corpus.embeddings import DeterministicHashEmbedding


def test_chroma_add_query_persist_reload(tmp_path: Path) -> None:
    ef = DeterministicHashEmbedding(dimension=64)
    p1 = tmp_path / "c1"
    idx = ChromaCorpusIndex(p1, ef)
    col = idx.reset_collection("testauthor")
    col.add(
        ids=["1", "2"],
        documents=["神经网络与符号主义。", "文学创作中的节奏感。"],
        metadatas=[{"chunk_id": "1"}, {"chunk_id": "2"}],
    )
    qr = idx.query_semantic("testauthor", "深度学习的写作风格", 2)
    assert qr["ids"] and qr["ids"][0]

    p2 = tmp_path / "c2"
    # 另建目录演示隔离；同源持久化复查
    client2 = chromadb.PersistentClient(path=str(p1))
    name = chroma_collection_name("testauthor")
    col2 = client2.get_collection(name=name, embedding_function=ef)
    assert col2.count() == 2
