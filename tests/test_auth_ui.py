"""Phase 5 tests — UI polish and logout button."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import COOKIE_NAME, create_session_cookie
from app.config import get_settings
from app.main import create_app


@pytest.fixture
def auth_enabled_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-ui-secret")
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_nav_shows_logout_when_authenticated(auth_enabled_client: TestClient) -> None:
    cookie = create_session_cookie()
    auth_enabled_client.cookies.set(COOKIE_NAME, cookie)
    resp = auth_enabled_client.get("/inbox")
    assert resp.status_code == 200
    assert "/auth/logout" in resp.text


def test_nav_hides_logout_when_auth_disabled(client) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/inbox")
    assert resp.status_code == 200
    assert "/auth/logout" not in resp.text


def test_nav_icons_inside_single_container(auth_enabled_client: TestClient) -> None:
    """Settings, theme toggle, and logout icons must all live inside one nav-actions div."""
    cookie = create_session_cookie()
    auth_enabled_client.cookies.set(COOKIE_NAME, cookie)
    resp = auth_enabled_client.get("/inbox")
    assert resp.status_code == 200
    # Extract the nav-actions block (greedy within the nav)
    match = re.search(
        r'<div\s+class="[^"]*\bnav-actions\b[^"]*">(.*?)</div>',
        resp.text,
        re.DOTALL,
    )
    assert match, "nav-actions container not found"
    block = match.group(1)
    assert '/settings' in block, "settings link not inside nav-actions"
    assert 'id="theme-toggle"' in block, "theme toggle not inside nav-actions"
    assert '/auth/logout' in block, "logout form not inside nav-actions"


def test_login_page_is_styled(auth_enabled_client: TestClient) -> None:
    resp = auth_enabled_client.get("/auth/login", follow_redirects=False)
    # If no credentials, it redirects to setup — that's fine too
    if resp.status_code == 302:
        resp = auth_enabled_client.get("/auth/setup")
    assert "app.css" in resp.text
    assert "auth-card" in resp.text or "auth-container" in resp.text


def test_setup_page_is_styled(auth_enabled_client: TestClient) -> None:
    resp = auth_enabled_client.get("/auth/setup")
    assert resp.status_code == 200
    assert "app.css" in resp.text
    assert "auth-card" in resp.text
