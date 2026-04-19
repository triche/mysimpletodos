"""Backup and restore routes — download / upload the SQLite database."""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlmodel import Session

from app.db import get_session
from app.services.backup_service import create_backup_bytes, restore_from_bytes

logger = logging.getLogger("app")

router = APIRouter(tags=["backup"])

# Max upload size: 100 MB
_MAX_UPLOAD_BYTES = 100 * 1024 * 1024


@router.get("/backup/download")
def download_backup(session: Session = Depends(get_session)) -> Response:
    """Download a consistent snapshot of the SQLite database."""
    data = create_backup_bytes()
    filename = f"todo-{date.today().isoformat()}.db"
    logger.info("Database backup downloaded (%d bytes)", len(data))
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/backup/restore")
async def restore_backup(
    request: Request,
    file: UploadFile | None = None,
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """Restore the database from an uploaded SQLite file."""
    if file is None or file.filename == "":
        return RedirectResponse(
            "/settings?error=No+file+selected", status_code=303
        )

    data = await file.read()

    if len(data) > _MAX_UPLOAD_BYTES:
        return RedirectResponse(
            "/settings?error=File+too+large+(100+MB+max)", status_code=303
        )

    if len(data) == 0:
        return RedirectResponse(
            "/settings?error=Uploaded+file+is+empty", status_code=303
        )

    try:
        restore_from_bytes(data)
    except ValueError as e:
        logger.warning("Restore rejected: %s", e)
        return RedirectResponse(
            f"/settings?error={str(e)}", status_code=303
        )

    logger.info("Database restored from upload (%d bytes)", len(data))
    return RedirectResponse("/settings?restored=1", status_code=303)
