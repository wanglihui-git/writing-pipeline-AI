from __future__ import annotations

import types

import pytest

from app.pipeline.qwen_client import QwenClient, _extract_embedding


class _Resp:
    def __init__(self, status_code: int, output: object, code: str = "err", message: str = "bad") -> None:
        self.status_code = status_code
        self.output = output
        self.code = code
        self.message = message


def test_extract_embedding_supports_dict_and_attr() -> None:
    out_dict = {"embeddings": [{"embedding": [0.1, 0.2]}]}
    assert _extract_embedding(out_dict) == [0.1, 0.2]

    out_obj = types.SimpleNamespace(
        embeddings=[types.SimpleNamespace(embedding=[1, 2, 3])],
    )
    assert _extract_embedding(out_obj) == [1.0, 2.0, 3.0]


def test_qwen_complete_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dummy")
    from app.pipeline import qwen_client as mod

    def _call(**kwargs: object) -> _Resp:
        _ = kwargs
        msg = types.SimpleNamespace(content="hello")
        choice = types.SimpleNamespace(message=msg)
        out = types.SimpleNamespace(choices=[choice])
        return _Resp(200, out)

    monkeypatch.setattr(mod.dashscope.Generation, "call", _call)
    c = QwenClient()
    got = c.complete(system_prompt="sys", user_prompt="u", model_id="qwen-plus")
    assert got == "hello"


def test_qwen_embed_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dummy")
    from app.pipeline import qwen_client as mod

    def _emb_call(**kwargs: object) -> _Resp:
        _ = kwargs
        return _Resp(200, {"embeddings": [{"embedding": [0.9, 0.8]}]})

    monkeypatch.setattr(mod.dashscope.TextEmbedding, "call", _emb_call)
    c = QwenClient()
    emb = c.embed("abc")
    assert emb == [0.9, 0.8]


def test_qwen_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("WRITING_QWEN_API_KEY", raising=False)
    with pytest.raises(ValueError):
        QwenClient()
