from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.domain.state_machine import InvalidStateTransitionError
from app.services.rewrite_workflow import run_full_rewrite, run_partial_rewrite
from app.services.task_store import TaskStore
from app.settings import get_app_config

router = APIRouter()


class FullRewriteBody(BaseModel):
    instruction: str = Field(default="", max_length=16_000)
    keep_facts: bool = True


class PartialRewriteBody(BaseModel):
    instruction: str = Field(default="", max_length=16_000)
    section_id: int | None = None
    paragraph_range: tuple[int, int] | None = Field(
        default=None,
        description="Inclusive global paragraph indices (by blank-line split).",
    )
    apply_context_bridge: bool = True


class RewriteResponse(BaseModel):
    task_id: str
    article_version: int
    fused_score_0_100: float | None


@router.post("/{task_id}/rewrite/full", response_model=RewriteResponse)
def rewrite_full(task_id: str, body: FullRewriteBody, request: Request) -> RewriteResponse:
    conn = request.app.state.db_conn
    store = TaskStore(conn)
    cfg = get_app_config()
    try:
        v_no, card = run_full_rewrite(
            store,
            cfg,
            task_id,
            instruction=body.instruction,
            keep_facts=body.keep_facts,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found") from None
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RewriteResponse(
        task_id=task_id,
        article_version=v_no,
        fused_score_0_100=card.fused_total_0_100,
    )


@router.post("/{task_id}/rewrite/partial", response_model=RewriteResponse)
def rewrite_partial(task_id: str, body: PartialRewriteBody, request: Request) -> RewriteResponse:
    conn = request.app.state.db_conn
    store = TaskStore(conn)
    cfg = get_app_config()
    try:
        v_no, card = run_partial_rewrite(
            store,
            cfg,
            task_id,
            instruction=body.instruction,
            section_id=body.section_id,
            paragraph_range=body.paragraph_range,
            apply_context_bridge=body.apply_context_bridge,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found") from None
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RewriteResponse(
        task_id=task_id,
        article_version=v_no,
        fused_score_0_100=card.fused_total_0_100,
    )


class HumanFeedbackBody(BaseModel):
    score_1_5: int = Field(..., ge=1, le=5)
    comment: str | None = None


@router.post("/{task_id}/feedback", summary="人工评分入库")
def post_human_feedback(task_id: str, body: HumanFeedbackBody, request: Request) -> dict[str, object]:
    store = TaskStore(request.app.state.db_conn)
    if store.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="task not found")
    try:
        rid = store.add_human_feedback(task_id, body.score_1_5, body.comment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"id": rid, "task_id": task_id}


@router.get("/{task_id}/feedback/stats", summary="评分统计")
def feedback_stats(task_id: str, request: Request) -> dict[str, object]:
    store = TaskStore(request.app.state.db_conn)
    if store.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="task not found")
    return store.feedback_stats(task_id)
