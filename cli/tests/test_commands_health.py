"""Tests for the health command."""

from __future__ import annotations

import httpx
import respx

from mst_cli.main import cli


@respx.mock
def test_health_success(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", "http://test:8080")
    respx.get("http://test:8080/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    result = runner.invoke(cli, ["health"])
    assert result.exit_code == 0
    assert "✓ Server is healthy" in result.output


@respx.mock
def test_health_failure(runner, monkeypatch):
    monkeypatch.setenv("MST_SERVER_URL", "http://test:8080")
    respx.get("http://test:8080/health").mock(return_value=httpx.Response(500, text="error"))
    result = runner.invoke(cli, ["health"])
    assert result.exit_code != 0
    assert "✗" in result.stderr or "✗" in result.output
