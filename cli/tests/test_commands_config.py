"""Tests for the config commands."""

from __future__ import annotations

from mst_cli.config import load_config
from mst_cli.main import cli


def test_config_init_creates_file(runner, isolated_config):
    result = runner.invoke(cli, ["config", "init"], input="http://test:8080\nmst_secret\n")
    assert result.exit_code == 0
    assert "✓ Configuration saved" in result.output
    config = load_config()
    assert config["server"]["url"] == "http://test:8080"
    assert config["auth"]["api_key"] == "mst_secret"


def test_config_show_masked_key(runner, isolated_config):
    from mst_cli.config import save_config

    save_config({"server": {"url": "http://x:8080"}, "auth": {"api_key": "mst_abcdef123456"}})
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "http://x:8080" in result.output
    assert "mst_••••••123456" in result.output
    assert "mst_abcdef123456" not in result.output


def test_config_show_no_key(runner, isolated_config):
    result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "not set" in result.output


def test_config_set_server_url(runner, isolated_config):
    result = runner.invoke(cli, ["config", "set", "server.url", "http://new:9090"])
    assert result.exit_code == 0
    config = load_config()
    assert config["server"]["url"] == "http://new:9090"


def test_config_set_api_key(runner, isolated_config):
    result = runner.invoke(cli, ["config", "set", "auth.api_key", "mst_newkey"])
    assert result.exit_code == 0
    config = load_config()
    assert config["auth"]["api_key"] == "mst_newkey"


def test_help_shows_ascii_banner(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "██████╗" in result.output
    assert "MySimpleTodos" in result.output


def test_subcommand_help_no_banner(runner):
    result = runner.invoke(cli, ["config", "--help"])
    assert result.exit_code == 0
    assert "██████╗" not in result.output


def test_version_flag(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
