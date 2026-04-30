from __future__ import annotations

import asyncio
import sqlite3
from typing import Any


def categorize_pipeline_exception(exc: BaseException) -> dict[str, Any]:
    """
    将异常归为稳定代号，便于 API/日志一致处理；单测对齐「错误矩阵」语义。
    """
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return {"code": "TIMEOUT", "retryable": True, "layer": "llm_or_io"}
    if isinstance(exc, sqlite3.Error):
        return {"code": "DATABASE", "retryable": False, "layer": "storage"}
    if isinstance(exc, (ConnectionError, OSError)):
        return {"code": "NETWORK_OR_OS", "retryable": True, "layer": "io"}
    if isinstance(exc, ValueError):
        return {"code": "INVALID_INPUT", "retryable": False, "layer": "validation"}
    if isinstance(exc, KeyError):
        return {"code": "NOT_FOUND", "retryable": False, "layer": "routing"}
    return {"code": "UNKNOWN", "retryable": False, "layer": "unknown"}
