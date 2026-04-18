"""Config module for reading/writing ~/.mst/config.toml."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import tomli_w

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

DEFAULT_SERVER_URL = "http://localhost:8080"


def get_config_dir() -> Path:
    """Return ~/.mst, respecting MST_CONFIG_DIR env override."""
    override = os.environ.get("MST_CONFIG_DIR")
    if override:
        return Path(override)
    return Path.home() / ".mst"


def get_config_path() -> Path:
    """Return ~/.mst/config.toml."""
    return get_config_dir() / "config.toml"


def ensure_config_dir() -> Path:
    """Create ~/.mst/ with 0700 permissions if it doesn't exist."""
    config_dir = get_config_dir()
    if not config_dir.exists():
        config_dir.mkdir(parents=True, mode=0o700)
    return config_dir


def load_config() -> dict:
    """Read and return config dict. Returns defaults if file missing."""
    config_path = get_config_path()
    if not config_path.exists():
        return {"server": {"url": DEFAULT_SERVER_URL}, "auth": {}}
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def save_config(config: dict) -> None:
    """Write config dict to TOML file with 0600 permissions."""
    ensure_config_dir()
    config_path = get_config_path()
    with open(config_path, "wb") as f:
        tomli_w.dump(config, f)
    config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def get_server_url(ctx_override: str | None = None) -> str:
    """Resolve server URL: CLI flag > env var > config file > default."""
    if ctx_override:
        return ctx_override
    env_url = os.environ.get("MST_SERVER_URL")
    if env_url:
        return env_url
    config = load_config()
    return config.get("server", {}).get("url", DEFAULT_SERVER_URL)


def get_api_key() -> str | None:
    """Resolve API key: env var > config file."""
    env_key = os.environ.get("MST_API_KEY")
    if env_key:
        return env_key
    config = load_config()
    return config.get("auth", {}).get("api_key")
