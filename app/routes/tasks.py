"""Task mutation and edit routes."""

from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from app.config import get_settings
from app.db import get_session
from app.models import RecurrenceType, Task, TaskStatus
from app.routes import templates
from app.routes.helpers import redirect_back, safe_back_url
from app.services.project_service import list_projects
from app.services.task_service import complete_task, create_task, reopen_task, update_task

STATUS_OPTIONS = [(s.value, s.label) for s in TaskStatus]

RECURRENCE_OPTIONS = [
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
    ("interval_days", "Custom Interval (days)"),
]

router = APIRouter(tags=["tasks"])


@router.post("/tasks")
def create_task_route(
    request: Request,
    title: str = Form(""),
    project_id: str = Form(""),
    due_date: str = Form(""),
    status: str = Form(""),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    if not title.strip():
        return RedirectResponse(redirect_back(request), status_code=303)
    kwargs: dict = {"title": title.strip()}
    if project_id:
        kwargs["project_id"] = int(project_id)
    if due_date:
        kwargs["due_date"] = date.fromisoformat(due_date)
    if status:
        kwargs["status"] = TaskStatus(status)
    create_task(session, **kwargs)
    return RedirectResponse(redirect_back(request), status_code=303)


@router.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
def edit_task_page(
    request: Request,
    task_id: int,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    settings = get_settings()
    projects = list_projects(session)
    # Build a map of project_id -> due_date for client-side validation
    project_due_dates = {p.id: str(p.due_date) if p.due_date else "" for p in projects}
    # Prefer explicit query param (preserved across Save round-trips) over Referer
    back_url = request.query_params.get("back_url") or redirect_back(request)
    return templates.TemplateResponse(
        request,
        "task_edit.html",
        {
            "app_name": settings.app_name,
            "task": task,
            "projects": projects,
            "project_due_dates": project_due_dates,
            "statuses": STATUS_OPTIONS,
            "recurrence_types": RECURRENCE_OPTIONS,
            "back_url": back_url,
        },
    )


@router.post("/tasks/{task_id}/update")
def update_task_route(
    request: Request,
    task_id: int,
    title: str = Form(...),
    notes: str = Form(""),
    status: str = Form("inbox"),
    due_date: str = Form(""),
    is_recurring: str = Form(""),
    recurrence_type: str = Form(""),
    recurrence_interval_days: str = Form(""),
    project_id: str = Form(""),
    action: str = Form("save"),
    back_url: str = Form("/inbox"),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if not title.strip():
        return RedirectResponse(f"/tasks/{task_id}/edit", status_code=303)

    update_task(
        session,
        task_id,
        title=title,
        notes=notes if notes.strip() else None,
        status=TaskStatus(status),
        due_date=date.fromisoformat(due_date) if due_date else None,
        is_recurring=is_recurring in ("on", "true", "1"),
        recurrence_type=RecurrenceType(recurrence_type) if recurrence_type else None,
        recurrence_interval_days=(
            int(recurrence_interval_days) if recurrence_interval_days else None
        ),
        project_id=int(project_id) if project_id else None,
    )

    if action == "close":
        return RedirectResponse(safe_back_url(back_url, "/inbox"), status_code=303)
    # Preserve back_url through the Save redirect so it survives round-trips
    safe = safe_back_url(back_url, "/inbox")
    return RedirectResponse(
        f"/tasks/{task_id}/edit?back_url={quote(safe)}", status_code=303
    )


@router.post("/tasks/{task_id}/quick-update")
def quick_update_task_route(
    request: Request,
    task_id: int,
    field: str = Form(...),
    status: str = Form(""),
    due_date: str = Form(""),
    project_id: str = Form(""),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    kwargs: dict = {}
    if field == "status" and status:
        try:
            kwargs["status"] = TaskStatus(status)
        except ValueError:
            pass  # ignore invalid status values
    elif field == "due_date":
        kwargs["due_date"] = date.fromisoformat(due_date) if due_date else None
    elif field == "project_id":
        kwargs["project_id"] = int(project_id) if project_id else None

    if kwargs:
        update_task(session, task_id, **kwargs)

    return RedirectResponse(redirect_back(request), status_code=303)


@router.post("/tasks/{task_id}/complete")
def complete_task_route(
    request: Request,
    task_id: int,
    session: Session = Depends(get_session),
) -> RedirectResponse:
    task = complete_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return RedirectResponse(redirect_back(request), status_code=303)


@router.post("/tasks/{task_id}/reopen")
def reopen_task_route(
    request: Request,
    task_id: int,
    session: Session = Depends(get_session),
) -> RedirectResponse:
    task = reopen_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return RedirectResponse(redirect_back(request), status_code=303)
