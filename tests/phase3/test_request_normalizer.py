from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.pipeline.request_normalizer import normalize_article_brief
from app.settings import AppYamlConfig


def test_required_fields_must_present() -> None:
    with pytest.raises(ValidationError):
        normalize_article_brief({"topic": "t", "angle": "only"})  # 缺 thesis 等


def test_chinese_aliases_and_default_word_count() -> None:
    raw = {
        "选题": "写作者风格",
        "切入角度": "冷启动",
        "核心命题": "风格可迁移",
        "论证框架": "对比实验",
        "叙事骨架": "问题-分析-建议",
        "目标读者": "独立开发者",
    }
    app = AppYamlConfig(default_word_count=7200)
    n = normalize_article_brief(raw, app_defaults=app)
    assert n.topic == "写作者风格"
    assert n.target_word_count == 7200


def test_explicit_word_count_alias() -> None:
    raw = {
        "topic": "t",
        "angle": "a",
        "thesis": "th",
        "argument_framework": "af",
        "narrative_skeleton": "ns",
        "target_audience": "r",
        "word_count": 9000,
    }
    n = normalize_article_brief(raw, app_defaults=AppYamlConfig())
    assert n.target_word_count == 9000
