from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ChatCompletionClient(Protocol):
    """可替换的实现：DashScope/OpenAI Stub 等。"""

    def complete(self, *, system_prompt: str, user_prompt: str, model_id: str) -> str:
        ...
