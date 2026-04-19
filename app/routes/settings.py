"""Settings page routes — API key management."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from itsdangerous import BadSignature, SignatureExpired
from sqlmodel import Session

from app.auth import create_signer
from app.config import get_settings
from app.db import get_session
from app.routes import templates
from app.routes.helpers import base_context
from app.services.api_key_service import generate_key, list_keys, revoke_key

router = APIRouter(tags=["settings"])


@router.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request, session: Session = Depends(get_session)
) -> HTMLResponse:
    keys = list_keys(session)

    # Read flash cookie for newly created key (avoids exposing key in URL).
    new_key = None
    flash_cookie = request.cookies.get("_flash_key")
    if flash_cookie:
        try:
            signer = create_signer()
            new_key = signer.unsign(flash_cookie, max_age=60).decode()
        except (BadSignature, SignatureExpired):
            pass

    ctx = base_context(session)
    ctx.update({
        "api_keys": keys,
        "new_key": new_key,
        "error": request.query_params.get("error"),
        "restored": request.query_params.get("restored"),
        "auth_disabled": get_settings().auth_disabled,
    })
    resp = templates.TemplateResponse(request, "settings.html", ctx)
    if flash_cookie:
        resp.delete_cookie("_flash_key")
    return resp


@router.post("/settings/api-keys")
def create_api_key(
    request: Request, name: str = Form(""), session: Session = Depends(get_session)
) -> RedirectResponse:
    try:
        _, plaintext = generate_key(session, name)
    except ValueError as e:
        return RedirectResponse(
            f"/settings?error={str(e)}", status_code=303
        )
    settings = get_settings()
    signer = create_signer()
    resp = RedirectResponse("/settings", status_code=303)
    resp.set_cookie(
        "_flash_key",
        signer.sign(plaintext).decode(),
        max_age=60,
        httponly=True,
        samesite="strict",
        secure=settings.webauthn_origin.startswith("https"),
    )
    return resp


@router.post("/settings/api-keys/{key_id}/revoke")
def revoke_api_key(
    key_id: int, session: Session = Depends(get_session)
) -> RedirectResponse:
    if not revoke_key(session, key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    return RedirectResponse("/settings", status_code=303)
