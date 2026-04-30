"""核心生成 Pipeline：先大纲后正文，评分三层融合（Phase 3）。"""

from app.pipeline.models import ArticleBriefNormalized, OutlineDocument

__all__ = ["ArticleBriefNormalized", "OutlineDocument"]
