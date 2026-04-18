"""Authentication middleware and session helpers."""

from __future__ import annotations

import json
import logging

from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from sqlmodel import Session as DBSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse, Response

from app.config import get_settings
from app.db import get_engine

logger = logging.getLogger("app")

COOKIE_NAME = "mst_session"

# Paths that never require authentication.
_EXEMPT_PREFIXES = ("/health", "/auth/", "/static/")


def _is_exempt(path: str) -> bool:
    return any(path.startswith(p) for p in _EXEMPT_PREFIXES) or path == "/auth"


def create_signer() -> TimestampSigner:
    settings = get_settings()
    return TimestampSigner(settings.auth_secret_key)


def create_session_cookie() -> str:
    signer = create_signer()
    payload = json.dumps({"authenticated": True})
    return signer.sign(payload).decode("utf-8")


def verify_session_cookie(cookie_value: str) -> bool:
    settings = get_settings()
    signer = create_signer()
    try:
        signer.unsign(cookie_value, max_age=settings.auth_session_max_age)
        return True
    except (BadSignature, SignatureExpired):
        return False


def _wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "application/json" in accept and "text/html" not in accept


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()

        if settings.auth_disabled:
            return await call_next(request)

        path = request.url.path
        if _is_exempt(path):
            return await call_next(request)

        # Check Authorization header for Bearer token
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]  # strip "Bearer "
            if token.startswith("mst_"):
                from app.services.api_key_service import verify_key

                engine = get_engine()
                with DBSession(engine) as db_session:
                    api_key = verify_key(db_session, token)
                if api_key is not None:
                    return await call_next(request)

        # Check session cookie
        cookie = request.cookies.get(COOKIE_NAME)
        if cookie and verify_session_cookie(cookie):
            return await call_next(request)

        # Not authenticated — check if we need to redirect to setup or login
        if _wants_json(request) or path.startswith("/export/"):
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)

        return RedirectResponse("/auth/login", status_code=302)
