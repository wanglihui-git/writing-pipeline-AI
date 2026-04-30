from __future__ import annotations

import logging
import os

from app.pipeline.llm_protocol import ChatCompletionClient
from app.pipeline.qwen_client import QwenClient

logger = logging.getLogger(__name__)


def _has_dashscope_key() -> bool:
    return bool(
        os.environ.get("DASHSCOPE_API_KEY")
        or os.environ.get("WRITING_QWEN_API_KEY")
    )


def get_default_chat_client() -> ChatCompletionClient | None:
    """
    默认 Chat 客户端工厂：
    - 配置了 DashScope Key：返回 QwenClient
    - 未配置：返回 None（调用方走本地兜底逻辑）
    """
    if not _has_dashscope_key():
        return None
    try:
        return QwenClient()
    except Exception as exc:
        logger.warning("init default qwen client failed: %s", exc)
        return None
