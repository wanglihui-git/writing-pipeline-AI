from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 3

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    author TEXT,
    brief_json TEXT,
    feishu_chat_id TEXT,
    feishus_open_id TEXT,
    outline_confirmed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS task_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    version_no INTEGER NOT NULL DEFAULT 1,
    storage_path TEXT,
    content TEXT,
    meta_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(task_id, kind, version_no)
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    task_version_id INTEGER REFERENCES task_versions(id) ON DELETE SET NULL,
    score_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    score_1_5 INTEGER NOT NULL,
    comment TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK(score_1_5 >= 1 AND score_1_5 <= 5)
);

CREATE INDEX IF NOT EXISTS idx_task_versions_task ON task_versions(task_id);
CREATE INDEX IF NOT EXISTS idx_scores_task ON scores(task_id);
CREATE INDEX IF NOT EXISTS idx_feedback_task ON feedback(task_id);

CREATE TABLE IF NOT EXISTS authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    display_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS corpus_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_slug TEXT NOT NULL,
    source_relpath TEXT NOT NULL,
    title TEXT,
    body_sha256 TEXT NOT NULL,
    char_count INTEGER NOT NULL DEFAULT 0,
    clean_jsonl_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(author_slug, source_relpath)
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES corpus_documents(id) ON DELETE CASCADE,
    author_slug TEXT NOT NULL,
    kind TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    text TEXT NOT NULL,
    char_len INTEGER NOT NULL,
    meta_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS style_features (
    chunk_id INTEGER PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
    avg_sentence_len REAL NOT NULL,
    long_short_ratio REAL NOT NULL,
    punctuation_profile_json TEXT NOT NULL,
    transition_word_density REAL NOT NULL,
    rhetoric_density REAL NOT NULL,
    first_person_ratio REAL NOT NULL,
    assertiveness_score REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_corpus_docs_author ON corpus_documents(author_slug);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_author ON chunks(author_slug);

CREATE TABLE IF NOT EXISTS corpus_jobs (
    job_id TEXT PRIMARY KEY,
    author_slug TEXT NOT NULL,
    source_path TEXT,
    status TEXT NOT NULL,
    files_found INTEGER NOT NULL DEFAULT 0,
    files_processed INTEGER NOT NULL DEFAULT 0,
    chunks_indexed INTEGER NOT NULL DEFAULT 0,
    skipped_json TEXT,
    profile_json TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_corpus_jobs_author ON corpus_jobs(author_slug);
CREATE INDEX IF NOT EXISTS idx_corpus_jobs_status ON corpus_jobs(status);
"""


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    p = Path(db_path)
    _ensure_parent(p)
    conn = sqlite3.connect(str(p), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(DDL)
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    conn.commit()
