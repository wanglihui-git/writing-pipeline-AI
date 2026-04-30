from __future__ import annotations

import re
from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError


def chroma_collection_name(author_slug: str) -> str:
    safe = re.sub(r"[^\w\-]+", "_", author_slug, flags=re.UNICODE).strip("_")
    if not safe:
        raise ValueError("author_slug 非法")
    return f"corpus_{safe[:80]}"


class ChromaCorpusIndex:
    def __init__(self, persistence_path: Path, embedding_function):
        persistence_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persistence_path))
        self._ef = embedding_function

    @property
    def client(self) -> chromadb.PersistentClient:
        return self._client

    def reset_collection(self, author_slug: str):
        name = chroma_collection_name(author_slug)
        try:
            self._client.delete_collection(name=name)
        except (ValueError, NotFoundError):
            pass
        return self._client.create_collection(name=name, embedding_function=self._ef)

    def get_or_create(self, author_slug: str):
        name = chroma_collection_name(author_slug)
        return self._client.get_or_create_collection(name=name, embedding_function=self._ef)

    def upsert_chunks(
        self,
        author_slug: str,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        reset: bool = False,
    ):
        if len(ids) != len(documents) or len(ids) != len(metadatas):
            raise ValueError("ids/documents/metadatas 长度不一致")
        col = self.reset_collection(author_slug) if reset else self.get_or_create(author_slug)
        col.add(ids=ids, documents=documents, metadatas=metadatas)
        return col

    def query_semantic(self, author_slug: str, query_text: str, k: int):
        col = self.get_or_create(author_slug)
        n = col.count()
        if n == 0:
            return {"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]}
        return col.query(query_texts=[query_text.strip()], n_results=min(max(1, k), n))
