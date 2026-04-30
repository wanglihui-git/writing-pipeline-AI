from __future__ import annotations

from typing import Any

from app.pipeline.models import ArticleBriefNormalized
from app.settings import AppYamlConfig


_MISSING = object()


def normalize_article_brief(raw: dict[str, Any], *, app_defaults: AppYamlConfig | None = None) -> ArticleBriefNormalized:
    """
    将 API/飞书 brief 映射为结构化请求；必填缺失抛 ValidationError；
    word_count -> target_word_count 默认取自 app_defaults。
    """
    app_defaults = app_defaults or AppYamlConfig()
    aliases = {
        "选题": "topic",
        "切入角度": "angle",
        "核心命题": "thesis",
        "论证框架": "argument_framework",
        "叙事骨架": "narrative_skeleton",
        "目标读者": "target_audience",
    }
    data = dict(raw)
    for zh, en in aliases.items():
        if en not in data and zh in data and data.get(zh) is not None:
            data[en] = data[zh]

    if "target_word_count" not in data:
        wc = data.get("word_count", _MISSING)
        if wc is _MISSING:
            data["target_word_count"] = app_defaults.default_word_count
        else:
            data["target_word_count"] = int(wc)

    return ArticleBriefNormalized.model_validate(data)
