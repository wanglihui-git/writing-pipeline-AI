from __future__ import annotations

import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)

_messages: list[tuple[str, str]] = []
_live_message_sender: Callable[[str, str], None] | None = None


def configure_live_message_sender(sender: Callable[[str, str], None] | None) -> None:
    """
    可选：设置真实消息投递（如 FeishuOpenApiClient.send_text_auto_id_type）。
    单测与无凭证环境不配置，则仅保留内存队列 `_messages`。
    """
    global _live_message_sender
    _live_message_sender = sender


def push_task_status(chat_id: str, message: str) -> None:
    """内存记录 + 可选调用飞书 OpenAPI 发到会话。"""
    _messages.append((chat_id, message))
    if _live_message_sender and chat_id and chat_id != "unknown":
        try:
            _live_message_sender(chat_id, message)
        except Exception:
            logger.exception("live message push failed chat_id=%s", chat_id[:16])


def drain_pushed_messages() -> list[tuple[str, str]]:
    out = list(_messages)
    _messages.clear()
    return out


def peek_pushed_messages() -> list[tuple[str, str]]:
    return list(_messages)


# --- Phase 4：阶段进度与百分比节流（可单测重置） ---
_throttle: dict[tuple[str, str], tuple[float, float]] = {}

# (min_seconds_between_pct, min_percent_step)
_PERCENT_THROTTLE = (2.5, 5.0)


def reset_progress_notifications() -> None:
    """测试用：清空节流状态。"""
    _throttle.clear()


def push_task_phase(chat_id: str | None, task_id: str, phase: str, detail: str = "") -> None:
    cid = chat_id or "unknown"
    body = f"任务 `{task_id}` · 阶段：**{phase}**"
    if detail:
        body += f"\n{detail}"
    push_task_status(cid, body)


def push_generation_percent(
    chat_id: str | None,
    task_id: str,
    percent: float,
    *,
    now_mono: Callable[[], float] = time.monotonic,
    min_seconds: float | None = None,
    min_step: float | None = None,
) -> bool:
    """
    正文生成百分比提示；节流：同一时间序列下过密或过小步进则被丢弃。
    返回是否实际写入了一条推送。
    """
    cid = chat_id or "unknown"
    pct = max(0.0, min(100.0, float(percent)))
    key = (cid, task_id)
    mn = min_seconds if min_seconds is not None else _PERCENT_THROTTLE[0]
    ms = min_step if min_step is not None else _PERCENT_THROTTLE[1]

    prev = _throttle.get(key)
    t_now = now_mono()
    if prev:
        prev_t, prev_p = prev
        if pct < 100.0 and pct > 0.0:
            if (t_now - prev_t) < mn and abs(pct - prev_p) < ms:
                return False

    msg = f"任务 `{task_id}` · 正文进度 **{pct:.0f}%**"
    push_task_status(cid, msg)
    _throttle[key] = (t_now, pct)
    return True
