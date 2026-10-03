"""Shared fixtures. Each test gets its own in-memory database."""

from __future__ import annotations

from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import db.models  # noqa: F401
import db.session  # noqa: F401
from db.base import Base


@pytest.fixture(autouse=True)
def _keep_match_off_unless_a_test_opts_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JOB_AI_MATCH_DISABLED", "1")
    from services.match_queue import configure_clients

    configure_clients(None, None)


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
