"""Shared fixtures for CLI tests."""

from __future__ import annotations

import pytest
from click.testing import CliRunner


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Use a temp directory for config to avoid touching real ~/.gtd."""
    config_dir = tmp_path / ".gtd"
    monkeypatch.setenv("MST_CONFIG_DIR", str(config_dir))
    # Clear any env overrides so tests start clean
    monkeypatch.delenv("MST_API_KEY", raising=False)
    monkeypatch.delenv("MST_SERVER_URL", raising=False)
    return config_dir


@pytest.fixture
def runner():
    return CliRunner()
