from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import app
from db.models import BrowseSession, Job, JobEvent, SessionJob
from db.session import get_engine, reset_engine

DETAIL = "https://www.zhipin.com/job_detail/abc123.html"
BODY = "负责 Python 后端接口开发，参与需求分析、设计和上线维护，并保证接口稳定可用。"


def _payload(event_id, url=DETAIL):
    return {
        "event_id": event_id,
        "event_type": "job.discovered",
        "source": "boss",
        "url": url,
        "captured_at": "2026-10-02T10:00:00Z",
        "raw_job": {
            "title": "Python 工程师",
            "company": "示例公司",
            "salary": "25-35K",
            "location": "上海",
            "responsibilities": ["负责 Python 后端接口开发"],
            "required_skills": ["Python"],
            "preferred_skills": [],
            "experience_years": "3年以上工作经验",
            "education": ["本科"],
            "benefits": ["五险一金"],
            "full_text": BODY,
        },
    }


def _use_db(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_AI_DB_PATH", str(tmp_path / "events.db"))
    reset_engine()


def _counts():
    with Session(get_engine()) as db:
        return {
            "jobs": db.query(Job).count(),
            "links": db.query(SessionJob).count(),
            "events": db.query(JobEvent).count(),
            "sessions": db.query(BrowseSession).count(),
            "origin": db.query(BrowseSession).one().origin if db.query(BrowseSession).count() else None,
        }


def test_repeated_event_and_url_variants_create_one_job(tmp_path, monkeypatch):
    _use_db(tmp_path, monkeypatch)
    with TestClient(app) as client:
        first = client.post("/api/jobs/events", json=_payload("event-a"))
        second = client.post("/api/jobs/events", json=_payload("event-a"))
        third = client.post("/api/jobs/events", json=_payload("event-a"))
        refreshed = client.post(
            "/api/jobs/events",
            json=_payload("event-b", "http://www.zhipin.com/job_detail/abc123.html?ka=1"),
        )
        assert first.status_code == 200
        assert first.json()["data"]["created"] is True
        assert first.json()["data"]["duplicate_event"] is False
        assert second.json()["data"]["duplicate_event"] is True
        assert third.json()["data"]["duplicate_event"] is True
        assert refreshed.json()["data"]["created"] is False
        assert first.json()["data"]["fingerprint"] == refreshed.json()["data"]["fingerprint"]
        assert first.json()["data"]["job_id"] == refreshed.json()["data"]["job_id"]
    counts = _counts()
    assert counts == {
        "jobs": 1,
        "links": 1,
        "events": 2,
        "sessions": 1,
        "origin": "extension_auto",
    }
    reset_engine()


def test_incomplete_page_does_not_create_a_job(tmp_path, monkeypatch):
    _use_db(tmp_path, monkeypatch)
    payload = _payload("short")
    payload["raw_job"]["full_text"] = "太短"
    with TestClient(app) as client:
        response = client.post("/api/jobs/events", json=payload)
        failed = client.post(
            "/api/jobs/events",
            json={
                "event_id": "failed-1",
                "event_type": "job.extraction_failed",
                "source": "boss",
                "url": DETAIL,
                "captured_at": "2026-10-02T10:00:00Z",
            },
        )
        missing = client.post("/api/jobs/events", json=_payload("missing", DETAIL) | {"session_id": "missing"})
    assert response.status_code == 422
    assert failed.status_code == 200
    assert missing.status_code == 404
    with Session(get_engine()) as db:
        assert db.query(Job).count() == 0
        assert db.query(JobEvent).count() == 1
    reset_engine()


def test_legacy_routes_remain_available(tmp_path, monkeypatch):
    _use_db(tmp_path, monkeypatch)
    with TestClient(app) as client:
        paths = client.get("/openapi.json").json()["paths"]
        status = client.get("/status")
    for path in [
        "/status",
        "/parse-resume",
        "/analyze-resume",
        "/optimize-resume",
        "/analyze-jobs",
        "/chat",
        "/test-connection",
    ]:
        assert path in paths
    assert status.json()["status"] == "running"
    reset_engine()
