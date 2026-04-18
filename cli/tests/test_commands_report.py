"""Tests for the report command."""

from __future__ import annotations

from datetime import date, timedelta

import httpx
import respx

from mst_cli.main import cli

BASE = "http://test:8080"

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TWO_DAYS_AGO = TODAY - timedelta(days=2)

TWO_DAYS_AGO_TS = TWO_DAYS_AGO.isoformat() + "T09:00:00"
TODAY_TS = TODAY.isoformat() + "T09:00:00"
YESTERDAY_TS = YESTERDAY.isoformat() + "T17:00:00"
IN_TWO_DAYS = (TODAY + timedelta(days=2)).isoformat()

PROJECTS = [
    {"id": 1, "name": "Work Project"},
    {"id": 2, "name": "Personal"},
]

TASKS = [
    # Hard landscape — due today
    {
        "id": 1, "title": "Team standup", "status": "next_action",
        "due_date": TODAY.isoformat(), "project_id": 1,
        "is_recurring": False, "created_at": TWO_DAYS_AGO_TS,
        "completed_at": None, "last_completed_at": None,
    },
    # Overdue
    {
        "id": 2, "title": "Overdue report", "status": "next_action",
        "due_date": YESTERDAY.isoformat(), "project_id": 1,
        "is_recurring": False, "created_at": TWO_DAYS_AGO_TS,
        "completed_at": None, "last_completed_at": None,
    },
    # Next action, due in 2 days (urgent)
    {
        "id": 3, "title": "Urgent next", "status": "next_action",
        "due_date": IN_TWO_DAYS, "project_id": None,
        "is_recurring": False, "created_at": TWO_DAYS_AGO_TS,
        "completed_at": None, "last_completed_at": None,
    },
    # Waiting for
    {
        "id": 4, "title": "Waiting on Bob", "status": "waiting_for",
        "due_date": None, "project_id": 2,
        "is_recurring": False, "created_at": TWO_DAYS_AGO_TS,
        "completed_at": None, "last_completed_at": None,
    },
    # Inbox
    {
        "id": 5, "title": "Inbox item", "status": "inbox",
        "due_date": None, "project_id": None,
        "is_recurring": False, "created_at": TODAY_TS,
        "completed_at": None, "last_completed_at": None,
    },
    # Done yesterday (for completed count)
    {
        "id": 6, "title": "Finished yesterday", "status": "done",
        "due_date": None, "project_id": None,
        "is_recurring": False, "created_at": TWO_DAYS_AGO_TS,
        "completed_at": YESTERDAY_TS, "last_completed_at": None,
    },
]


def _mock_endpoints():
    respx.get(f"{BASE}/export/tasks.json").mock(return_value=httpx.Response(200, json=TASKS))
    respx.get(f"{BASE}/export/projects.json").mock(return_value=httpx.Response(200, json=PROJECTS))


@respx.mock
def test_report_generates_markdown(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    _mock_endpoints()
    result = runner.invoke(cli, ["report"])
    assert result.exit_code == 0
    assert f"## Focus Report — {TODAY.isoformat()}" in result.output


@respx.mock
def test_report_hard_landscape_section(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    _mock_endpoints()
    result = runner.invoke(cli, ["report"])
    assert "### Do First" in result.output
    assert "Team standup" in result.output


@respx.mock
def test_report_overdue_tasks(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    _mock_endpoints()
    result = runner.invoke(cli, ["report"])
    assert "Overdue report" in result.output


@respx.mock
def test_report_next_actions_table(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    _mock_endpoints()
    result = runner.invoke(cli, ["report"])
    assert "### Next Actions" in result.output
    assert "Urgent next" in result.output
    assert "Days Remaining" in result.output


@respx.mock
def test_report_waiting_for_with_days(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    _mock_endpoints()
    result = runner.invoke(cli, ["report"])
    assert "### Waiting For" in result.output
    assert "Waiting on Bob" in result.output
    assert "Days Waiting" in result.output


@respx.mock
def test_report_inbox_count(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    _mock_endpoints()
    result = runner.invoke(cli, ["report"])
    assert "### Inbox (1 tasks to clarify)" in result.output
    assert "Inbox item" in result.output


@respx.mock
def test_report_tomorrow_flag(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    _mock_endpoints()
    tomorrow = (TODAY + timedelta(days=1)).isoformat()
    result = runner.invoke(cli, ["report", "--tomorrow"])
    assert result.exit_code == 0
    assert f"## Focus Report — {tomorrow}" in result.output


@respx.mock
def test_report_custom_date(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    _mock_endpoints()
    result = runner.invoke(cli, ["report", "--date", "2026-04-01"])
    assert result.exit_code == 0
    assert "## Focus Report — 2026-04-01" in result.output


@respx.mock
def test_report_project_name_resolution(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    _mock_endpoints()
    result = runner.invoke(cli, ["report"])
    assert "Work Project" in result.output
    assert "Personal" in result.output


@respx.mock
def test_report_completed_count(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", BASE)
    _mock_endpoints()
    result = runner.invoke(cli, ["report"])
    assert "### Previous Day" in result.output
    assert f"**1** task(s) completed on {YESTERDAY.isoformat()}" in result.output
