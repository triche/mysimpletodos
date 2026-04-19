"""Tests for backup commands."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import httpx
import respx

from mst_cli.main import cli

BASE = "http://test:8080"


def _make_sqlite_bytes(tmp_path: Path) -> bytes:
    """Create a minimal valid SQLite database and return its bytes."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    return db.read_bytes()


@respx.mock
def test_backup_download_default_filename(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    monkeypatch.chdir(tmp_path)
    db_bytes = _make_sqlite_bytes(tmp_path)
    respx.get(f"{BASE}/backup/download").mock(
        return_value=httpx.Response(200, content=db_bytes)
    )
    result = runner.invoke(cli, ["backup", "download"])
    assert result.exit_code == 0
    assert "Backup saved" in result.output
    # Should have created a file in cwd
    files = list(tmp_path.glob("todo-*.db"))
    assert len(files) == 1
    assert files[0].read_bytes().startswith(b"SQLite format 3")


@respx.mock
def test_backup_download_custom_output(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    db_bytes = _make_sqlite_bytes(tmp_path)
    respx.get(f"{BASE}/backup/download").mock(
        return_value=httpx.Response(200, content=db_bytes)
    )
    out = tmp_path / "custom.db"
    result = runner.invoke(cli, ["backup", "download", "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()


@respx.mock
def test_backup_restore_with_confirmation(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    db_file = tmp_path / "backup.db"
    db_file.write_bytes(_make_sqlite_bytes(tmp_path))
    respx.post(f"{BASE}/backup/restore").mock(
        return_value=httpx.Response(303, headers={"location": "/settings?restored=1"})
    )
    result = runner.invoke(cli, ["backup", "restore", str(db_file)], input="y\n")
    assert result.exit_code == 0
    assert "restored" in result.output


@respx.mock
def test_backup_restore_skip_confirm(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    db_file = tmp_path / "backup.db"
    db_file.write_bytes(_make_sqlite_bytes(tmp_path))
    respx.post(f"{BASE}/backup/restore").mock(
        return_value=httpx.Response(303, headers={"location": "/settings?restored=1"})
    )
    result = runner.invoke(cli, ["backup", "restore", "--yes", str(db_file)])
    assert result.exit_code == 0
    assert "restored" in result.output


def test_backup_restore_rejects_non_sqlite(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    bad_file = tmp_path / "bad.db"
    bad_file.write_text("not a database")
    result = runner.invoke(cli, ["backup", "restore", "--yes", str(bad_file)])
    assert result.exit_code != 0
    assert "valid SQLite" in result.output


def test_backup_restore_aborted(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    db_file = tmp_path / "backup.db"
    db_file.write_bytes(_make_sqlite_bytes(tmp_path))
    result = runner.invoke(cli, ["backup", "restore", str(db_file)], input="n\n")
    assert result.exit_code != 0  # Aborted
