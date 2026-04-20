"""Backup service — download and restore the SQLite database."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from app.config import get_settings


def get_db_path() -> Path:
    """Return the resolved SQLite file path, or raise if not SQLite."""
    settings = get_settings()
    path = settings.sqlite_path
    if path is None:
        raise RuntimeError("Backup is only supported for SQLite databases")
    return path


def create_backup_bytes() -> bytes:
    """Return a consistent snapshot of the database as bytes.

    Uses SQLite's online backup API via a temporary file so the copy is
    safe even while the application is serving requests.
    """
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")
    return _backup_via_tempfile(db_path)


def _backup_via_tempfile(db_path: Path) -> bytes:
    """Use sqlite3.backup() to produce a safe copy, return its bytes."""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(tmp_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


def restore_from_bytes(data: bytes) -> None:
    """Replace the current database with the uploaded snapshot.

    Validates that the upload is a real SQLite file before overwriting.
    """
    if not data.startswith(b"SQLite format 3\x00"):
        raise ValueError("Uploaded file is not a valid SQLite database")

    db_path = get_db_path()

    import tempfile

    # Write to a temp file first, then atomically move into place.
    tmp_fd = tempfile.NamedTemporaryFile(
        dir=db_path.parent, suffix=".db.tmp", delete=False
    )
    tmp_path = Path(tmp_fd.name)
    try:
        tmp_path.write_bytes(data)

        # Quick integrity check
        conn = sqlite3.connect(str(tmp_path))
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result is None or result[0] != "ok":
                raise ValueError(
                    f"Uploaded database failed integrity check: {result}"
                )
        finally:
            conn.close()

        # Atomic-ish replace
        shutil.move(str(tmp_path), str(db_path))
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    # Force the running app to reconnect to the new database file
    # and re-apply schema migrations in case the backup is from an
    # older version.
    from app.db import get_engine, init_db

    engine = get_engine()
    engine.dispose()
    init_db()
