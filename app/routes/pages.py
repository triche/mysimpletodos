"""Page routes."""

from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from app.db import get_session
from app.models import TaskStatus
from app.routes import templates
from app.routes.helpers import (
    base_context,
    parse_bool_filter,
    parse_status_filter,
    redirect_back,
    safe_back_url,
)
from app.services.project_service import (
    can_complete_project,
    complete_project,
    create_project,
    get_project,
    get_project_task_counts,
    list_projects,
    update_project,
)
from app.services.task_service import (
    list_tasks,
    list_tasks_due_today,
    list_tasks_overdue,
    search_tasks,
)

router = APIRouter(tags=["pages"])

STATUS_LABELS: dict[str, str] = {s.value: s.label for s in TaskStatus}


@router.get("/")
def home() -> RedirectResponse:
    return RedirectResponse("/inbox", status_code=302)


@router.get("/inbox", response_class=HTMLResponse)
def inbox(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    tasks = list_tasks(session, status=TaskStatus.INBOX)
    projects_all = list_projects(session, include_completed=True)
    active_projects = list_projects(session)
    projects_map = {p.id: p.name for p in projects_all}
    ctx = base_context(session)
    ctx.update({
        "tasks": tasks,
        "projects": projects_map,
        "projects_list": active_projects,
        "status_labels": STATUS_LABELS,
    })
    return templates.TemplateResponse(request, "inbox.html", ctx)


@router.get("/today", response_class=HTMLResponse)
def today(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    overdue = list_tasks_overdue(session)
    due_today = list_tasks_due_today(session)
    projects_all = list_projects(session, include_completed=True)
    active_projects = list_projects(session)
    projects_map = {p.id: p.name for p in projects_all}
    ctx = base_context(session)
    ctx.update({
        "overdue": overdue,
        "due_today": due_today,
        "projects": projects_map,
        "projects_list": active_projects,
        "status_labels": STATUS_LABELS,
        "today_date": date.today().isoformat(),
    })
    return templates.TemplateResponse(request, "today.html", ctx)


@router.get("/projects", response_class=HTMLResponse)
def projects_list(
    request: Request,
    show: str = "open",
    has_due_date: str = "",
    session: Session = Depends(get_session),
) -> HTMLResponse:
    include_completed = show == "all"
    due_filter = parse_bool_filter(has_due_date)
    projects = list_projects(
        session, include_completed=include_completed, has_due_date=due_filter,
    )
    if include_completed:
        # Open projects first, then completed; alphabetical within each group
        projects = sorted(projects, key=lambda p: (p.completed_at is not None, p.name))
    counts = {p.id: get_project_task_counts(session, p.id) for p in projects}  # type: ignore[arg-type]
    ctx = base_context(session)
    ctx.update({
        "projects": projects,
        "counts": counts,
        "today": date.today(),
        "f_show": show,
        "f_has_due_date": has_due_date,
    })
    return templates.TemplateResponse(request, "projects_list.html", ctx)


@router.post("/projects")
def create_project_route(
    name: str = Form(""),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    if name.strip():
        create_project(session, name=name.strip())
    return RedirectResponse("/projects", status_code=303)


@router.post("/projects/{project_id}/complete")
def complete_project_route(
    project_id: int,
    session: Session = Depends(get_session),
) -> RedirectResponse:
    project = get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    completed = complete_project(session, project_id)
    if completed is None:
        raise HTTPException(status_code=409, detail="Project has open tasks")
    return RedirectResponse(f"/projects/{project_id}", status_code=303)  # noqa: E501


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(
    request: Request,
    project_id: int,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    project = get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = list_tasks(session, project_id=project_id)

    # Group tasks by status, ordered to match the STATUS_LABELS dropdown
    grouped: dict[str, list] = {}
    for label in STATUS_LABELS.values():
        grouped[label] = []
    for task in tasks:
        label = STATUS_LABELS.get(task.status.value, task.status.value)
        grouped.setdefault(label, []).append(task)
    # Drop empty groups
    grouped = {k: v for k, v in grouped.items() if v}

    completable = can_complete_project(session, project_id)
    ctx = base_context(session)
    ctx.update({
        "project": project,
        "grouped_tasks": grouped,
        "status_labels": STATUS_LABELS,
        "can_complete": completable,
        "today": date.today(),
    })
    return templates.TemplateResponse(request, "project_detail.html", ctx)



@router.get("/projects/{project_id}/edit", response_class=HTMLResponse)
def edit_project_page(
    request: Request,
    project_id: int,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    project = get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    back_url = request.query_params.get("back_url") or redirect_back(request, "/projects")
    ctx = base_context(session)
    ctx.update({"project": project, "back_url": back_url})
    return templates.TemplateResponse(request, "project_edit.html", ctx)


@router.post("/projects/{project_id}/update")
def update_project_route(
    project_id: int,
    name: str = Form(...),
    description: str = Form(""),
    notes: str = Form(""),
    due_date: str = Form(""),
    action: str = Form("save"),
    back_url: str = Form("/projects"),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    project = get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if not name.strip():
        return RedirectResponse(f"/projects/{project_id}/edit", status_code=303)

    parsed_due = date.fromisoformat(due_date) if due_date else None
    update_project(
        session,
        project_id,
        name=name.strip(),
        description=description.strip() if description.strip() else None,
        notes=notes.strip() if notes.strip() else None,
        due_date=parsed_due,
    )

    if action == "close":
        return RedirectResponse(safe_back_url(back_url, f"/projects/{project_id}"), status_code=303)
    # Preserve back_url through the Save redirect so it survives round-trips
    safe = safe_back_url(back_url, f"/projects/{project_id}")
    return RedirectResponse(
        f"/projects/{project_id}/edit?back_url={quote(safe)}", status_code=303
    )


@router.get("/tasks", response_class=HTMLResponse)
def all_tasks(
    request: Request,
    status: str = "all_in_work",
    project_id: str = "",
    q: str = "",
    has_due_date: str = "",
    is_recurring: str = "",
    session: Session = Depends(get_session),
) -> HTMLResponse:
    projects_list_all = list_projects(session, include_completed=True)
    active_projects = list_projects(session)
    projects_map = {p.id: p.name for p in projects_list_all}

    # Parse filters
    exclude_done = status == "all_in_work"
    status_filter = None if exclude_done else parse_status_filter(status)

    pid: int | None = None
    no_project = False
    if project_id == "none":
        no_project = True
    elif project_id:
        try:
            pid = int(project_id)
        except ValueError:
            pass

    tasks = search_tasks(
        session,
        status=status_filter,
        exclude_done=exclude_done,
        project_id=pid,
        no_project=no_project,
        q=q.strip() if q else None,
        has_due_date=parse_bool_filter(has_due_date),
        is_recurring=parse_bool_filter(is_recurring),
    )

    # When showing all statuses, push done tasks to the bottom
    if not status and not exclude_done:
        tasks = sorted(tasks, key=lambda t: t.status == TaskStatus.DONE)

    ctx = base_context(session)
    ctx.update({
        "tasks": tasks,
        "projects": projects_map,
        "projects_list": active_projects,
        "projects_filter_list": projects_list_all,
        "status_labels": STATUS_LABELS,
        "today": date.today(),
        # Current filter values for the form
        "f_status": status,
        "f_project_id": project_id,
        "f_q": q,
        "f_has_due_date": has_due_date,
        "f_is_recurring": is_recurring,
    })
    return templates.TemplateResponse(request, "tasks_list.html", ctx)