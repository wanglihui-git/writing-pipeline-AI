from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.domain.state_machine import InvalidStateTransitionError, TaskState, assert_transition
from app.pipeline.models import DraftBundle, OutlineDocument, ScoreCard


def _now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


@dataclass
class TaskRecord:
    task_id: str
    state: TaskState
    author: str | None
    brief: dict[str, Any]
    feishu_chat_id: str | None
    outline_confirmed: bool
    created_at: str
    updated_at: str


class TaskStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_task(
        self,
        *,
        author: str | None = None,
        brief: dict[str, Any] | None = None,
        feishu_chat_id: str | None = None,
        initial_state: TaskState = TaskState.RECEIVED,
    ) -> str:
        task_id = str(uuid.uuid4())
        brief = brief or {}
        self._conn.execute(
            """
            INSERT INTO tasks (task_id, state, author, brief_json, feishu_chat_id, outline_confirmed, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                task_id,
                str(initial_state),
                author,
                json.dumps(brief, ensure_ascii=False),
                feishu_chat_id,
                _now_iso(),
                _now_iso(),
            ),
        )
        self._conn.commit()
        return task_id

    def get_task(self, task_id: str) -> TaskRecord | None:
        row = self._conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def set_state(self, task_id: str, new_state: TaskState) -> None:
        row = self._conn.execute("SELECT state FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        current = TaskState(row["state"])
        assert_transition(current, new_state)
        self._conn.execute(
            "UPDATE tasks SET state = ?, updated_at = ? WHERE task_id = ?",
            (str(new_state), _now_iso(), task_id),
        )
        self._conn.commit()

    def try_set_state(self, task_id: str, new_state: TaskState) -> bool:
        try:
            self.set_state(task_id, new_state)
        except (KeyError, InvalidStateTransitionError):
            return False
        return True

    def force_state(self, task_id: str, new_state: TaskState) -> None:
        """内部恢复用：跳过状态机（仅 worker / 管理路径）。"""
        self._conn.execute(
            "UPDATE tasks SET state = ?, updated_at = ? WHERE task_id = ?",
            (str(new_state), _now_iso(), task_id),
        )
        self._conn.commit()

    def latest_outline_version_no(self, task_id: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(version_no), 0) AS m FROM task_versions WHERE task_id = ? AND kind = 'outline'",
            (task_id,),
        ).fetchone()
        return int(row["m"]) if row else 0

    def persist_outline_revision(self, task_id: str, outline: OutlineDocument, *, model_id: str) -> int:
        """插入新版本大纲，并将 outline_confirmed 置 0。"""
        v = self.latest_outline_version_no(task_id) + 1
        meta_json = json.dumps({"model_id": model_id}, ensure_ascii=False)
        body = outline.model_dump_json()
        self._conn.execute(
            """
            INSERT INTO task_versions(task_id, kind, version_no, storage_path, content, meta_json)
            VALUES(?, 'outline', ?, NULL, ?, ?)
            """,
            (task_id, v, body, meta_json),
        )
        self._conn.execute(
            "UPDATE tasks SET outline_confirmed = 0, updated_at = ? WHERE task_id = ?",
            (_now_iso(), task_id),
        )
        self._conn.commit()
        return v

    def confirm_outline(self, task_id: str) -> None:
        self._conn.execute(
            "UPDATE tasks SET outline_confirmed = 1, updated_at = ? WHERE task_id = ?",
            (_now_iso(), task_id),
        )
        self._conn.commit()

    def fetch_latest_outline_document(self, task_id: str) -> OutlineDocument | None:
        row = self._conn.execute(
            """
            SELECT content FROM task_versions WHERE task_id = ? AND kind = 'outline'
            ORDER BY version_no DESC LIMIT 1
            """,
            (task_id,),
        ).fetchone()
        if not row or not row["content"]:
            return None
        return OutlineDocument.model_validate_json(row["content"])

    def latest_article_version_no(self, task_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT COALESCE(MAX(version_no), 0) AS m FROM task_versions
            WHERE task_id = ? AND kind = 'article'
            """,
            (task_id,),
        ).fetchone()
        return int(row["m"]) if row else 0

    def fetch_latest_article_bundle(self, task_id: str) -> DraftBundle | None:
        row = self._conn.execute(
            """
            SELECT content FROM task_versions WHERE task_id = ? AND kind = 'article'
            ORDER BY version_no DESC LIMIT 1
            """,
            (task_id,),
        ).fetchone()
        if not row or not row["content"]:
            return None
        return DraftBundle.model_validate_json(row["content"])

    def fetch_article_bundle_version(self, task_id: str, version_no: int) -> DraftBundle | None:
        row = self._conn.execute(
            """
            SELECT content FROM task_versions
            WHERE task_id = ? AND kind = 'article' AND version_no = ?
            """,
            (task_id, version_no),
        ).fetchone()
        if not row or not row["content"]:
            return None
        return DraftBundle.model_validate_json(row["content"])

    def _task_versions_pk(self, task_id: str, kind: str, version_no: int) -> int | None:
        row = self._conn.execute(
            "SELECT id FROM task_versions WHERE task_id = ? AND kind = ? AND version_no = ?",
            (task_id, kind, version_no),
        ).fetchone()
        return int(row["id"]) if row else None

    def persist_article_bundle(
        self,
        task_id: str,
        bundle: DraftBundle,
        *,
        rewrite_mode: str,
        paragraphs_touched: list[int] | None,
        artifact_dir: Path,
    ) -> tuple[int, int]:
        prev_v = self.latest_article_version_no(task_id)
        v = prev_v + 1
        prev_text = None
        if prev_v > 0:
            prev_b = self.fetch_article_bundle_version(task_id, prev_v)
            prev_text = prev_b.concatenated_polished if prev_b else None
        artifact_dir.mkdir(parents=True, exist_ok=True)
        body = bundle.model_dump_json()
        meta = json.dumps({"rewrite_mode": rewrite_mode}, ensure_ascii=False)
        self._conn.execute(
            """
            INSERT INTO task_versions(task_id, kind, version_no, storage_path, content, meta_json)
            VALUES(?, 'article', ?, ?, ?, ?)
            """,
            (
                task_id,
                v,
                str(artifact_dir / f"article_v{v}.txt"),
                body,
                meta,
            ),
        )
        self._conn.commit()
        vid = self._task_versions_pk(task_id, "article", v)
        if vid is None:
            raise RuntimeError("failed to resolve article version row id")

        polished = bundle.concatenated_polished
        (artifact_dir / f"article_v{v}.txt").write_text(polished, encoding="utf-8")
        diff_summary: dict[str, Any] = {
            "previous_version_no": prev_v if prev_v else None,
            "new_version_no": v,
            "rewrite_mode": rewrite_mode,
            "chars_before": len(prev_text or ""),
            "chars_after": len(polished),
            "paragraphs_touched": paragraphs_touched or [],
        }
        (artifact_dir / f"rewrite_diff_v{v}.json").write_text(
            json.dumps(diff_summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._conn.execute(
            "UPDATE tasks SET updated_at = ? WHERE task_id = ?",
            (_now_iso(), task_id),
        )
        self._conn.commit()
        return v, vid

    def persist_score_card(
        self, task_id: str, *, task_version_id: int | None, card: ScoreCard
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO scores(task_id, task_version_id, score_json)
            VALUES(?,?,?)
            """,
            (task_id, task_version_id, card.model_dump_json()),
        )
        self._conn.commit()

    def add_human_feedback(self, task_id: str, score_1_5: int, comment: str | None = None) -> int:
        if score_1_5 < 1 or score_1_5 > 5:
            raise ValueError("score must be 1..5")
        cur = self._conn.execute(
            """
            INSERT INTO feedback(task_id, score_1_5, comment)
            VALUES(?,?,?)
            """,
            (task_id, score_1_5, comment),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def feedback_stats(self, task_id: str) -> dict[str, Any]:
        rows = self._conn.execute(
            """
            SELECT score_1_5 AS s, COUNT(*) AS c FROM feedback
            WHERE task_id = ?
            GROUP BY score_1_5
            """,
            (task_id,),
        ).fetchall()
        dist = {int(r["s"]): int(r["c"]) for r in rows}
        total = sum(dist.values())
        avg_row = self._conn.execute(
            """
            SELECT AVG(score_1_5) AS a FROM feedback WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()
        avg = float(avg_row["a"]) if avg_row and avg_row["a"] is not None else 0.0
        latest = self._conn.execute(
            """
            SELECT score_1_5, comment, created_at FROM feedback
            WHERE task_id = ? ORDER BY id DESC LIMIT 5
            """,
            (task_id,),
        ).fetchall()
        return {
            "task_id": task_id,
            "count": total,
            "avg_1_5": round(avg, 4) if total else None,
            "distribution": dist,
            "latest": [{"score": int(r["score_1_5"]), "comment": r["comment"], "created_at": r["created_at"]} for r in latest],
        }

    def _row_to_record(self, row: sqlite3.Row) -> TaskRecord:
        brief_raw = row["brief_json"] or "{}"
        try:
            brief = json.loads(brief_raw)
        except json.JSONDecodeError:
            brief = {}
        return TaskRecord(
            task_id=row["task_id"],
            state=TaskState(row["state"]),
            author=row["author"],
            brief=brief if isinstance(brief, dict) else {},
            feishu_chat_id=row["feishu_chat_id"],
            outline_confirmed=bool(row["outline_confirmed"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
