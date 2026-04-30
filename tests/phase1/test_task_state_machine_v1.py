from __future__ import annotations

import pytest

from app.domain.state_machine import (
    InvalidStateTransitionError,
    TaskState,
    assert_transition,
    can_transition,
)


def test_happy_path_transitions() -> None:
    assert can_transition(TaskState.RECEIVED, TaskState.OUTLINE_GENERATING)
    assert_transition(TaskState.RECEIVED, TaskState.OUTLINE_GENERATING)
    assert_transition(TaskState.OUTLINE_GENERATING, TaskState.WAIT_OUTLINE_CONFIRM)
    assert_transition(TaskState.WAIT_OUTLINE_CONFIRM, TaskState.DRAFT_GENERATING)
    assert_transition(TaskState.DRAFT_GENERATING, TaskState.SCORING)
    assert_transition(TaskState.SCORING, TaskState.READY)


def test_wait_outline_can_regenerate_outline() -> None:
    assert can_transition(TaskState.WAIT_OUTLINE_CONFIRM, TaskState.OUTLINE_GENERATING)


def test_illegal_skip_outline_confirm() -> None:
    assert not can_transition(TaskState.WAIT_OUTLINE_CONFIRM, TaskState.READY)
    with pytest.raises(InvalidStateTransitionError):
        assert_transition(TaskState.RECEIVED, TaskState.READY)


def test_received_to_scoring_illegal() -> None:
    with pytest.raises(InvalidStateTransitionError):
        assert_transition(TaskState.RECEIVED, TaskState.SCORING)
