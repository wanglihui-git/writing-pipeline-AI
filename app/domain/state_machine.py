from __future__ import annotations

from enum import StrEnum


class TaskState(StrEnum):
    RECEIVED = "RECEIVED"
    OUTLINE_GENERATING = "OUTLINE_GENERATING"
    WAIT_OUTLINE_CONFIRM = "WAIT_OUTLINE_CONFIRM"
    DRAFT_GENERATING = "DRAFT_GENERATING"
    SCORING = "SCORING"
    READY = "READY"
    FAILED = "FAILED"
    # 技术方案中的改写态，Phase1 预留合法跳转目标
    REWRITING = "REWRITING"


_ALLOWED: dict[TaskState, frozenset[TaskState]] = {
    TaskState.RECEIVED: frozenset({TaskState.OUTLINE_GENERATING, TaskState.FAILED}),
    TaskState.OUTLINE_GENERATING: frozenset({TaskState.WAIT_OUTLINE_CONFIRM, TaskState.FAILED}),
    TaskState.WAIT_OUTLINE_CONFIRM: frozenset(
        {TaskState.DRAFT_GENERATING, TaskState.OUTLINE_GENERATING, TaskState.FAILED}
    ),
    TaskState.DRAFT_GENERATING: frozenset({TaskState.SCORING, TaskState.FAILED}),
    TaskState.SCORING: frozenset({TaskState.READY, TaskState.FAILED}),
    TaskState.READY: frozenset({TaskState.REWRITING, TaskState.SCORING}),
    TaskState.REWRITING: frozenset({TaskState.SCORING, TaskState.READY, TaskState.FAILED}),
    TaskState.FAILED: frozenset(
        {
            TaskState.OUTLINE_GENERATING,
            TaskState.WAIT_OUTLINE_CONFIRM,
            TaskState.DRAFT_GENERATING,
            TaskState.SCORING,
        }
    ),
}


class InvalidStateTransitionError(ValueError):
    def __init__(self, current: TaskState, target: TaskState) -> None:
        super().__init__(f"Illegal transition: {current} -> {target}")
        self.current = current
        self.target = target


def can_transition(current: TaskState, target: TaskState) -> bool:
    return target in _ALLOWED.get(current, frozenset())


def assert_transition(current: TaskState, target: TaskState) -> None:
    if not can_transition(current, target):
        raise InvalidStateTransitionError(current, target)
