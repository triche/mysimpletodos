"""CSRF protection — double-submit cookie pattern."""

from __future__ import annotations

import hmac
import logging
import secrets
from urllib.parse import parse_qs

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

from app.config import get_settings

logger = logging.getLogger("app")

CSRF_COOKIE_NAME = "csrf_token"
CSRF_FIELD_NAME = "csrf_token"

# Paths that are exempt from CSRF validation.
_EXEMPT_PREFIXES = ("/health", "/auth/", "/static/")


def _is_exempt(path: str) -> bool:
    return any(path.startswith(p) for p in _EXEMPT_PREFIXES) or path == "/auth"


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie CSRF protection.

    * On every request, ensures a ``csrf_token`` cookie is set and stores the
      value on ``request.state.csrf_token`` so templates can embed it.
    * On **POST** requests (except exempt paths and Bearer-authenticated
      requests), validates that the form field ``csrf_token`` matches the
      cookie value.
    * Skipped entirely when ``AUTH_DISABLED=true`` (dev/test).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()

        # Always populate request.state so templates can reference it.
        token = request.cookies.get(CSRF_COOKIE_NAME) or secrets.token_hex(32)
        request.state.csrf_token = token

        # When auth is disabled, skip validation (dev/test).
        if settings.auth_disabled:
            response = await call_next(request)
            self._ensure_cookie(request, response, token, settings)
            return response

        # Validate POST requests.
        if request.method == "POST" and not _is_exempt(request.url.path):
            # Bearer-token requests are not susceptible to CSRF.
            auth_header = request.headers.get("authorization", "")
            if not auth_header.lower().startswith("bearer "):
                cookie_token = request.cookies.get(CSRF_COOKIE_NAME, "")
                form_token = await self._extract_form_token(request)

                if (
                    not cookie_token
                    or not form_token
                    or not hmac.compare_digest(cookie_token, form_token)
                ):
                    logger.warning(
                        "CSRF validation failed for %s %s",
                        request.method,
                        request.url.path,
                    )
                    accept = request.headers.get("accept", "")
                    if "application/json" in accept and "text/html" not in accept:
                        return JSONResponse(
                            {"detail": "CSRF validation failed"}, status_code=403
                        )
                    return HTMLResponse("CSRF validation failed", status_code=403)

        response = await call_next(request)
        self._ensure_cookie(request, response, token, settings)
        return response

    # ------------------------------------------------------------------
    @staticmethod
    async def _extract_form_token(request: Request) -> str:
        """Read the csrf_token field from a URL-encoded or multipart form body."""
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type:
            body = await request.body()
            params = parse_qs(body.decode("utf-8", errors="replace"))
            return params.get(CSRF_FIELD_NAME, [""])[0]
        if "multipart/form-data" in content_type:
            # For multipart uploads we cannot call request.form() because
            # BaseHTTPMiddleware consumes the body stream and the downstream
            # route handler would then receive an empty upload.  Instead,
            # read the raw body (already buffered by BaseHTTPMiddleware) and
            # scan for the csrf_token field which appears before any file
            # data in the multipart stream.
            body = await request.body()
            text = body[:8192].decode("utf-8", errors="replace")
            # Look for: Content-Disposition: form-data; name="csrf_token"\r\n\r\n<value>
            marker = f'name="{CSRF_FIELD_NAME}"'
            idx = text.find(marker)
            if idx != -1:
                # Skip past the marker and the blank line separator
                rest = text[idx + len(marker):]
                # Find the double newline that separates headers from value
                sep = rest.find("\r\n\r\n")
                if sep != -1:
                    value_start = sep + 4
                    # Value ends at the next boundary (starts with \r\n--)
                    end = rest.find("\r\n--", value_start)
                    if end != -1:
                        return rest[value_start:end].strip()
            return ""
        # Fall back to a custom header (useful for fetch-based JSON posts).
        return request.headers.get("x-csrf-token", "")

    @staticmethod
    def _ensure_cookie(
        request: Request, response: Response, token: str, settings: object
    ) -> None:
        if CSRF_COOKIE_NAME not in request.cookies:
            origin = getattr(settings, "webauthn_origin", "http://localhost")
            response.set_cookie(
                CSRF_COOKIE_NAME,
                token,
                httponly=True,
                samesite="strict",
                secure=origin.startswith("https"),
            )
