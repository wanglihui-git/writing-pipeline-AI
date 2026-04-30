from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.settings import clear_settings_cache


@pytest.fixture
def client(tmp_sqlite_url: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("WRITING_TASKS_DATA_DIR", str(tmp_path / "phase5artifacts"))
    clear_settings_cache()
    with TestClient(create_app()) as c:
        yield c
