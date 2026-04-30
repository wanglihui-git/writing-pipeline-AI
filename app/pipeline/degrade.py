from __future__ import annotations

# MVP：常规链路目标 <= 10 分钟（见 Phase 5 验收）；单元测试用常量守卫，非真实预测。
E2E_SLA_SECONDS = 600
DEGRADED_E2E_BUDGET_SECONDS = 480


def draft_concurrency_effective(desired: int, *, degraded: bool) -> int:
    """高负载降级：强制串行章节生成，降低外部 API 并发压力。"""
    if desired < 1:
        raise ValueError("desired concurrency must be >= 1")
    if degraded:
        return 1
    return min(desired, 8)


def e2e_runtime_budget_seconds(*, degraded: bool) -> float:
    """文档化 SLA 上限（秒）；降级路径预留略宽松排队余量。"""
    return float(DEGRADED_E2E_BUDGET_SECONDS if degraded else E2E_SLA_SECONDS)
