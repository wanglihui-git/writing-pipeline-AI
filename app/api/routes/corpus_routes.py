from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.paths import corpus_raw_root
from app.settings import get_app_config
from app.workers.tasks import process_corpus_ingest

router = APIRouter()

_AUTHOR_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _safe_author_slug(slug: str) -> str:
    s = slug.strip()
    if not _AUTHOR_RE.match(s):
        raise ValueError("author_slug 仅允许字母/数字/_/- 且长度 1..64")
    return s


@router.post("/upload", summary="上传作者语料 txt 并触发入库")
async def upload_corpus_file(
    request: Request,
    author_slug: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, str]:
    try:
        slug = _safe_author_slug(author_slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    filename = file.filename or "upload.txt"
    if not filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="仅支持 .txt 文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件过大，限制 5MB")

    cfg = get_app_config()
    raw_root = corpus_raw_root(cfg) / slug
    raw_root.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name
    target = raw_root / f"{uuid.uuid4().hex[:8]}_{safe_name}"
    target.write_bytes(content)

    conn = request.app.state.db_conn
    job_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO corpus_jobs(job_id, author_slug, source_path, status, created_at, updated_at)
        VALUES(?,?,?,?,datetime('now'),datetime('now'))
        """,
        (job_id, slug, str(target), "PENDING"),
    )
    conn.commit()

    sqlite_path: str = request.app.state.sqlite_path
    process_corpus_ingest(job_id, slug, sqlite_path)
    row = conn.execute("SELECT status FROM corpus_jobs WHERE job_id = ?", (job_id,)).fetchone()
    return {"job_id": job_id, "author_slug": slug, "status": str(row["status"] if row else "UNKNOWN")}


@router.get("/jobs/{job_id}", summary="查询语料入库任务")
def get_corpus_job(job_id: str, request: Request) -> dict:
    conn = request.app.state.db_conn
    row = conn.execute("SELECT * FROM corpus_jobs WHERE job_id = ?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="corpus job not found")
    skipped = json.loads(row["skipped_json"]) if row["skipped_json"] else []
    return {
        "job_id": row["job_id"],
        "author_slug": row["author_slug"],
        "status": row["status"],
        "files_found": int(row["files_found"] or 0),
        "files_processed": int(row["files_processed"] or 0),
        "chunks_indexed": int(row["chunks_indexed"] or 0),
        "skipped": skipped,
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.get("/authors/{author_slug}/profile", summary="查询作者画像")
def get_author_profile(author_slug: str, request: Request) -> dict:
    conn = request.app.state.db_conn
    row = conn.execute(
        """
        SELECT profile_json FROM corpus_jobs
        WHERE author_slug = ? AND status = 'SUCCEEDED' AND profile_json IS NOT NULL
        ORDER BY updated_at DESC LIMIT 1
        """,
        (author_slug,),
    ).fetchone()
    if row is None or not row["profile_json"]:
        raise HTTPException(status_code=404, detail="author profile not found")
    return json.loads(row["profile_json"])
