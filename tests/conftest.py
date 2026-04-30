from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _default_writing_pipeline_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """保证默认从仓库读取 config/，避免导入阶段路径漂移。"""
    monkeypatch.setenv("WRITING_PIPELINE_ROOT", str(_REPO_ROOT))


@pytest.fixture
def tmp_sqlite_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "test.sqlite"
    monkeypatch.setenv("WRITING_SQLITE_PATH", str(db))
    from app.settings import clear_settings_cache

    clear_settings_cache()
    return db
