from __future__ import annotations

import json

from app.corpus.style_features import StyleFeatureVector, extract_style_features, split_sentences


def test_split_sentences_chinese_period() -> None:
    s = split_sentences("你好。再见！真的吗？")
    assert len(s) == 3


def extract_metrics(text: str) -> StyleFeatureVector:
    return extract_style_features(text)


def test_sentence_len_positive_on_prose() -> None:
    t = "。".join(["这是第{}句内容，稍长一点点。".format(i) for i in range(5)]) + "。"
    sf = extract_metrics(t)
    assert sf.avg_sentence_len > 5


def test_transition_boost() -> None:
    plain = "叙述。" * 8
    with_tr = plain + "因此，我们需要继续。" + "此外，还有一点。"
    sf0 = extract_style_features(plain)
    sf1 = extract_style_features(with_tr)
    assert sf1.transition_word_density >= sf0.transition_word_density


def test_punctuation_profile_json_roundtrip() -> None:
    sf = extract_style_features("你好，世界。真的？")
    punct = sf.punctuation_profile
    js = json.dumps(punct)
    back = json.loads(js)
    assert "comma" in back
