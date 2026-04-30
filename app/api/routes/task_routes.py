from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.domain.state_machine import TaskState
from app.pipeline.models import OutlineDocument
from app.services.task_store import TaskStore
from app.workers.tasks import process_generate_task, process_received_task

router = APIRouter()


class CreateTaskBody(BaseModel):
    author: str | None = None
    brief: dict[str, Any] = Field(default_factory=dict)
    feishu_chat_id: str | None = None


class TaskResponse(BaseModel):
    task_id: str
    state: TaskState
    author: str | None
    brief: dict[str, Any]
    outline_confirmed: bool
    created_at: str
    updated_at: str


class LatestArticleResponse(BaseModel):
    task_id: str
    article_version: int
    sections_body: list[str]
    concatenated_raw: str
    concatenated_polished: str


class LatestOutlineResponse(BaseModel):
    task_id: str
    outline_version: int
    outline_confirmed: bool
    outline: OutlineDocument


class TaskActionResponse(BaseModel):
    task_id: str
    message: str


@router.post("/", response_model=dict[str, str], summary="创建写作任务")
def create_task(body: CreateTaskBody, request: Request) -> dict[str, str]:
    conn = request.app.state.db_conn
    store = TaskStore(conn)
    task_id = store.create_task(
        author=body.author,
        brief=body.brief,
        feishu_chat_id=body.feishu_chat_id,
    )
    sqlite_path: str = request.app.state.sqlite_path
    process_received_task(task_id, sqlite_path)
    return {"task_id": task_id}


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, request: Request) -> TaskResponse:
    conn = request.app.state.db_conn
    store = TaskStore(conn)
    rec = store.get_task(task_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskResponse(
        task_id=rec.task_id,
        state=rec.state,
        author=rec.author,
        brief=rec.brief,
        outline_confirmed=rec.outline_confirmed,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
    )


@router.get("/{task_id}/outline/latest", response_model=LatestOutlineResponse, summary="获取任务最新大纲")
def get_latest_outline(task_id: str, request: Request) -> LatestOutlineResponse:
    conn = request.app.state.db_conn
    store = TaskStore(conn)
    rec = store.get_task(task_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="task not found")
    outline = store.fetch_latest_outline_document(task_id)
    if outline is None:
        raise HTTPException(status_code=404, detail="outline not found")
    return LatestOutlineResponse(
        task_id=task_id,
        outline_version=store.latest_outline_version_no(task_id),
        outline_confirmed=rec.outline_confirmed,
        outline=outline,
    )


@router.get("/{task_id}/article/latest", response_model=LatestArticleResponse, summary="获取任务最新正文")
def get_latest_article(task_id: str, request: Request) -> LatestArticleResponse:
    conn = request.app.state.db_conn
    store = TaskStore(conn)
    if store.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="task not found")
    bundle = store.fetch_latest_article_bundle(task_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="article not found")
    version = store.latest_article_version_no(task_id)
    return LatestArticleResponse(
        task_id=task_id,
        article_version=version,
        sections_body=bundle.sections_body,
        concatenated_raw=bundle.concatenated_raw,
        concatenated_polished=bundle.concatenated_polished,
    )


@router.post("/{task_id}/outline/confirm", response_model=TaskActionResponse, summary="确认当前最新大纲")
def confirm_outline(task_id: str, request: Request) -> TaskActionResponse:
    conn = request.app.state.db_conn
    store = TaskStore(conn)
    rec = store.get_task(task_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="task not found")
    if store.fetch_latest_outline_document(task_id) is None:
        raise HTTPException(status_code=400, detail="outline not found")
    store.confirm_outline(task_id)
    return TaskActionResponse(task_id=task_id, message="outline confirmed")


@router.post("/{task_id}/generate", response_model=TaskActionResponse, summary="基于已确认大纲生成正文")
def generate_article(task_id: str, request: Request) -> TaskActionResponse:
    conn = request.app.state.db_conn
    store = TaskStore(conn)
    rec = store.get_task(task_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="task not found")
    if not rec.outline_confirmed:
        raise HTTPException(status_code=409, detail="outline not confirmed")
    sqlite_path: str = request.app.state.sqlite_path
    process_generate_task(task_id, sqlite_path)
    return TaskActionResponse(task_id=task_id, message="article generated")
