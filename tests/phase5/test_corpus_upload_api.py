from __future__ import annotations

import json
import uuid

from fastapi.testclient import TestClient


def test_corpus_upload_processes_synchronously(client: TestClient) -> None:
    resp = client.post(
        "/corpus/upload",
        data={"author_slug": "demo_author"},
        files={"file": ("demo.txt", b"hello corpus", "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"SUCCEEDED", "FAILED"}
    row = client.app.state.db_conn.execute("SELECT status FROM corpus_jobs WHERE job_id = ?", (body["job_id"],)).fetchone()
    assert row is not None
    assert row["status"] == body["status"]


def test_corpus_upload_invalid_author_and_ext(client: TestClient) -> None:
    bad_author = client.post(
        "/corpus/upload",
        data={"author_slug": "a/b"},
        files={"file": ("demo.txt", b"hi", "text/plain")},
    )
    assert bad_author.status_code == 400

    bad_ext = client.post(
        "/corpus/upload",
        data={"author_slug": "ok_author"},
        files={"file": ("demo.md", b"hi", "text/plain")},
    )
    assert bad_ext.status_code == 400


def test_corpus_job_and_profile_query(client: TestClient) -> None:
    conn = client.app.state.db_conn
    job_id = str(uuid.uuid4())
    profile = {"author_slug": "a1", "lexical": {"top_character_bigrams": ["人工"]}}
    conn.execute(
        """
        INSERT INTO corpus_jobs(job_id, author_slug, source_path, status, files_found, files_processed, chunks_indexed, profile_json, created_at, updated_at)
        VALUES(?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))
        """,
        (job_id, "a1", "x.txt", "SUCCEEDED", 1, 1, 3, json.dumps(profile, ensure_ascii=False)),
    )
    conn.commit()

    job_resp = client.get(f"/corpus/jobs/{job_id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] == "SUCCEEDED"

    profile_resp = client.get("/corpus/authors/a1/profile")
    assert profile_resp.status_code == 200
    assert profile_resp.json()["author_slug"] == "a1"
