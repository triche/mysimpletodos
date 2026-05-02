"""Tests for inline quick-update selectors on task list items."""

from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import TaskStatus
from app.services.project_service import complete_project, create_project
from app.services.task_service import create_task, get_task

# ---------------------------------------------------------------------------
# Phase 1: POST /tasks/{id}/quick-update endpoint
# ---------------------------------------------------------------------------


class TestQuickUpdateEndpoint:
    def test_quick_update_status(self, client: TestClient, db_session: Session) -> None:
        task = create_task(db_session, title="Status task")
        response = client.post(
            f"/tasks/{task.id}/quick-update",
            data={"field": "status", "status": "next_action"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        db_session.expire_all()
        updated = get_task(db_session, task.id)  # type: ignore[arg-type]
        assert updated is not None
        assert updated.status == TaskStatus.NEXT_ACTION

    def test_quick_update_due_date(self, client: TestClient, db_session: Session) -> None:
        task = create_task(db_session, title="Date task")
        response = client.post(
            f"/tasks/{task.id}/quick-update",
            data={"field": "due_date", "due_date": "2026-04-01"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        db_session.expire_all()
        updated = get_task(db_session, task.id)  # type: ignore[arg-type]
        assert updated is not None
        assert updated.due_date == date(2026, 4, 1)

    def test_quick_update_clear_due_date(
        self, client: TestClient, db_session: Session
    ) -> None:
        task = create_task(db_session, title="Clear date", due_date=date(2026, 5, 1))
        response = client.post(
            f"/tasks/{task.id}/quick-update",
            data={"field": "due_date", "due_date": ""},
            follow_redirects=False,
        )
        assert response.status_code == 303
        db_session.expire_all()
        updated = get_task(db_session, task.id)  # type: ignore[arg-type]
        assert updated is not None
        assert updated.due_date is None

    def test_quick_update_project(self, client: TestClient, db_session: Session) -> None:
        project = create_project(db_session, name="Quick proj")
        task = create_task(db_session, title="Proj task")
        response = client.post(
            f"/tasks/{task.id}/quick-update",
            data={"field": "project_id", "project_id": str(project.id)},
            follow_redirects=False,
        )
        assert response.status_code == 303
        db_session.expire_all()
        updated = get_task(db_session, task.id)  # type: ignore[arg-type]
        assert updated is not None
        assert updated.project_id == project.id

    def test_quick_update_clear_project(
        self, client: TestClient, db_session: Session
    ) -> None:
        project = create_project(db_session, name="Remove proj")
        task = create_task(
            db_session, title="Has proj", project_id=project.id  # type: ignore[arg-type]
        )
        response = client.post(
            f"/tasks/{task.id}/quick-update",
            data={"field": "project_id", "project_id": ""},
            follow_redirects=False,
        )
        assert response.status_code == 303
        db_session.expire_all()
        updated = get_task(db_session, task.id)  # type: ignore[arg-type]
        assert updated is not None
        assert updated.project_id is None

    def test_quick_update_redirects_to_referer(
        self, client: TestClient, db_session: Session
    ) -> None:
        task = create_task(db_session, title="Referer task")
        response = client.post(
            f"/tasks/{task.id}/quick-update",
            data={"field": "status", "status": "scheduled"},
            headers={"referer": "http://testserver/today"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/today"

    def test_quick_update_fallback_redirect(
        self, client: TestClient, db_session: Session
    ) -> None:
        task = create_task(db_session, title="No referer task")
        response = client.post(
            f"/tasks/{task.id}/quick-update",
            data={"field": "status", "status": "inbox"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/inbox"

    def test_quick_update_404(self, client: TestClient) -> None:
        response = client.post(
            "/tasks/99999/quick-update",
            data={"field": "status", "status": "inbox"},
            follow_redirects=False,
        )
        assert response.status_code == 404

    def test_quick_update_invalid_status_ignored(
        self, client: TestClient, db_session: Session
    ) -> None:
        task = create_task(db_session, title="Bad status task")
        response = client.post(
            f"/tasks/{task.id}/quick-update",
            data={"field": "status", "status": "bogus"},
            follow_redirects=False,
        )
        # Should redirect without crashing; status unchanged
        assert response.status_code == 303
        db_session.expire_all()
        updated = get_task(db_session, task.id)  # type: ignore[arg-type]
        assert updated is not None
        assert updated.status == TaskStatus.INBOX

    def test_quick_update_status_reflects_in_db(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Changing status from done→inbox should revert the done state."""
        task = create_task(db_session, title="Was done", status=TaskStatus.DONE)
        response = client.post(
            f"/tasks/{task.id}/quick-update",
            data={"field": "status", "status": "inbox"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        db_session.expire_all()
        updated = get_task(db_session, task.id)  # type: ignore[arg-type]
        assert updated is not None
        assert updated.status == TaskStatus.INBOX


# ---------------------------------------------------------------------------
# Phase 2 & 4: Inline selectors present on list pages
# ---------------------------------------------------------------------------


class TestInlineSelectorsOnInbox:
    def test_inbox_has_status_selector(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_task(db_session, title="Selector task")
        response = client.get("/inbox")
        assert 'name="status"' in response.text
        assert "quick-update" in response.text

    def test_inbox_has_date_selector(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_task(db_session, title="Date selector task")
        response = client.get("/inbox")
        assert 'name="due_date"' in response.text
        assert 'type="date"' in response.text

    def test_inbox_has_project_selector(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_task(db_session, title="Proj selector task")
        response = client.get("/inbox")
        assert 'name="project_id"' in response.text

    def test_inbox_project_selector_hides_completed_projects(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_project(db_session, name="Open Inline Project")
        completed_project = create_project(db_session, name="Completed Inline Project")
        complete_project(db_session, completed_project.id)  # type: ignore[arg-type]
        create_task(db_session, title="Proj selector task")

        response = client.get("/inbox")

        assert "Open Inline Project" in response.text
        assert "Completed Inline Project" not in response.text

    def test_selectors_reflect_current_values(
        self, client: TestClient, db_session: Session
    ) -> None:
        project = create_project(db_session, name="Reflect Proj")
        create_task(
            db_session,
            title="Reflect task",
            status=TaskStatus.NEXT_ACTION,
            due_date=date(2026, 4, 1),
            project_id=project.id,  # type: ignore[arg-type]
        )
        response = client.get("/inbox")
        # Not on inbox since it's NEXT_ACTION — check All Tasks instead
        response = client.get("/tasks?status=next_action")
        html = response.text
        # Status option should be selected
        assert 'value="next_action" selected' in html
        # Date input should carry the value
        assert 'value="2026-04-01"' in html
        # Project option should be selected
        assert f'value="{project.id}" selected' in html

    def test_status_selector_has_color_class(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_task(db_session, title="Color class task", status=TaskStatus.NEXT_ACTION)
        response = client.get("/tasks?status=next_action")
        assert "inline-status" in response.text
        assert "badge-status-next_action" in response.text


class TestInlineSelectorsOnToday:
    def test_today_selectors_present(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_task(db_session, title="Today sel task", due_date=date.today())
        response = client.get("/today")
        assert 'name="status"' in response.text
        assert 'name="due_date"' in response.text
        assert 'name="project_id"' in response.text
        assert "quick-update" in response.text


class TestInlineSelectorsOnAllTasks:
    def test_all_tasks_selectors_present(
        self, client: TestClient, db_session: Session
    ) -> None:
        create_task(db_session, title="All sel task")
        response = client.get("/tasks?status=")
        assert 'name="status"' in response.text
        assert 'name="due_date"' in response.text
        assert 'name="project_id"' in response.text
        assert "quick-update" in response.text


class TestInlineSelectorsOnProjectDetail:
    def test_project_detail_selectors_present(
        self, client: TestClient, db_session: Session
    ) -> None:
        project = create_project(db_session, name="Detail proj")
        create_task(
            db_session,
            title="PD sel task",
            project_id=project.id,  # type: ignore[arg-type]
        )
        response = client.get(f"/projects/{project.id}")
        assert 'name="status"' in response.text
        assert 'name="due_date"' in response.text
        assert "quick-update" in response.text

    def test_project_detail_hides_project_selector(
        self, client: TestClient, db_session: Session
    ) -> None:
        project = create_project(db_session, name="No proj sel")
        create_task(
            db_session,
            title="No proj sel task",
            project_id=project.id,  # type: ignore[arg-type]
        )
        response = client.get(f"/projects/{project.id}")
        # The quick-add form has a hidden project_id, but no inline project
        # selector should appear inside the quick-update forms.
        assert 'class="inline-select inline-project"' not in response.text


# ---------------------------------------------------------------------------
# Phase 6: End-to-end quick triage workflow
# ---------------------------------------------------------------------------


class TestQuickTriageWorkflow:
    def test_quick_triage_from_inbox(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Full triage: create inbox task, quick-set status + date + project."""
        project = create_project(db_session, name="Triage proj")
        task = create_task(db_session, title="Triage me")
        today = date.today()

        # Quick-update status
        client.post(
            f"/tasks/{task.id}/quick-update",
            data={"field": "status", "status": "next_action"},
            follow_redirects=False,
        )
        # Quick-update due date to today
        client.post(
            f"/tasks/{task.id}/quick-update",
            data={"field": "due_date", "due_date": str(today)},
            follow_redirects=False,
        )
        # Quick-update project
        client.post(
            f"/tasks/{task.id}/quick-update",
            data={"field": "project_id", "project_id": str(project.id)},
            follow_redirects=False,
        )

        # Verify on Today page
        response = client.get("/today")
        assert "Triage me" in response.text

        # Verify on Project detail page
        response = client.get(f"/projects/{project.id}")
        assert "Triage me" in response.text

        # Verify final state in DB
        db_session.expire_all()
        updated = get_task(db_session, task.id)  # type: ignore[arg-type]
        assert updated is not None
        assert updated.status == TaskStatus.NEXT_ACTION
        assert updated.due_date == today
        assert updated.project_id == project.id
