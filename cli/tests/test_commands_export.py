"""Tests for export commands."""

from __future__ import annotations

import httpx
import respx

from mst_cli.main import cli

BASE = "http://test:8080"


@respx.mock
def test_export_tasks_json_stdout(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    data = [{"id": 1, "title": "Test"}]
    respx.get(f"{BASE}/export/tasks.json").mock(
        return_value=httpx.Response(200, json=data)
    )
    result = runner.invoke(cli, ["export", "tasks"])
    assert result.exit_code == 0
    assert '"title"' in result.output


@respx.mock
def test_export_tasks_csv_stdout(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    csv_data = "id,title\n1,Test\n"
    respx.get(f"{BASE}/export/tasks.csv").mock(
        return_value=httpx.Response(200, text=csv_data)
    )
    result = runner.invoke(cli, ["export", "tasks", "--format", "csv"])
    assert result.exit_code == 0
    assert "id,title" in result.output


@respx.mock
def test_export_tasks_with_status_filter(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    route = respx.get(f"{BASE}/export/tasks.json", params={"status": "inbox"}).mock(
        return_value=httpx.Response(200, json=[])
    )
    result = runner.invoke(cli, ["export", "tasks", "--status", "inbox"])
    assert result.exit_code == 0
    assert route.called


@respx.mock
def test_export_tasks_to_file(runner, monkeypatch, tmp_path):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    data = [{"id": 1, "title": "Test"}]
    respx.get(f"{BASE}/export/tasks.json").mock(
        return_value=httpx.Response(200, json=data)
    )
    out = tmp_path / "tasks.json"
    result = runner.invoke(cli, ["export", "tasks", "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    assert "Test" in out.read_text()


@respx.mock
def test_export_projects_json(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    data = [{"id": 1, "name": "Proj"}]
    respx.get(f"{BASE}/export/projects.json").mock(
        return_value=httpx.Response(200, json=data)
    )
    result = runner.invoke(cli, ["export", "projects"])
    assert result.exit_code == 0
    assert '"name"' in result.output
