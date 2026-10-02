"""Engine and Alembic startup.

The database file defaults to ``data/job_ai.db`` under the repository root.
Tests set ``JOB_AI_DB_PATH`` before calling :func:`init_db`.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import db.models  # noqa: F401  # register tables on Base.metadata
from db.base import Base

logger = logging.getLogger("job_ai.db")

_engine: Engine | None = None
_engine_url: str | None = None
_session_factory: sessionmaker[Session] | None = None

SERVER_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVER_DIR.parent
ALEMBIC_INI = SERVER_DIR / "alembic.ini"
MIGRATIONS_DIR = SERVER_DIR / "db" / "migrations"


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def database_path() -> Path:
    override = os.environ.get("JOB_AI_DB_PATH")
    if override:
        return Path(override)
    return PROJECT_ROOT / "data" / "job_ai.db"


def get_database_url() -> str:
    return "sqlite:///" + database_path().as_posix()


def reset_engine() -> None:
    global _engine, _engine_url, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_url = None
    _session_factory = None


def get_engine() -> Engine:
    global _engine, _engine_url, _session_factory
    url = get_database_url()
    if _engine is None or _engine_url != url:
        if _engine is not None:
            _engine.dispose()
        _engine = create_engine(url, connect_args={"check_same_thread": False})
        _engine_url = url
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("opening sqlite path=%s", path)
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", get_database_url())
    command.upgrade(cfg, "head")
    get_engine()


def check_db() -> bool:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("sqlite health check failed")
        return False


def create_all(engine: Engine | None = None) -> None:
    """Create tables from metadata. Tests use this; runtime uses Alembic."""
    Base.metadata.create_all(engine or get_engine())
