from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.settings import clear_settings_cache


@pytest.fixture
def client(tmp_sqlite_url: Path) -> TestClient:
    clear_settings_cache()
    with TestClient(create_app()) as c:
        yield c


def test_health_ok(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_task_returns_task_id(client: TestClient) -> None:
    r = client.post("/tasks/", json={"author": "demo", "brief": {"topic": "x"}})
    assert r.status_code == 200
    body = r.json()
    assert "task_id" in body
    assert len(body["task_id"]) > 8


def test_get_task_not_found(client: TestClient) -> None:
    r = client.get("/tasks/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_get_task_exists(client: TestClient) -> None:
    created = client.post("/tasks/", json={"author": "a"}).json()
    tid = created["task_id"]
    r = client.get(f"/tasks/{tid}")
    assert r.status_code == 200
    data = r.json()
    assert data["task_id"] == tid
    assert data["state"] == "WAIT_OUTLINE_CONFIRM"


def test_get_latest_outline_endpoint(client: TestClient) -> None:
    created = client.post(
        "/tasks/",
        json={
            "author": "a",
            "brief": {
                "topic": "t",
                "angle": "a",
                "thesis": "th",
                "argument_framework": "af",
                "narrative_skeleton": "ns",
                "target_audience": "aud",
            },
        },
    ).json()
    tid = created["task_id"]
    r = client.get(f"/tasks/{tid}/outline/latest")
    assert r.status_code == 200
    body = r.json()
    assert body["task_id"] == tid
    assert body["outline_version"] >= 1
    assert body["outline_confirmed"] is False
    assert body["outline"]["title"]
    assert len(body["outline"]["sections"]) >= 1


def test_outline_confirm_endpoint(client: TestClient) -> None:
    created = client.post(
        "/tasks/",
        json={
            "author": "a",
            "brief": {
                "topic": "t",
                "angle": "a",
                "thesis": "th",
                "argument_framework": "af",
                "narrative_skeleton": "ns",
                "target_audience": "aud",
            },
        },
    ).json()
    tid = created["task_id"]
    ok = client.post(f"/tasks/{tid}/outline/confirm")
    assert ok.status_code == 200
    body = ok.json()
    assert body["task_id"] == tid
    after = client.get(f"/tasks/{tid}").json()
    assert after["outline_confirmed"] is True


def test_generate_endpoint_requires_outline_confirmed(client: TestClient) -> None:
    tid = client.post("/tasks/", json={"author": "a", "brief": {"topic": "x"}}).json()["task_id"]
    bad = client.post(f"/tasks/{tid}/generate")
    assert bad.status_code == 409
