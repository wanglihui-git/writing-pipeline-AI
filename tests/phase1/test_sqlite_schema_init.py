from __future__ import annotations

from pathlib import Path

from app.db.sqlite_schema import get_connection, init_schema


def test_init_schema_creates_core_tables(tmp_path: Path) -> None:
    db = tmp_path / "m.db"
    conn = get_connection(db)
    init_schema(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = {r[0] for r in rows}
    assert {"tasks", "task_versions", "scores", "feedback", "schema_meta"}.issubset(names)
    conn.close()


def test_init_schema_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "m2.db"
    conn = get_connection(db)
    init_schema(conn)
    init_schema(conn)
    conn.execute("SELECT 1 FROM tasks LIMIT 1")
    conn.close()
