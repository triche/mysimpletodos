"""HTTP client wrapper for the MySimpleTodos API."""

from __future__ import annotations

import click
import httpx


class MSTClient:
    """HTTP client for the MySimpleTodos API."""

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers,
            follow_redirects=False,
            timeout=10.0,
        )

    def get(self, path: str, **kwargs: object) -> httpx.Response:
        """Send a GET request."""
        try:
            resp = self._client.get(path, **kwargs)
        except httpx.ConnectError as exc:
            raise click.ClickException(f"Cannot connect to server: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise click.ClickException(f"Request timed out: {exc}") from exc
        if resp.status_code >= 400:
            raise click.ClickException(
                f"Server returned {resp.status_code}: {resp.text[:200]}"
            )
        return resp

    def post_form(self, path: str, data: dict[str, str], **kwargs: object) -> httpx.Response:
        """Send a POST request with form-encoded data. Treats 3xx as success."""
        try:
            resp = self._client.post(path, data=data, **kwargs)
        except httpx.ConnectError as exc:
            raise click.ClickException(f"Cannot connect to server: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise click.ClickException(f"Request timed out: {exc}") from exc
        if resp.status_code >= 400:
            raise click.ClickException(
                f"Server returned {resp.status_code}: {resp.text[:200]}"
            )
        return resp

    def health(self) -> dict:
        """Check server health."""
        resp = self.get("/health")
        return resp.json()

    def get_tasks(self, status: str | None = None) -> list[dict]:
        """Fetch tasks via export endpoint."""
        params: dict[str, str] = {}
        if status:
            params["status"] = status
        resp = self.get("/export/tasks.json", params=params)
        return resp.json()

    def get_projects(self) -> list[dict]:
        """Fetch projects via export endpoint."""
        resp = self.get("/export/projects.json")
        return resp.json()

    def create_task(self, title: str, project_id: int | None = None) -> None:
        """Create a new task."""
        data: dict[str, str] = {"title": title}
        if project_id is not None:
            data["project_id"] = str(project_id)
        self.post_form("/tasks", data)

    def complete_task(self, task_id: int) -> None:
        """Complete a task."""
        self.post_form(f"/tasks/{task_id}/complete", {})

    def reopen_task(self, task_id: int) -> None:
        """Reopen a task."""
        self.post_form(f"/tasks/{task_id}/reopen", {})

    def update_task(self, task_id: int, **fields: str) -> None:
        """Update a task via the full update route."""
        self.post_form(f"/tasks/{task_id}/update", fields)

    def quick_update_task(self, task_id: int, field: str, value: str) -> None:
        """Update a single field via quick-update."""
        self.post_form(f"/tasks/{task_id}/quick-update", {"field": field, field: value})

    def export_tasks(self, fmt: str = "json", status: str | None = None) -> str:
        """Export tasks in the given format. Returns raw response text."""
        params: dict[str, str] = {}
        if status:
            params["status"] = status
        resp = self.get(f"/export/tasks.{fmt}", params=params)
        return resp.text

    def export_projects(self, fmt: str = "json") -> str:
        """Export projects in the given format. Returns raw response text."""
        resp = self.get(f"/export/projects.{fmt}")
        return resp.text

    def download_backup(self) -> bytes:
        """Download a database backup. Returns raw bytes."""
        try:
            resp = self._client.get("/backup/download")
        except httpx.ConnectError as exc:
            raise click.ClickException(f"Cannot connect to server: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise click.ClickException(f"Request timed out: {exc}") from exc
        if resp.status_code >= 400:
            raise click.ClickException(
                f"Server returned {resp.status_code}: {resp.text[:200]}"
            )
        return resp.content

    def upload_restore(self, data: bytes, filename: str = "backup.db") -> None:
        """Upload a database backup for restore."""
        try:
            resp = self._client.post(
                "/backup/restore",
                files={"file": (filename, data, "application/octet-stream")},
            )
        except httpx.ConnectError as exc:
            raise click.ClickException(f"Cannot connect to server: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise click.ClickException(f"Request timed out: {exc}") from exc
        if resp.status_code >= 400:
            raise click.ClickException(
                f"Server returned {resp.status_code}: {resp.text[:200]}"
            )
