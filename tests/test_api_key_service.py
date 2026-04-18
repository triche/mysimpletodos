"""Tests for API key service — generation, verification, listing, revocation."""

from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import inspect
from sqlmodel import Session

from app.db import get_engine, init_db
from app.services.api_key_service import generate_key, list_keys, revoke_key, verify_key


def test_api_key_table_created(sqlite_database_url: str) -> None:
    init_db(sqlite_database_url)
    engine = get_engine(sqlite_database_url)
    inspector = inspect(engine)
    assert "api_keys" in inspector.get_table_names()


def test_generate_key_returns_plaintext_and_model(db_session: Session) -> None:
    api_key, plaintext = generate_key(db_session, "test key")
    assert plaintext.startswith("mst_")
    assert api_key.id is not None
    assert api_key.name == "test key"


def test_generated_key_hash_matches(db_session: Session) -> None:
    api_key, plaintext = generate_key(db_session, "hash test")
    expected_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    assert api_key.key_hash == expected_hash


def test_key_suffix_matches(db_session: Session) -> None:
    api_key, plaintext = generate_key(db_session, "suffix test")
    assert api_key.key_suffix == plaintext[-6:]


def test_verify_valid_key(db_session: Session) -> None:
    _, plaintext = generate_key(db_session, "verify test")
    result = verify_key(db_session, plaintext)
    assert result is not None
    assert result.name == "verify test"


def test_verify_invalid_key(db_session: Session) -> None:
    result = verify_key(db_session, "mst_invalid_key_that_does_not_exist")
    assert result is None


def test_verify_updates_last_used_at(db_session: Session) -> None:
    api_key, plaintext = generate_key(db_session, "last used test")
    assert api_key.last_used_at is None
    result = verify_key(db_session, plaintext)
    assert result is not None
    assert result.last_used_at is not None


def test_list_keys_ordered(db_session: Session) -> None:
    generate_key(db_session, "first")
    generate_key(db_session, "second")
    generate_key(db_session, "third")
    keys = list_keys(db_session)
    assert len(keys) == 3
    # Ordered by created_at desc — most recent first
    assert keys[0].name == "third"
    assert keys[2].name == "first"


def test_revoke_key_deletes(db_session: Session) -> None:
    api_key, plaintext = generate_key(db_session, "revoke test")
    assert revoke_key(db_session, api_key.id) is True
    assert verify_key(db_session, plaintext) is None


def test_revoke_nonexistent_returns_false(db_session: Session) -> None:
    assert revoke_key(db_session, 99999) is False


def test_generate_key_empty_name_raises(db_session: Session) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        generate_key(db_session, "")
    with pytest.raises(ValueError, match="must not be empty"):
        generate_key(db_session, "   ")


def test_generate_key_limit_enforced(db_session: Session) -> None:
    for i in range(10):
        generate_key(db_session, f"key-{i}")
    with pytest.raises(ValueError, match="Maximum"):
        generate_key(db_session, "one too many")
