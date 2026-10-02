from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app import app
from db.base import Base
from db.session import get_engine, init_db, reset_engine


def test_existing_status_route_still_reports_running(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_AI_DB_PATH", str(tmp_path / "compat.db"))
    reset_engine()
    with TestClient(app) as client:
        status = client.get("/status")
        health = client.get("/health")
        root = client.get("/")
    reset_engine()
    assert status.status_code == 200
    assert status.json()["status"] == "running"
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert health.json()["database"] == "ok"
    assert root.status_code == 200


def test_alembic_schema_matches_models(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_AI_DB_PATH", str(tmp_path / "migrated.db"))
    reset_engine()
    init_db()
    inspector = inspect(get_engine())
    created = set(inspector.get_table_names())
    assert set(Base.metadata.tables) <= created
    assert "alembic_version" in created
    for table_name, table in Base.metadata.tables.items():
        actual = {column["name"] for column in inspector.get_columns(table_name)}
        expected = {column.name for column in table.columns}
        assert actual == expected
    reset_engine()
