from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.settings import (
    AppYamlConfig,
    ModelYamlConfig,
    RuntimeSettings,
    clear_settings_cache,
    get_app_config,
    get_models_config,
    load_app_yaml,
    load_models_yaml,
    merge_app_with_runtime,
)


def test_load_models_yaml_success(tmp_path: Path) -> None:
    d = tmp_path / "config"
    d.mkdir()
    (d / "models.yaml").write_text(
        yaml.dump(
            {
                "outline_model": "a",
                "draft_model": "b",
                "polish_model": "c",
                "judge_model": "d",
                "embedding_model": "e",
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    cfg = load_models_yaml(d)
    assert cfg.outline_model == "a"


def test_load_models_yaml_missing_field_raises(tmp_path: Path) -> None:
    d = tmp_path / "config"
    d.mkdir()
    (d / "models.yaml").write_text(
        yaml.dump({"outline_model": "only"}, allow_unicode=True),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_models_yaml(d)


def test_env_override_tasks_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    d = tmp_path / "config"
    d.mkdir()
    (d / "app.yaml").write_text(
        yaml.dump({"sqlite_path": "data/meta/app.db", "tasks_data_dir": "data/tasks"}, allow_unicode=True),
        encoding="utf-8",
    )
    app = load_app_yaml(d)
    merged = merge_app_with_runtime(app, RuntimeSettings(tasks_data_dir="Z:/tasks_root"))
    assert merged.tasks_data_dir == "Z:/tasks_root"


def test_env_override_sqlite_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    d = tmp_path / "config"
    d.mkdir()
    (d / "app.yaml").write_text(
        yaml.dump({"sqlite_path": "data/meta/app.db"}, allow_unicode=True),
        encoding="utf-8",
    )
    app = load_app_yaml(d)
    merged = merge_app_with_runtime(app, RuntimeSettings(sqlite_path="Z:/override.db"))
    assert merged.sqlite_path == "Z:/override.db"


def test_get_app_config_reads_repo_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = Path(__file__).resolve().parent.parent.parent
    monkeypatch.setenv("WRITING_PIPELINE_ROOT", str(repo))
    clear_settings_cache()
    cfg = get_app_config()
    assert cfg.default_word_count == 5000
    assert "meta" in cfg.sqlite_path


def test_get_models_config_reads_repo_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = Path(__file__).resolve().parent.parent.parent
    monkeypatch.setenv("WRITING_PIPELINE_ROOT", str(repo))
    clear_settings_cache()
    m = get_models_config()
    assert m.outline_model
