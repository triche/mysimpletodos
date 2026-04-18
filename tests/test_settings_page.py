"""Phase 3 tests — Settings page and API key management UI."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import get_settings
from app.main import create_app
from app.services.api_key_service import generate_key

# --- Fixtures (AUTH_DISABLED=true, default from conftest) ---


def test_settings_page_loads(client: TestClient) -> None:
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert "Settings" in resp.text


def test_settings_page_shows_api_keys_section(client: TestClient) -> None:
    resp = client.get("/settings")
    assert "API Keys" in resp.text


def test_generate_key_shows_plaintext_once(client: TestClient) -> None:
    resp = client.post(
        "/settings/api-keys",
        data={"name": "test key"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "mst_" in resp.text
    assert "will not be shown again" in resp.text


def test_generated_key_appears_in_list(client: TestClient, db_session: Session) -> None:
    # Generate via service so we can check the list
    api_key, _ = generate_key(db_session, "my-cli")
    resp = client.get("/settings")
    assert "my-cli" in resp.text
    assert api_key.key_suffix in resp.text


def test_revoke_key_removes_from_list(client: TestClient, db_session: Session) -> None:
    api_key, _ = generate_key(db_session, "to-revoke")
    resp = client.post(
        f"/settings/api-keys/{api_key.id}/revoke",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "to-revoke" not in resp.text


def test_generate_key_empty_name_shows_error(client: TestClient) -> None:
    resp = client.post(
        "/settings/api-keys",
        data={"name": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "must not be empty" in resp.text


def test_generate_key_at_limit_shows_error(client: TestClient, db_session: Session) -> None:
    for i in range(10):
        generate_key(db_session, f"key-{i}")
    resp = client.post(
        "/settings/api-keys",
        data={"name": "one-more"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Maximum" in resp.text


def test_gear_icon_in_nav(client: TestClient) -> None:
    resp = client.get("/inbox")
    assert resp.status_code == 200
    assert "/settings" in resp.text
    assert "nav-icon-btn" in resp.text


# --- Test that settings requires auth when enabled ---


@pytest.fixture
def auth_enabled_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret-for-settings")
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_settings_requires_auth(auth_enabled_client: TestClient) -> None:
    resp = auth_enabled_client.get("/settings", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["location"]
