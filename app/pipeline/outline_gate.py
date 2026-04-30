from __future__ import annotations

from app.domain.state_machine import TaskState
from app.services.task_store import TaskRecord


class OutlineGateError(RuntimeError):
    pass


class OutlineNotConfirmedError(OutlineGateError):
    pass


def assert_can_generate_draft(task: TaskRecord) -> None:
    """未确认大纲严禁进入正文阶段。"""
    if not task.outline_confirmed:
        raise OutlineNotConfirmedError("大纲尚未确认")
    allowed = frozenset({TaskState.WAIT_OUTLINE_CONFIRM, TaskState.FAILED})
    if task.state not in allowed:
        raise OutlineGateError(f"当前任务状态不允许开始正文生成: {task.state}")
