"""Tests for the HTTP client."""

from __future__ import annotations

import click
import httpx
import pytest
import respx

from mst_cli.client import MSTClient


@respx.mock
def test_client_sets_auth_header():
    client = MSTClient("http://test:8080", api_key="mst_abc123")
    route = respx.get("http://test:8080/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    client.health()
    assert route.called
    req = route.calls[0].request
    assert req.headers["authorization"] == "Bearer mst_abc123"


@respx.mock
def test_client_no_auth_header_without_key():
    client = MSTClient("http://test:8080", api_key=None)
    route = respx.get("http://test:8080/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    client.health()
    req = route.calls[0].request
    assert "authorization" not in req.headers


@respx.mock
def test_health_returns_status():
    respx.get("http://test:8080/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    client = MSTClient("http://test:8080")
    assert client.health() == {"status": "ok"}


@respx.mock
def test_get_tasks_returns_list():
    tasks = [{"id": 1, "title": "Test"}]
    respx.get("http://test:8080/export/tasks.json").mock(
        return_value=httpx.Response(200, json=tasks)
    )
    client = MSTClient("http://test:8080")
    assert client.get_tasks() == tasks


@respx.mock
def test_get_tasks_with_status_filter():
    respx.get("http://test:8080/export/tasks.json", params={"status": "inbox"}).mock(
        return_value=httpx.Response(200, json=[])
    )
    client = MSTClient("http://test:8080")
    client.get_tasks(status="inbox")


@respx.mock
def test_post_form_sends_encoded_data():
    route = respx.post("http://test:8080/tasks").mock(
        return_value=httpx.Response(303, headers={"location": "/inbox"})
    )
    client = MSTClient("http://test:8080")
    client.create_task("Buy milk")
    req = route.calls[0].request
    assert b"title=Buy+milk" in req.content or b"title=Buy%20milk" in req.content


@respx.mock
def test_post_form_treats_redirect_as_success():
    respx.post("http://test:8080/tasks/1/complete").mock(
        return_value=httpx.Response(303, headers={"location": "/inbox"})
    )
    client = MSTClient("http://test:8080")
    # Should not raise
    client.complete_task(1)


@respx.mock
def test_http_error_raises_click_exception():
    respx.get("http://test:8080/health").mock(return_value=httpx.Response(500, text="fail"))
    client = MSTClient("http://test:8080")
    with pytest.raises(click.ClickException, match="500"):
        client.health()


def test_connection_error_raises_click_exception():
    client = MSTClient("http://doesnotexist.invalid:9999")
    with pytest.raises(click.ClickException, match="Cannot connect"):
        client.health()
