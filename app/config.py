"""Application configuration."""

import os
import secrets
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DEFAULT_DATA_DIR = Path("/data")
DEFAULT_DB_FILENAME = "todo.db"


def _default_secret_key() -> str:
    return secrets.token_hex(32)


@dataclass(slots=True)
class Settings:
    app_name: str = "MySimpleTodos"
    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8080
    database_url: str = f"sqlite:///{DEFAULT_DATA_DIR / DEFAULT_DB_FILENAME}"

    # Auth settings
    auth_disabled: bool = True
    auth_secret_key: str = field(default_factory=_default_secret_key)
    auth_session_max_age: int = 604800  # 7 days
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "MySimpleTodos"
    webauthn_origin: str = "http://localhost:8080"

    @property
    def sqlite_path(self) -> Path | None:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            return None
        return Path(self.database_url.removeprefix(prefix))


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "MySimpleTodos"),
        app_env=os.getenv("APP_ENV", "development"),
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8080")),
        database_url=os.getenv(
            "DATABASE_URL",
            f"sqlite:///{DEFAULT_DATA_DIR / DEFAULT_DB_FILENAME}",
        ),
        auth_disabled=os.getenv("AUTH_DISABLED", "false").lower() in ("true", "1", "yes"),
        auth_secret_key=os.getenv("AUTH_SECRET_KEY", _default_secret_key()),
        auth_session_max_age=int(os.getenv("AUTH_SESSION_MAX_AGE", "604800")),
        webauthn_rp_id=os.getenv("WEBAUTHN_RP_ID", "localhost"),
        webauthn_rp_name=os.getenv("WEBAUTHN_RP_NAME", "MySimpleTodos"),
        webauthn_origin=os.getenv("WEBAUTHN_ORIGIN", "http://localhost:8080"),
    )