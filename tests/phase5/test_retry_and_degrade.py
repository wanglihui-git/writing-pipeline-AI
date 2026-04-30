from __future__ import annotations

from app.pipeline.degrade import (
    DEGRADED_E2E_BUDGET_SECONDS,
    E2E_SLA_SECONDS,
    draft_concurrency_effective,
    e2e_runtime_budget_seconds,
)
from app.workers.tasks import flaky_demo_task, process_received_task


def test_sync_worker_functions_exist() -> None:
    assert callable(process_received_task)
    assert callable(flaky_demo_task)


def test_draft_concurrency_degrades_to_serial() -> None:
    assert draft_concurrency_effective(4, degraded=True) == 1
    assert draft_concurrency_effective(4, degraded=False) == 4


def test_draft_concurrency_caps_at_eight() -> None:
    assert draft_concurrency_effective(20, degraded=False) == 8


def test_degrade_invalid_concurrency_raises() -> None:
    try:
        draft_concurrency_effective(0, degraded=False)
        failed = False
    except ValueError:
        failed = True
    assert failed


def test_e2e_budget_within_ten_minute_gate() -> None:
    assert e2e_runtime_budget_seconds(degraded=False) <= 600
    assert e2e_runtime_budget_seconds(degraded=True) <= 600


def test_sla_constants_documented_alignment() -> None:
    """与 degrade 模块文档字符串保持同步（防回归漂移）。"""
    assert E2E_SLA_SECONDS == 600
    assert DEGRADED_E2E_BUDGET_SECONDS < E2E_SLA_SECONDS
