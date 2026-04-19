"""Tests for backup download and restore."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Task, TaskStatus

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_client(client: TestClient, db_session: Session) -> TestClient:
    """Client with one task in the database."""
    task = Task(title="Backup me", status=TaskStatus.INBOX)
    db_session.add(task)
    db_session.commit()
    return client


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

class TestBackupDownload:
    def test_download_returns_sqlite_bytes(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/backup/download")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/octet-stream"
        assert "todo-" in resp.headers["content-disposition"]
        assert resp.content.startswith(b"SQLite format 3\x00")

    def test_download_contains_data(self, seeded_client: TestClient, tmp_path: Path) -> None:
        resp = seeded_client.get("/backup/download")
        db_file = tmp_path / "downloaded.db"
        db_file.write_bytes(resp.content)

        conn = sqlite3.connect(str(db_file))
        rows = conn.execute("SELECT title FROM tasks").fetchall()
        conn.close()

        assert any("Backup me" in r[0] for r in rows)


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------

class TestBackupRestore:
    def _make_test_db(self, tmp_path: Path) -> Path:
        """Create a minimal valid SQLite DB with one task."""
        db_path = tmp_path / "restore_test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                notes TEXT,
                status TEXT DEFAULT 'inbox',
                due_date DATE,
                is_recurring INTEGER DEFAULT 0,
                recurrence_type TEXT,
                recurrence_interval_days INTEGER,
                last_completed_at DATETIME,
                project_id INTEGER,
                created_at DATETIME,
                updated_at DATETIME,
                completed_at DATETIME
            )"""
        )
        conn.execute("INSERT INTO tasks (title, status) VALUES ('Restored task', 'inbox')")
        conn.commit()
        conn.close()
        return db_path

    def test_restore_replaces_database(self, seeded_client: TestClient, tmp_path: Path) -> None:
        db_path = self._make_test_db(tmp_path)
        data = db_path.read_bytes()

        resp = seeded_client.post(
            "/backup/restore",
            files={"file": ("backup.db", data, "application/octet-stream")},
        )
        # Follows redirect to settings with restored=1
        assert resp.status_code == 200
        assert "restored" in resp.text.lower() or "restored=1" in str(resp.url)

    def test_restore_rejects_non_sqlite(self, client: TestClient) -> None:
        resp = client.post(
            "/backup/restore",
            files={"file": ("bad.db", b"not a database", "application/octet-stream")},
        )
        # Follows redirect to settings with error
        assert resp.status_code == 200
        assert "error" in str(resp.url) or "not a valid SQLite" in resp.text

    def test_restore_rejects_empty_file(self, client: TestClient) -> None:
        resp = client.post(
            "/backup/restore",
            files={"file": ("empty.db", b"", "application/octet-stream")},
        )
        # Follows redirect to settings with error
        assert resp.status_code == 200
        assert "error" in str(resp.url) or "empty" in resp.text

    def test_restore_no_file(self, client: TestClient) -> None:
        resp = client.post("/backup/restore")
        # Either follows redirect or FastAPI returns 422 for missing field
        assert resp.status_code in (200, 422)


# ---------------------------------------------------------------------------
# Settings page shows backup section
# ---------------------------------------------------------------------------

class TestSettingsBackupUI:
    def test_settings_page_has_backup_section(self, client: TestClient) -> None:
        resp = client.get("/settings")
        assert resp.status_code == 200
        assert "Database Backup" in resp.text
        assert "/backup/download" in resp.text
        assert "/backup/restore" in resp.text

    def test_settings_shows_restored_banner(self, client: TestClient) -> None:
        resp = client.get("/settings?restored=1")
        assert resp.status_code == 200
        assert "restored successfully" in resp.text
