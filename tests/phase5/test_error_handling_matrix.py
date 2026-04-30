from __future__ import annotations

import asyncio
import sqlite3

import pytest

from app.corpus.retrieval import retrieve_style_anchors
from app.domain.pipeline_errors import categorize_pipeline_exception


def test_categorize_timeout_builtin() -> None:
    meta = categorize_pipeline_exception(TimeoutError("llm stalled"))
    assert meta["code"] == "TIMEOUT"
    assert meta["retryable"] is True


def test_categorize_asyncio_timeout_aliases_builtin() -> None:
    meta = categorize_pipeline_exception(asyncio.TimeoutError())
    assert meta["code"] == "TIMEOUT"


def test_categorize_sqlite() -> None:
    meta = categorize_pipeline_exception(sqlite3.OperationalError("locked"))
    assert meta["code"] == "DATABASE"
    assert meta["retryable"] is False


def test_categorize_value_error_vs_key_error() -> None:
    assert categorize_pipeline_exception(ValueError("bad"))["code"] == "INVALID_INPUT"
    assert categorize_pipeline_exception(KeyError("tid"))["code"] == "NOT_FOUND"


def test_retrieval_empty_gracefully_without_crash(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """向量/语料为空时retrieve退化为 []，不抛上层异常。"""
    import app.db.sqlite_schema as sqlite_mod

    db = tmp_path / "corp.sqlite"
    conn = sqlite_mod.get_connection(db)
    sqlite_mod.init_schema(conn)

    class _StubIndex:
        def query_semantic(self, author_slug: str, query_text: str, top_k: int) -> dict:
            return {"ids": [[]], "metadatas": [[]]}

    anchors = retrieve_style_anchors(conn, _StubIndex(), "ghost", "query", top_k=4, top_n=2, semantic_weight=0.5)
    assert anchors == []
    conn.close()
