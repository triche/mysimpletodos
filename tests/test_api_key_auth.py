"""Phase 2 tests — API key Bearer token authentication."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth import COOKIE_NAME, create_session_cookie
from app.config import get_settings
from app.db import get_engine, init_db
from app.main import create_app
from app.services.api_key_service import generate_key, revoke_key, verify_key


@pytest.fixture
def auth_enabled_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Set up an auth-enabled environment and return the database URL."""
    get_settings.cache_clear()
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret-key-for-api-keys")
    return db_url


@pytest.fixture
def auth_enabled_client(auth_enabled_url: str) -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def api_key_plaintext(auth_enabled_url: str) -> str:
    """Generate an API key and return the plaintext."""
    init_db(auth_enabled_url)
    engine = get_engine(auth_enabled_url)
    with Session(engine) as session:
        _, plaintext = generate_key(session, "test-key")
    return plaintext


def test_bearer_token_grants_access(
    auth_enabled_client: TestClient, api_key_plaintext: str
) -> None:
    resp = auth_enabled_client.get(
        "/inbox",
        headers={"Authorization": f"Bearer {api_key_plaintext}"},
    )
    assert resp.status_code == 200


def test_invalid_bearer_token_falls_through(auth_enabled_client: TestClient) -> None:
    resp = auth_enabled_client.get(
        "/inbox",
        headers={"Authorization": "Bearer mst_invalid_key_value"},
        follow_redirects=False,
    )
    # Falls through to cookie check, then redirects to login
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["location"]


def test_bearer_token_on_json_route(
    auth_enabled_client: TestClient, api_key_plaintext: str
) -> None:
    resp = auth_enabled_client.get(
        "/export/tasks.json",
        headers={"Authorization": f"Bearer {api_key_plaintext}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")


def test_no_auth_returns_401_for_api(auth_enabled_client: TestClient) -> None:
    resp = auth_enabled_client.get(
        "/export/tasks.json",
        follow_redirects=False,
    )
    assert resp.status_code == 401


def test_bearer_token_updates_last_used(
    auth_enabled_client: TestClient, api_key_plaintext: str, auth_enabled_url: str
) -> None:
    auth_enabled_client.get(
        "/inbox",
        headers={"Authorization": f"Bearer {api_key_plaintext}"},
    )
    engine = get_engine(auth_enabled_url)
    with Session(engine) as session:
        key = verify_key(session, api_key_plaintext)
    assert key is not None
    assert key.last_used_at is not None


def test_revoked_key_returns_401(
    auth_enabled_client: TestClient, api_key_plaintext: str, auth_enabled_url: str
) -> None:
    # Revoke the key
    engine = get_engine(auth_enabled_url)
    with Session(engine) as session:
        from app.services.api_key_service import list_keys

        keys = list_keys(session)
        revoke_key(session, keys[0].id)

    resp = auth_enabled_client.get(
        "/export/tasks.json",
        headers={"Authorization": f"Bearer {api_key_plaintext}"},
        follow_redirects=False,
    )
    assert resp.status_code == 401


def test_auth_disabled_skips_bearer_check(client: TestClient) -> None:
    """With AUTH_DISABLED=true, routes work without any token."""
    resp = client.get("/inbox")
    assert resp.status_code == 200


def test_bearer_and_cookie_both_work(auth_enabled_client: TestClient) -> None:
    """A valid session cookie still works without a Bearer header."""
    cookie = create_session_cookie()
    auth_enabled_client.cookies.set(COOKIE_NAME, cookie)
    resp = auth_enabled_client.get("/inbox")
    assert resp.status_code == 200
