"""API key generation, verification, listing, and revocation."""

import hashlib
import secrets
from datetime import UTC, datetime

from sqlmodel import Session, col, func, select

from app.models import APIKey

_KEY_PREFIX = "mst_"
_KEY_BYTES = 32
_MAX_KEYS = 10


def _hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def generate_key(session: Session, name: str) -> tuple[APIKey, str]:
    """Create a new API key. Returns (saved model, plaintext key).

    Raises ValueError if name is empty or limit (10) is reached.
    """
    if not name or not name.strip():
        raise ValueError("API key name must not be empty")

    count = session.exec(select(func.count()).select_from(APIKey)).one()
    if count >= _MAX_KEYS:
        raise ValueError(f"Maximum of {_MAX_KEYS} API keys reached")

    plaintext = _KEY_PREFIX + secrets.token_hex(_KEY_BYTES)
    key_hash = _hash_key(plaintext)
    key_suffix = plaintext[-6:]

    api_key = APIKey(
        name=name.strip(),
        key_hash=key_hash,
        key_suffix=key_suffix,
    )
    session.add(api_key)
    session.commit()
    session.refresh(api_key)
    return api_key, plaintext


def verify_key(session: Session, plaintext_key: str) -> APIKey | None:
    """Look up a key by its hash. Returns the APIKey if valid, else None.

    Updates last_used_at on success.
    """
    candidate_hash = _hash_key(plaintext_key)
    key = session.exec(select(APIKey).where(APIKey.key_hash == candidate_hash)).first()
    if key is None:
        return None
    key.last_used_at = datetime.now(UTC)
    session.add(key)
    session.commit()
    session.refresh(key)
    return key


def list_keys(session: Session) -> list[APIKey]:
    """Return all API keys ordered by created_at desc."""
    return list(session.exec(select(APIKey).order_by(col(APIKey.created_at).desc())).all())


def revoke_key(session: Session, key_id: int) -> bool:
    """Delete an API key by ID. Returns True if deleted, False if not found."""
    key = session.get(APIKey, key_id)
    if key is None:
        return False
    session.delete(key)
    session.commit()
    return True
