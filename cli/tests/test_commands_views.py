"""Tests for view commands (today, inbox)."""

from __future__ import annotations

from datetime import date, timedelta

import httpx
import respx

from mst_cli.main import cli

BASE = "http://test:8080"

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()

TASKS = [
    {
        "id": 1, "title": "Overdue task", "status": "next_action",
        "due_date": YESTERDAY, "project_id": None, "is_recurring": False,
    },
    {
        "id": 2, "title": "Due today task", "status": "next_action",
        "due_date": TODAY, "project_id": None, "is_recurring": False,
    },
    {
        "id": 3, "title": "Future task", "status": "next_action",
        "due_date": TOMORROW, "project_id": None, "is_recurring": False,
    },
    {
        "id": 4, "title": "Done task", "status": "done",
        "due_date": TODAY, "project_id": None, "is_recurring": False,
    },
    {
        "id": 5, "title": "No due date", "status": "inbox",
        "due_date": None, "project_id": None, "is_recurring": False,
    },
]


@respx.mock
def test_today_shows_overdue_and_due_today(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.get(f"{BASE}/export/tasks.json").mock(return_value=httpx.Response(200, json=TASKS))
    result = runner.invoke(cli, ["today"])
    assert result.exit_code == 0
    assert "Overdue" in result.output
    assert "Due Today" in result.output
    assert "Overdue task" in result.output
    assert "Due today task" in result.output


@respx.mock
def test_today_excludes_done_tasks(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.get(f"{BASE}/export/tasks.json").mock(return_value=httpx.Response(200, json=TASKS))
    result = runner.invoke(cli, ["today"])
    assert "Done task" not in result.output


@respx.mock
def test_today_excludes_no_due_date(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.get(f"{BASE}/export/tasks.json").mock(return_value=httpx.Response(200, json=TASKS))
    result = runner.invoke(cli, ["today"])
    assert "No due date" not in result.output


@respx.mock
def test_today_shows_count_summary(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.get(f"{BASE}/export/tasks.json").mock(return_value=httpx.Response(200, json=TASKS))
    result = runner.invoke(cli, ["today"])
    assert "1 overdue" in result.output
    assert "1 due today" in result.output


@respx.mock
def test_inbox_shows_inbox_tasks(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    inbox_tasks = [{
        "id": 5, "title": "No due date", "status": "inbox",
        "due_date": None, "project_id": None, "is_recurring": False,
    }]
    respx.get(f"{BASE}/export/tasks.json", params={"status": "inbox"}).mock(
        return_value=httpx.Response(200, json=inbox_tasks)
    )
    result = runner.invoke(cli, ["inbox"])
    assert result.exit_code == 0
    assert "No due date" in result.output


@respx.mock
def test_inbox_shows_count(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    respx.get(f"{BASE}/export/tasks.json", params={"status": "inbox"}).mock(
        return_value=httpx.Response(200, json=[{
            "id": 1, "title": "T", "status": "inbox",
            "due_date": None, "project_id": None, "is_recurring": False,
        }])
    )
    result = runner.invoke(cli, ["inbox"])
    assert "1 task(s) in inbox" in result.output
