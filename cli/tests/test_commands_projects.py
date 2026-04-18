"""Tests for project commands."""

from __future__ import annotations

import httpx
import respx

from mst_cli.main import cli

BASE = "http://test:8080"

PROJECTS = [
    {
        "id": 1, "name": "Project A", "description": "Desc A",
        "notes": "Some notes", "due_date": "2026-04-15",
        "completed_at": None, "archived_at": None,
    },
    {
        "id": 2, "name": "Project B", "description": None,
        "notes": None, "due_date": None,
        "completed_at": None, "archived_at": None,
    },
]

TASKS = [
    {
        "id": 1, "title": "Task 1", "status": "inbox",
        "due_date": None, "project_id": 1, "is_recurring": False,
    },
    {
        "id": 2, "title": "Task 2", "status": "next_action",
        "due_date": "2026-04-01", "project_id": 1, "is_recurring": False,
    },
    {
        "id": 3, "title": "Task 3", "status": "done",
        "due_date": None, "project_id": 1, "is_recurring": False,
    },
    {
        "id": 4, "title": "Task 4", "status": "inbox",
        "due_date": None, "project_id": 2, "is_recurring": False,
    },
]


@respx.mock
def test_projects_list_with_counts(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.get(f"{BASE}/export/projects.json").mock(return_value=httpx.Response(200, json=PROJECTS))
    respx.get(f"{BASE}/export/tasks.json").mock(return_value=httpx.Response(200, json=TASKS))
    result = runner.invoke(cli, ["projects"])
    assert result.exit_code == 0
    assert "Project A" in result.output
    assert "Project B" in result.output
    assert "2 project(s)" in result.output


@respx.mock
def test_project_detail_shows_metadata(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.get(f"{BASE}/export/projects.json").mock(return_value=httpx.Response(200, json=PROJECTS))
    respx.get(f"{BASE}/export/tasks.json").mock(return_value=httpx.Response(200, json=TASKS))
    result = runner.invoke(cli, ["project", "1"])
    assert result.exit_code == 0
    assert "Project A" in result.output
    assert "Desc A" in result.output
    assert "Some notes" in result.output
    assert "2026-04-15" in result.output


@respx.mock
def test_project_detail_groups_tasks(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.get(f"{BASE}/export/projects.json").mock(return_value=httpx.Response(200, json=PROJECTS))
    respx.get(f"{BASE}/export/tasks.json").mock(return_value=httpx.Response(200, json=TASKS))
    result = runner.invoke(cli, ["project", "1"])
    assert "Inbox" in result.output
    assert "Next Action" in result.output
    assert "Done" in result.output


@respx.mock
def test_project_not_found_shows_error(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.get(f"{BASE}/export/projects.json").mock(return_value=httpx.Response(200, json=PROJECTS))
    result = runner.invoke(cli, ["project", "999"])
    assert result.exit_code != 0
