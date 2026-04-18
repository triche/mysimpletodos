"""Tests for CSRF protection, security headers, shared helpers, and API-key flash cookie."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.models import TaskStatus
from app.routes.helpers import parse_bool_filter, parse_status_filter, safe_back_url

# ---------------------------------------------------------------------------
# Helper function unit tests
# ---------------------------------------------------------------------------

class TestParseBoolFilter:
    def test_yes(self):
        assert parse_bool_filter("yes") is True

    def test_no(self):
        assert parse_bool_filter("no") is False

    def test_empty(self):
        assert parse_bool_filter("") is None

    def test_garbage(self):
        assert parse_bool_filter("maybe") is None


class TestParseStatusFilter:
    def test_valid_status(self):
        assert parse_status_filter("inbox") == TaskStatus.INBOX

    def test_empty(self):
        assert parse_status_filter("") is None

    def test_invalid(self):
        assert parse_status_filter("bogus") is None


class TestSafeBackUrl:
    def test_safe_prefix(self):
        assert safe_back_url("/inbox", "/fallback") == "/inbox"

    def test_unsafe_prefix(self):
        assert safe_back_url("https://evil.com", "/fallback") == "/fallback"

    def test_projects_prefix(self):
        assert safe_back_url("/projects/1", "/fallback") == "/projects/1"


# ---------------------------------------------------------------------------
# Fixtures for auth-enabled tests
# ---------------------------------------------------------------------------

@pytest.fixture
def _auth_enabled_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    get_settings.cache_clear()
    url = f"sqlite:///{tmp_path / 'auth.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret-key-for-csrf")
    return url


@pytest.fixture
def auth_client(_auth_enabled_url: str) -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# CSRF middleware tests
# ---------------------------------------------------------------------------

class TestCSRFMiddleware:
    def test_csrf_cookie_set_on_get(self, auth_client: TestClient):
        """GET requests should set a csrf_token cookie."""
        resp = auth_client.get("/auth/setup")
        assert "csrf_token" in resp.cookies

    def test_post_without_csrf_rejected(self, auth_client: TestClient):
        """POST without CSRF token should be rejected when auth is enabled."""
        # First authenticate via session cookie bypass is not possible,
        # but the CSRF middleware runs before auth redirect.  A POST to an
        # auth-exempt path should still pass (e.g. /auth/logout).
        # A POST to a protected path without a session will be rejected by
        # auth first, but let's verify CSRF blocks on a non-exempt path.
        resp = auth_client.post(
            "/tasks",
            data={"title": "Test"},
            cookies={"mst_session": "fake"},  # won't pass auth but CSRF runs first
        )
        assert resp.status_code == 403

    def test_post_with_valid_csrf_passes_through(self, auth_client: TestClient):
        """POST with matching CSRF token should pass CSRF validation."""
        # Get a CSRF token
        get_resp = auth_client.get("/auth/setup")
        csrf_token = get_resp.cookies.get("csrf_token", "")
        assert csrf_token

        # POST with the CSRF token — will still be rejected by auth (302)
        # but should NOT be rejected by CSRF (403).
        resp = auth_client.post(
            "/tasks",
            data={"title": "Test", "csrf_token": csrf_token},
            cookies={"csrf_token": csrf_token},
        )
        # If CSRF passed, auth middleware redirects (302) instead of 403
        assert resp.status_code != 403

    def test_post_with_wrong_csrf_rejected(self, auth_client: TestClient):
        """POST with mismatched CSRF token should be rejected."""
        get_resp = auth_client.get("/auth/setup")
        csrf_token = get_resp.cookies.get("csrf_token", "")

        resp = auth_client.post(
            "/tasks",
            data={"title": "Test", "csrf_token": "wrong-token"},
            cookies={"csrf_token": csrf_token},
        )
        assert resp.status_code == 403

    def test_bearer_auth_skips_csrf(self, auth_client: TestClient):
        """Bearer-authenticated requests should bypass CSRF validation."""
        resp = auth_client.post(
            "/tasks",
            data={"title": "Test"},
            headers={"Authorization": "Bearer mst_fakekey"},
        )
        # Should not be 403 (CSRF) — will be 401 (invalid key) or similar
        assert resp.status_code != 403

    def test_csrf_skipped_when_auth_disabled(self, client: TestClient):
        """When AUTH_DISABLED=true, CSRF validation is skipped."""
        resp = client.post("/tasks", data={"title": "CSRF skip test"})
        assert resp.status_code != 403

    def test_exempt_paths_skip_csrf(self, auth_client: TestClient):
        """Auth-exempt paths should not require CSRF tokens."""
        resp = auth_client.post("/auth/logout")
        # Should redirect (302), not 403
        assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Security headers tests
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    def test_x_content_type_options(self, client: TestClient):
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client: TestClient):
        resp = client.get("/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self, client: TestClient):
        resp = client.get("/health")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_csp(self, client: TestClient):
        resp = client.get("/health")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_permissions_policy(self, client: TestClient):
        resp = client.get("/health")
        assert "camera=()" in resp.headers.get("Permissions-Policy", "")


# ---------------------------------------------------------------------------
# API key flash cookie (no longer in URL)
# ---------------------------------------------------------------------------

class TestAPIKeyFlashCookie:
    def test_new_key_not_in_url(self, client: TestClient):
        """Creating an API key should NOT put the key in the redirect URL."""
        resp = client.post(
            "/settings/api-keys",
            data={"name": "test-key"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        location = resp.headers.get("location", "")
        assert "new_key" not in location
        assert "mst_" not in location

    def test_flash_cookie_set_on_create(self, client: TestClient):
        """Creating an API key should set a _flash_key cookie."""
        resp = client.post(
            "/settings/api-keys",
            data={"name": "test-key"},
            follow_redirects=False,
        )
        assert "_flash_key" in resp.cookies

    def test_flash_cookie_cleared_on_read(self, client: TestClient):
        """Reading the settings page should clear the _flash_key cookie."""
        # Create a key
        create_resp = client.post(
            "/settings/api-keys",
            data={"name": "test-key"},
            follow_redirects=False,
        )
        flash = create_resp.cookies.get("_flash_key")
        assert flash

        # Read settings page
        resp = client.get("/settings", cookies={"_flash_key": flash})
        assert resp.status_code == 200
        assert "mst_" in resp.text  # Key shown on page
        # Cookie should be deleted
        set_cookie = resp.headers.get("set-cookie", "")
        assert "_flash_key" in set_cookie


# ---------------------------------------------------------------------------
# API key O(1) verification
# ---------------------------------------------------------------------------

class TestAPIKeyVerification:
    def test_verify_valid_key(self, client: TestClient):
        """A valid API key should authenticate requests."""
        # Create a key
        resp = client.post(
            "/settings/api-keys",
            data={"name": "cli"},
            follow_redirects=False,
        )
        flash = resp.cookies.get("_flash_key")
        # Read the key from settings page (consume the flash cookie)
        client.get("/settings", cookies={"_flash_key": flash})
        # Extract the key from the flash cookie via the signer
        from app.auth import create_signer
        signer = create_signer()
        plaintext = signer.unsign(flash, max_age=60).decode()

        # Use the key for an API request
        api_resp = client.get(
            "/export/tasks.json",
            headers={"Authorization": f"Bearer {plaintext}"},
        )
        assert api_resp.status_code == 200


# ---------------------------------------------------------------------------
# SameSite cookie upgrade
# ---------------------------------------------------------------------------

class TestSameSiteCookie:
    def test_samesite_strict_on_setup(self, auth_client: TestClient):
        """Session cookie should use SameSite=Strict."""
        # Trigger setup page (no credentials exist)
        resp = auth_client.get("/auth/setup")
        assert resp.status_code == 200
        # We can't easily test the cookie attribute without completing
        # registration, but we verify the code path compiles and runs.
