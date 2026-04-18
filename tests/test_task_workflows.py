"""Tests for Phase 2: Core task workflow routes."""

from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import RecurrenceType, TaskStatus
from app.services.project_service import create_project
from app.services.task_service import create_task, get_task, list_tasks

# --- Home redirect ---


def test_home_redirects_to_inbox(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/inbox" in response.headers["location"]


# --- Inbox page ---


def test_inbox_returns_html(client: TestClient) -> None:
    response = client.get("/inbox")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_inbox_shows_inbox_tasks(client: TestClient, db_session: Session) -> None:
    create_task(db_session, title="Inbox item")
    create_task(db_session, title="Done item", status=TaskStatus.DONE)

    response = client.get("/inbox")

    assert "Inbox item" in response.text
    assert "Done item" not in response.text


def test_inbox_has_quick_add_form(client: TestClient) -> None:
    response = client.get("/inbox")

    assert "<form" in response.text
    assert 'action="/tasks"' in response.text
    assert 'method="post"' in response.text


def test_inbox_renders_markdown_notes_safely(client: TestClient, db_session: Session) -> None:
    create_task(db_session, title="MD Task", notes="**bold text**")

    response = client.get("/inbox")

    assert "<strong>bold text</strong>" in response.text


def test_inbox_renders_markdown_checkboxes(client: TestClient, db_session: Session) -> None:
    create_task(db_session, title="Checklist", notes="- [ ] todo\n- [x] done")

    response = client.get("/inbox")

    assert 'type="checkbox"' in response.text
    assert 'checked="checked"' in response.text


def test_inbox_renders_markdown_tables(client: TestClient, db_session: Session) -> None:
    create_task(db_session, title="Table Task", notes="| A | B |\n|---|---|\n| 1 | 2 |")

    response = client.get("/inbox")

    assert "<table>" in response.text
    assert "<td>1</td>" in response.text


def test_inbox_sanitizes_unsafe_html_in_notes(client: TestClient, db_session: Session) -> None:
    create_task(db_session, title="XSS Task", notes="<script>alert('xss')</script>")

    response = client.get("/inbox")

    assert "<script>alert('xss')</script>" not in response.text


# --- Task creation ---


def test_create_task_redirects_to_inbox(client: TestClient) -> None:
    response = client.post("/tasks", data={"title": "New task"}, follow_redirects=False)

    assert response.status_code == 303
    assert "/inbox" in response.headers["location"]


def test_create_task_defaults_to_inbox_status(client: TestClient, db_session: Session) -> None:
    client.post("/tasks", data={"title": "Created via form"})

    db_session.expire_all()
    tasks = list_tasks(db_session, status=TaskStatus.INBOX)
    assert any(t.title == "Created via form" for t in tasks)


def test_create_task_empty_title_not_created(client: TestClient, db_session: Session) -> None:
    client.post("/tasks", data={"title": ""})

    db_session.expire_all()
    tasks = list_tasks(db_session)
    assert not any(t.title == "" for t in tasks)


def test_task_can_remain_unassigned_to_project(
    client: TestClient, db_session: Session
) -> None:
    client.post("/tasks", data={"title": "No project"})

    db_session.expire_all()
    tasks = list_tasks(db_session, status=TaskStatus.INBOX)
    task = next(t for t in tasks if t.title == "No project")
    assert task.project_id is None


# --- Task edit page ---


def test_edit_page_returns_html(client: TestClient, db_session: Session) -> None:
    task = create_task(db_session, title="Edit me")

    response = client.get(f"/tasks/{task.id}/edit")

    assert response.status_code == 200
    assert "Edit me" in response.text


def test_edit_page_shows_raw_markdown_in_textarea(
    client: TestClient, db_session: Session
) -> None:
    task = create_task(db_session, title="With notes", notes="# Hello\n\n**bold**")

    response = client.get(f"/tasks/{task.id}/edit")

    assert "# Hello" in response.text


def test_edit_page_shows_project_dropdown(client: TestClient, db_session: Session) -> None:
    create_project(db_session, name="Test Project")
    task = create_task(db_session, title="Editable")

    response = client.get(f"/tasks/{task.id}/edit")

    assert "Test Project" in response.text


def test_edit_page_shows_status_options(client: TestClient, db_session: Session) -> None:
    task = create_task(db_session, title="Status check")

    response = client.get(f"/tasks/{task.id}/edit")

    assert "inbox" in response.text
    assert "next_action" in response.text
    assert "waiting_for" in response.text
    assert "scheduled" in response.text
    assert "someday_maybe" in response.text
    assert "done" in response.text


def test_edit_page_not_found(client: TestClient) -> None:
    response = client.get("/tasks/9999/edit")

    assert response.status_code == 404


# --- Task update ---


def test_update_task_redirects(client: TestClient, db_session: Session) -> None:
    task = create_task(db_session, title="Old title")

    response = client.post(
        f"/tasks/{task.id}/update",
        data={"title": "New title", "status": "next_action"},
        follow_redirects=False,
    )

    assert response.status_code == 303


def test_update_task_changes_fields(client: TestClient, db_session: Session) -> None:
    task = create_task(db_session, title="To update")

    client.post(
        f"/tasks/{task.id}/update",
        data={
            "title": "Updated",
            "notes": "# Hello",
            "status": "next_action",
            "due_date": "2026-04-01",
        },
    )

    db_session.expire_all()
    updated = get_task(db_session, task.id)  # type: ignore[arg-type]
    assert updated is not None
    assert updated.title == "Updated"
    assert updated.notes == "# Hello"
    assert updated.status == TaskStatus.NEXT_ACTION
    assert updated.due_date == date(2026, 4, 1)


def test_update_task_moves_between_statuses(
    client: TestClient, db_session: Session
) -> None:
    task = create_task(db_session, title="Status mover")

    for status in ("next_action", "waiting_for", "scheduled", "someday_maybe", "done", "inbox"):
        client.post(
            f"/tasks/{task.id}/update",
            data={"title": "Status mover", "status": status},
        )
        db_session.expire_all()
        updated = get_task(db_session, task.id)  # type: ignore[arg-type]
        assert updated is not None
        assert updated.status == TaskStatus(status)


def test_update_task_assigns_project(client: TestClient, db_session: Session) -> None:
    project = create_project(db_session, name="Target")
    task = create_task(db_session, title="Orphan")

    client.post(
        f"/tasks/{task.id}/update",
        data={"title": "Orphan", "status": "inbox", "project_id": str(project.id)},
    )

    db_session.expire_all()
    updated = get_task(db_session, task.id)  # type: ignore[arg-type]
    assert updated is not None
    assert updated.project_id == project.id


def test_update_task_clears_due_date(client: TestClient, db_session: Session) -> None:
    task = create_task(db_session, title="Has date", due_date=date(2026, 5, 1))

    client.post(
        f"/tasks/{task.id}/update",
        data={"title": "Has date", "status": "inbox", "due_date": ""},
    )

    db_session.expire_all()
    updated = get_task(db_session, task.id)  # type: ignore[arg-type]
    assert updated is not None
    assert updated.due_date is None


def test_update_task_sets_recurrence(client: TestClient, db_session: Session) -> None:
    task = create_task(db_session, title="Make recurring")

    client.post(
        f"/tasks/{task.id}/update",
        data={
            "title": "Make recurring",
            "status": "scheduled",
            "is_recurring": "on",
            "recurrence_type": "weekly",
            "due_date": "2026-04-01",
        },
    )

    db_session.expire_all()
    updated = get_task(db_session, task.id)  # type: ignore[arg-type]
    assert updated is not None
    assert updated.is_recurring is True
    assert updated.recurrence_type == RecurrenceType.WEEKLY


def test_update_task_not_found(client: TestClient) -> None:
    response = client.post(
        "/tasks/9999/update",
        data={"title": "Ghost", "status": "inbox"},
        follow_redirects=False,
    )

    assert response.status_code == 404


# --- Task completion ---


def test_complete_task_redirects(client: TestClient, db_session: Session) -> None:
    task = create_task(db_session, title="Complete me")

    response = client.post(f"/tasks/{task.id}/complete", follow_redirects=False)

    assert response.status_code == 303


def test_complete_non_recurring_task_marks_done(
    client: TestClient, db_session: Session
) -> None:
    task = create_task(db_session, title="One-shot")

    client.post(f"/tasks/{task.id}/complete")

    db_session.expire_all()
    completed = get_task(db_session, task.id)  # type: ignore[arg-type]
    assert completed is not None
    assert completed.status == TaskStatus.DONE


def test_complete_recurring_task_advances_and_preserves(
    client: TestClient, db_session: Session
) -> None:
    task = create_task(
        db_session,
        title="Daily standup",
        is_recurring=True,
        recurrence_type=RecurrenceType.DAILY,
        due_date=date(2026, 3, 17),
        status=TaskStatus.NEXT_ACTION,
    )

    client.post(f"/tasks/{task.id}/complete")

    db_session.expire_all()
    result = get_task(db_session, task.id)  # type: ignore[arg-type]
    assert result is not None
    assert result.due_date == date(2026, 3, 18)
    assert result.is_recurring is True
    assert result.recurrence_type == RecurrenceType.DAILY
    assert result.status != TaskStatus.DONE
    assert result.id == task.id  # same record


def test_complete_task_not_found(client: TestClient) -> None:
    response = client.post("/tasks/9999/complete", follow_redirects=False)

    assert response.status_code == 404


# --- Task reopen ---


def test_reopen_task_redirects(client: TestClient, db_session: Session) -> None:
    task = create_task(db_session, title="Reopen me", status=TaskStatus.DONE)

    response = client.post(f"/tasks/{task.id}/reopen", follow_redirects=False)

    assert response.status_code == 303


def test_reopen_task_sets_inbox(client: TestClient, db_session: Session) -> None:
    task = create_task(db_session, title="Reopen me", status=TaskStatus.DONE)

    client.post(f"/tasks/{task.id}/reopen")

    db_session.expire_all()
    reopened = get_task(db_session, task.id)  # type: ignore[arg-type]
    assert reopened is not None
    assert reopened.status == TaskStatus.INBOX
    assert reopened.completed_at is None


def test_reopen_task_not_found(client: TestClient) -> None:
    response = client.post("/tasks/9999/reopen", follow_redirects=False)

    assert response.status_code == 404
