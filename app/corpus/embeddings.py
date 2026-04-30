from __future__ import annotations

import hashlib
from typing import Any, Dict

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings


class DeterministicHashEmbedding(EmbeddingFunction[Documents]):
    """无外部模型依赖的确定性向量，便于单测与本机离线 Chroma。"""

    def __init__(self, dimension: int = 384):
        super().__init__()
        if dimension < 8:
            raise ValueError("dimension 过小")
        self.dimension = dimension

    @staticmethod
    def name() -> str:
        return "deterministic_hash_v1"

    def __call__(self, input: Documents) -> Embeddings:
        texts = list(input) if not isinstance(input, list) else input
        out: Embeddings = []
        for doc in texts:
            h = hashlib.sha256(doc.encode("utf-8")).digest()
            repeat = (self.dimension + len(h) - 1) // len(h)
            raw = bytearray(h * repeat)[: self.dimension]
            vec = [(b - 128.0) / 128.0 for b in raw]
            out.append(vec)
        return out

    def get_config(self) -> Dict[str, Any]:
        return {"dimension": self.dimension}

    @staticmethod
    def build_from_config(config: Dict[str, Any]) -> "DeterministicHashEmbedding":
        return DeterministicHashEmbedding(dimension=int(config.get("dimension", 384)))
