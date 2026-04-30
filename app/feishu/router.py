from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from typing import Any, Callable

from app.feishu.status_push import push_task_status
from app.services.task_store import TaskStore


@dataclass
class ParsedCommand:
    name: str
    rest: str


def parse_command_text(text: str) -> ParsedCommand:
    t = (text or "").strip()
    if not t.startswith("/"):
        raise ValueError("指令必须以 / 开头")
    parts = t.split(maxsplit=1)
    raw = parts[0][1:].lower()
    rest = parts[1].strip() if len(parts) > 1 else ""
    if raw not in {"outline", "generate", "score", "feedback"}:
        raise ValueError(f"未知指令: /{raw}")
    return ParsedCommand(name=raw, rest=rest)


def parse_kv_args(rest: str) -> dict[str, str]:
    if not rest.strip():
        return {}
    try:
        tokens = shlex.split(rest.strip(), posix=True)
    except ValueError as e:
        raise ValueError(f"参数解析失败: {e}") from e
    out: dict[str, str] = {}
    for t in tokens:
        if "=" not in t:
            continue
        k, _, v = t.partition("=")
        key = k.strip().lower()
        if not key:
            continue
        out[key] = v.strip().strip('"').strip("'")
    return out


def extract_im_text_event(event: dict[str, Any]) -> tuple[str, str | None, str | None]:
    """从飞书长链接事件体中抽取文本与会话信息（兼容 tests 中的简化结构）。"""
    ev = event.get("event")
    if not isinstance(ev, dict):
        ev = event
    message = ev.get("message")
    if not isinstance(message, dict):
        raise ValueError("缺少 message")
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("message.content 必须是 JSON 字符串")
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError("message.content JSON 必须是对象")
    text = str(payload.get("text", ""))
    chat_id = ev.get("chat_id")
    if chat_id is None and isinstance(message.get("chat_id"), str):
        chat_id = message.get("chat_id")
    sender = ev.get("sender")
    open_id = None
    if isinstance(sender, dict):
        sid = sender.get("sender_id")
        if isinstance(sid, dict):
            open_id = sid.get("open_id") or sid.get("user_id")
    return text, (str(chat_id) if chat_id else None), (str(open_id) if open_id else None)


@dataclass
class FeishuHandleResult:
    ok: bool
    message: str
    task_id: str | None = None


def handle_feishu_text_message(
    text: str,
    *,
    chat_id: str | None,
    open_id: str | None,
    store: TaskStore,
    enqueue_outline: Callable[[str, str], None],
    sqlite_path: str,
    enqueue_generate: Callable[[str, str], None] | None = None,
) -> FeishuHandleResult:
    try:
        cmd = parse_command_text(text)
    except ValueError as e:
        return FeishuHandleResult(False, str(e))

    cid = chat_id or "unknown"
    kv = parse_kv_args(cmd.rest)

    if cmd.name == "outline":
        author = kv.get("author")
        if not author:
            return FeishuHandleResult(False, "/outline 需要提供 author=作者名")
        brief = {k: v for k, v in kv.items() if k != "author"}
        task_id = store.create_task(
            author=author,
            brief=brief,
            feishu_chat_id=chat_id,
        )
        enqueue_outline(task_id, sqlite_path)
        push_task_status(cid, f"任务已创建 `{task_id}`，状态：RECEIVED → 处理中")
        return FeishuHandleResult(True, f"已创建任务 `{task_id}`", task_id=task_id)

    if cmd.name in {"generate", "score"}:
        task_id = kv.get("task_id")
        if not task_id:
            return FeishuHandleResult(False, f"/{cmd.name} 需要提供 task_id=<uuid>")
        rec = store.get_task(task_id)
        if rec is None:
            return FeishuHandleResult(False, "任务不存在")
        if cmd.name == "generate" and enqueue_generate is not None:
            enqueue_generate(task_id, sqlite_path)
            push_task_status(cid, f"任务 `{task_id}` 已开始正文生成")
            return FeishuHandleResult(True, f"任务 `{task_id}` 已开始正文生成", task_id=task_id)
        push_task_status(cid, f"任务 `{task_id}` 当前状态：{rec.state}")
        return FeishuHandleResult(True, f"任务 `{task_id}` 当前状态：{rec.state}", task_id=task_id)

    if cmd.name == "feedback":
        task_id = kv.get("task_id")
        score_raw = kv.get("score") or kv.get("rating")
        if not task_id or score_raw is None:
            return FeishuHandleResult(False, "/feedback 需要提供 task_id= 与 score= 或 rating= （1~5）")
        rec = store.get_task(task_id)
        if rec is None:
            return FeishuHandleResult(False, "任务不存在")
        try:
            n = int(str(score_raw).strip())
            store.add_human_feedback(task_id, n)
        except ValueError as e:
            return FeishuHandleResult(False, str(e))
        push_task_status(cid, f"已记录人工评分 {n}/5，`{task_id}`")
        stats = store.feedback_stats(task_id)
        return FeishuHandleResult(True, f"评分已入库；当前平均分 {stats.get('avg_1_5')}", task_id=task_id)

    return FeishuHandleResult(False, "未处理指令")


def process_im_event_v1(
    event: dict[str, Any],
    *,
    store: TaskStore,
    enqueue_outline: Callable[[str, str], None],
    sqlite_path: str,
    enqueue_generate: Callable[[str, str], None] | None = None,
) -> dict[str, Any]:
    text, chat_id, open_id = extract_im_text_event(event)
    res = handle_feishu_text_message(
        text,
        chat_id=chat_id,
        open_id=open_id,
        store=store,
        enqueue_outline=enqueue_outline,
        sqlite_path=sqlite_path,
        enqueue_generate=enqueue_generate,
    )
    return {"ok": res.ok, "message": res.message, "task_id": res.task_id}
