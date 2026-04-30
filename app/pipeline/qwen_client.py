from __future__ import annotations

import logging
import os
from typing import Any

import dashscope
from tenacity import retry, stop_after_attempt, wait_exponential

from app.pipeline.llm_protocol import ChatCompletionClient
from app.settings import get_models_config

logger = logging.getLogger(__name__)


class QwenClient(ChatCompletionClient):
    """
    DashScope 千问客户端（同步版）。
    - `complete()` 满足 `ChatCompletionClient` 协议
    - `embed()` 提供文本向量接口（兼容示例里的多返回结构）
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_base: str | None = None,
        chat_model: str | None = None,
        embedding_model: str | None = None,
    ) -> None:
        models = get_models_config()
        self.chat_model = chat_model or models.draft_model
        self.embedding_model = embedding_model or models.embedding_model

        k = api_key or os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("WRITING_QWEN_API_KEY")
        b = api_base or os.environ.get("DASHSCOPE_BASE_URL") or os.environ.get("WRITING_QWEN_API_BASE")
        if not k:
            raise ValueError("DashScope API key 缺失，请设置 DASHSCOPE_API_KEY 或 WRITING_QWEN_API_KEY")
        dashscope.api_key = k
        if b:
            dashscope.base_http_api_url = b

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        model = model_id or self.chat_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        logger.info(
            "qwen.complete model=%s temp=%.2f prompt_len=%s",
            model,
            temperature,
            len(user_prompt),
        )
        response = dashscope.Generation.call(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            result_format="message",
        )
        if response.status_code != 200:
            raise RuntimeError(f"Qwen API 错误: {response.code} - {response.message}")

        try:
            return str(response.output.choices[0].message.content)
        except Exception as e:
            raise RuntimeError(f"Qwen 响应解析失败: {e}") from e

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def embed(self, text: str, *, model_id: str | None = None) -> list[float]:
        model = model_id or self.embedding_model
        logger.debug("qwen.embed model=%s text_len=%s", model, len(text))
        response = dashscope.TextEmbedding.call(model=model, input=text)
        if response.status_code != 200:
            raise RuntimeError(f"Embedding API 错误: {response.code} - {response.message}")
        return _extract_embedding(response.output)


def _extract_embedding(output: Any) -> list[float]:
    """兼容 dict / 类 dict / 属性访问三种返回形态。"""
    try:
        emb = output["embeddings"][0]["embedding"]
        return [float(x) for x in emb]
    except Exception:
        pass
    try:
        emb = output.embeddings[0].embedding
        return [float(x) for x in emb]
    except Exception as e:
        raise RuntimeError(f"Embedding 返回结构无法解析: {e}") from e
