from __future__ import annotations

from pathlib import Path

import yaml
import pytest
from pydantic import ValidationError

from app.settings import (
    clear_settings_cache,
    load_app_yaml,
    load_models_yaml,
    merge_app_with_runtime,
    RuntimeSettings,
)


def test_app_yaml_ignores_unknown_keys_nested_and_root(tmp_path: Path) -> None:
    d = tmp_path / "config"
    d.mkdir()
    (d / "app.yaml").write_text(
        yaml.dump(
            {
                "sqlite_path": "data/custom.db",
                "chroma_path": "data/chroma",
                "tasks_data_dir": "data/tasks",
                "corpus_raw_subdir": "data/raw",
                "corpus_clean_subdir": "data/clean",
                "default_word_count": 4500,
                "future_beta_feature": {"enabled": False},
                "chunk": {"slide_min_chars": 410, "_deprecated_block": True},
                "retrieval": {"chroma_top_k": 30},
                "task_retry": {},
                "feishu": {},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    cfg = load_app_yaml(d)
    assert cfg.default_word_count == 4500
    assert cfg.chunk.slide_min_chars == 410
    assert cfg.retrieval.chroma_top_k == 30
    assert not hasattr(cfg, "future_beta_feature")


def test_models_yaml_ignores_unknown_fields(tmp_path: Path) -> None:
    d = tmp_path / "mcfg"
    d.mkdir()
    (d / "models.yaml").write_text(
        yaml.dump(
            {
                "outline_model": "m1",
                "draft_model": "m2",
                "polish_model": "m3",
                "judge_model": "m4",
                "embedding_model": "m5",
                "deprecated_alias": "x",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    m = load_models_yaml(d)
    assert m.outline_model == "m1"


def test_models_yaml_strict_required_fields(tmp_path: Path) -> None:
    d = tmp_path / "mcfg2"
    d.mkdir()
    (d / "models.yaml").write_text(yaml.dump({"outline_model": "only"}, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_models_yaml(d)


def test_merge_runtime_preserves_yaml_defaults_for_unset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parent.parent.parent
    monkeypatch.setenv("WRITING_PIPELINE_ROOT", str(repo))
    clear_settings_cache()
    d = tmp_path / "ecfg"
    d.mkdir()
    (d / "app.yaml").write_text(yaml.dump({"sqlite_path": "data/meta/from_yaml.db"}, allow_unicode=True), encoding="utf-8")
    base = load_app_yaml(d)
    merged_only_sqlite = merge_app_with_runtime(base, RuntimeSettings(sqlite_path="Z:/priority.db"))
    assert merged_only_sqlite.sqlite_path == "Z:/priority.db"
    assert merged_only_sqlite.default_word_count == base.default_word_count
