"""Tests for task commands."""

from __future__ import annotations

import httpx
import respx

from mst_cli.main import cli

SAMPLE_TASKS = [
    {
        "id": 1, "title": "Buy milk", "status": "inbox",
        "due_date": None, "project_id": None, "is_recurring": False, "notes": None,
    },
    {
        "id": 2, "title": "Write report", "status": "next_action",
        "due_date": "2026-03-30", "project_id": 1, "is_recurring": False,
        "notes": "Important",
    },
    {
        "id": 3, "title": "Call dentist", "status": "waiting_for",
        "due_date": None, "project_id": None, "is_recurring": True, "notes": None,
    },
]

BASE = "http://test:8080"


@respx.mock
def test_tasks_list_renders_table(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.get(f"{BASE}/export/tasks.json").mock(return_value=httpx.Response(200, json=SAMPLE_TASKS))
    result = runner.invoke(cli, ["tasks"])
    assert result.exit_code == 0
    assert "Buy milk" in result.output
    assert "Write report" in result.output
    assert "3 task(s)" in result.output


@respx.mock
def test_tasks_filter_by_status(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    route = respx.get(f"{BASE}/export/tasks.json", params={"status": "inbox"}).mock(
        return_value=httpx.Response(200, json=[SAMPLE_TASKS[0]])
    )
    result = runner.invoke(cli, ["tasks", "--status", "inbox"])
    assert result.exit_code == 0
    assert route.called
    assert "1 task(s)" in result.output


@respx.mock
def test_tasks_search_filters_client_side(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.get(f"{BASE}/export/tasks.json").mock(return_value=httpx.Response(200, json=SAMPLE_TASKS))
    result = runner.invoke(cli, ["tasks", "--search", "milk"])
    assert result.exit_code == 0
    assert "Buy milk" in result.output
    assert "1 task(s)" in result.output


@respx.mock
def test_tasks_plain_output(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.get(f"{BASE}/export/tasks.json").mock(return_value=httpx.Response(200, json=SAMPLE_TASKS))
    result = runner.invoke(cli, ["--plain", "tasks"])
    assert result.exit_code == 0
    assert "\t" in result.output
    assert "Buy milk" in result.output


@respx.mock
def test_add_task(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    route = respx.post(f"{BASE}/tasks").mock(
        return_value=httpx.Response(303, headers={"location": "/inbox"})
    )
    result = runner.invoke(cli, ["add", "Test task"])
    assert result.exit_code == 0
    assert '✓ Task created: "Test task"' in result.output
    assert route.called


@respx.mock
def test_add_task_with_project(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    route = respx.post(f"{BASE}/tasks").mock(
        return_value=httpx.Response(303, headers={"location": "/inbox"})
    )
    result = runner.invoke(cli, ["add", "Task", "--project", "1"])
    assert result.exit_code == 0
    req = route.calls[0].request
    assert b"project_id=1" in req.content


@respx.mock
def test_complete_task(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.post(f"{BASE}/tasks/1/complete").mock(
        return_value=httpx.Response(303, headers={"location": "/inbox"})
    )
    result = runner.invoke(cli, ["complete", "1"])
    assert result.exit_code == 0
    assert "✓ Task 1 completed" in result.output


@respx.mock
def test_reopen_task(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.post(f"{BASE}/tasks/1/reopen").mock(
        return_value=httpx.Response(303, headers={"location": "/inbox"})
    )
    result = runner.invoke(cli, ["reopen", "1"])
    assert result.exit_code == 0
    assert "✓ Task 1 reopened" in result.output


@respx.mock
def test_edit_task_status_uses_quick_update(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    route = respx.post(f"{BASE}/tasks/1/quick-update").mock(
        return_value=httpx.Response(303, headers={"location": "/tasks"})
    )
    result = runner.invoke(cli, ["edit", "1", "--status", "next_action"])
    assert result.exit_code == 0
    assert route.called
    req = route.calls[0].request
    assert b"field=status" in req.content


@respx.mock
def test_edit_task_title_uses_full_update(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    route = respx.post(f"{BASE}/tasks/1/update").mock(
        return_value=httpx.Response(303, headers={"location": "/tasks"})
    )
    result = runner.invoke(cli, ["edit", "1", "--title", "New title"])
    assert result.exit_code == 0
    assert route.called


@respx.mock
def test_edit_task_due_date(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    route = respx.post(f"{BASE}/tasks/1/quick-update").mock(
        return_value=httpx.Response(303, headers={"location": "/tasks"})
    )
    result = runner.invoke(cli, ["edit", "1", "--due", "2026-04-01"])
    assert result.exit_code == 0
    assert route.called
    req = route.calls[0].request
    assert b"due_date=2026-04-01" in req.content


@respx.mock
def test_edit_task_clear_due_date(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    route = respx.post(f"{BASE}/tasks/1/quick-update").mock(
        return_value=httpx.Response(303, headers={"location": "/tasks"})
    )
    result = runner.invoke(cli, ["edit", "1", "--due", ""])
    assert result.exit_code == 0
    assert route.called


@respx.mock
def test_complete_nonexistent_shows_error(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.post(f"{BASE}/tasks/999/complete").mock(
        return_value=httpx.Response(404, text="Not found")
    )
    result = runner.invoke(cli, ["complete", "999"])
    assert result.exit_code != 0
