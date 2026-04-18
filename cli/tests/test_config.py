"""Tests for the config module."""

from __future__ import annotations

from mst_cli.config import (
    ensure_config_dir,
    get_api_key,
    get_config_dir,
    get_server_url,
    load_config,
    save_config,
)


def test_get_config_dir_default(monkeypatch):
    monkeypatch.delenv("MST_CONFIG_DIR", raising=False)
    d = get_config_dir()
    assert d.name == ".mst"
    assert str(d).endswith("/.mst")


def test_get_config_dir_env_override(monkeypatch, tmp_path):
    override = tmp_path / "custom"
    monkeypatch.setenv("MST_CONFIG_DIR", str(override))
    assert get_config_dir() == override


def test_ensure_config_dir_creates(isolated_config):
    assert not isolated_config.exists()
    result = ensure_config_dir()
    assert result.exists()
    mode = result.stat().st_mode
    assert mode & 0o777 == 0o700


def test_save_config_permissions(isolated_config):
    save_config({"server": {"url": "http://example.com"}, "auth": {}})
    config_path = isolated_config / "config.toml"
    assert config_path.exists()
    mode = config_path.stat().st_mode
    assert mode & 0o777 == 0o600


def test_load_config_missing_file():
    config = load_config()
    assert config["server"]["url"] == "http://localhost:8080"
    assert config["auth"] == {}


def test_load_save_roundtrip():
    data = {"server": {"url": "http://test:9090"}, "auth": {"api_key": "mst_abc123"}}
    save_config(data)
    loaded = load_config()
    assert loaded == data


def test_get_server_url_priority(monkeypatch):
    # Default
    assert get_server_url() == "http://localhost:8080"

    # Config file
    save_config({"server": {"url": "http://from-config:1234"}, "auth": {}})
    assert get_server_url() == "http://from-config:1234"

    # Env var overrides config
    monkeypatch.setenv("MST_SERVER_URL", "http://from-env:5678")
    assert get_server_url() == "http://from-env:5678"

    # CLI flag overrides env
    assert get_server_url(ctx_override="http://from-flag:9999") == "http://from-flag:9999"


def test_get_api_key_env_override(monkeypatch):
    save_config({"server": {"url": "http://x"}, "auth": {"api_key": "mst_from_config"}})
    assert get_api_key() == "mst_from_config"

    monkeypatch.setenv("MST_API_KEY", "mst_from_env")
    assert get_api_key() == "mst_from_env"
