from __future__ import annotations

from pathlib import Path

from app.corpus.author_profile import build_author_profile
from app.db.sqlite_schema import get_connection, init_schema


def test_empty_author_profile_handles_gracefully(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "e.db")
    init_schema(conn)
    prof = build_author_profile(conn, "ghost")
    assert prof["author_slug"] == "ghost"
    assert prof["lexical"]["note"] == "暂无语料切块"

