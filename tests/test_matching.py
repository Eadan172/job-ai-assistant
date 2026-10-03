import threading
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from agents.matcher import MatchAgent
from app import app
from db.models import Job, JobMatch
from db.repositories.jobs import JobRepository
from db.repositories.resumes import ResumeRepository
from db.repositories.sessions import UserRepository
from db.session import get_engine, reset_engine
from domain.preferences import SCORING_VERSION, default_preferences
from domain.schemas import (
    EducationRecord,
    ExperienceRange,
    JobJD,
    Location,
    MatchExplanation,
    ProjectExperience,
    ResumeProfile,
    ResumeSkill,
    Salary,
    WorkExperience,
)
from llm.gateway import LLMGateway, StructuredOutputError, unwrap_json_document
from services.event_hub import hub
from services.match_queue import configure_clients
from services.matching import MatchService
from utils.resume_parser import parse_resume

NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)
DETAIL = "https://www.zhipin.com/job_detail/abc123.html"


class ScriptedClient:
    model_version = "scripted"

    def __init__(self, profile: ResumeProfile, fail: str = "") -> None:
        self.profile = profile
        self.fail = fail
        self.profile_calls = 0
        self.explain_calls = 0

    def complete(self, schema, *, system: str, user: str):
        if schema is ResumeProfile:
            self.profile_calls += 1
            if self.fail == "timeout":
                raise TimeoutError("timeout")
            if self.fail == "invalid":
                raise StructuredOutputError("structured output did not match the schema")
            if self.fail == "unavailable":
                raise ConnectionError("provider unavailable")
            return self.profile
        if schema is MatchExplanation:
            self.explain_calls += 1
            if self.fail == "explanation":
                raise TimeoutError("timeout")
            return MatchExplanation(explanation="Python 与 FastAPI 有项目证据。Kubernetes 没有证据。")
        raise AssertionError(schema)


def _profile() -> ResumeProfile:
    return ResumeProfile(
        summary="Python 后端工程师",
        skills=[
            ResumeSkill(
                name="Python",
                evidence=["负责订单服务后端 API 开发，使用 Python 与 FastAPI"],
                source_span="使用 Python 与 FastAPI",
            ),
            ResumeSkill(name="FastAPI", evidence=["使用 Python 与 FastAPI"], source_span="使用 Python 与 FastAPI"),
        ],
        work_experiences=[
            WorkExperience(
                company="示例公司",
                title="后端工程师",
                description="负责订单服务后端 API 开发，使用 Python 与 FastAPI",
                source_span="负责订单服务后端 API 开发，使用 Python 与 FastAPI",
            )
        ],
        projects=[ProjectExperience(name="Agent 工作流", description="使用 Python 搭建内部 Agent 工作流")],
        education=[EducationRecord(school="示例大学", degree="本科")],
        years_of_experience=5,
    )


def _job(**overrides) -> JobJD:
    payload = dict(
        id="job-1",
        source="boss",
        url=DETAIL,
        title="Python 工程师",
        company="示例公司",
        salary=Salary(raw="25-35K"),
        location=Location(raw="上海", city="上海"),
        responsibilities=["负责后端 API 开发"],
        required_skills=["Python", "FastAPI", "Kubernetes"],
        preferred_skills=["Docker"],
        experience_years=ExperienceRange(raw="3年以上"),
        education=["本科"],
        full_text="负责后端 API 开发。熟悉 Python 与 FastAPI。本科。3年以上。",
        captured_at=NOW,
        normalized_at=NOW,
    )
    payload.update(overrides)
    return JobJD(**payload)


def _use_db(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_AI_DB_PATH", str(tmp_path / "match.db"))
    monkeypatch.setenv("JOB_AI_MATCH_DISABLED", "0")
    monkeypatch.setenv("JOB_AI_MATCH_INLINE", "1")
    reset_engine()


def _event(event_id: str = "event-a") -> dict:
    return {
        "event_id": event_id,
        "event_type": "job.discovered",
        "source": "boss",
        "url": DETAIL,
        "captured_at": "2026-10-03T10:00:00Z",
        "raw_job": {
            "title": "Python 工程师",
            "company": "示例公司",
            "salary": "25-35K",
            "location": "上海",
            "responsibilities": ["负责后端 API 开发"],
            "required_skills": ["Python", "FastAPI", "Kubernetes"],
            "preferred_skills": ["Docker"],
            "experience_years": "3年以上",
            "education": ["本科"],
            "benefits": [],
            "full_text": (
                "负责后端 API 开发，参与需求分析、设计和上线维护，并保证接口稳定可用。"
                "熟悉 Python 与 FastAPI。"
            ),
        },
    }


def test_gateway_accepts_a_json_document_and_rejects_free_text():
    profile = ResumeProfile.model_validate_json(unwrap_json_document('```json\n{"skills":[]}\n```'))
    assert profile.skills == []
    with pytest.raises(ValidationError):
        ResumeProfile.model_validate_json(unwrap_json_document("请看下面的分析，不是 JSON"))
    with pytest.raises(StructuredOutputError):
        LLMGateway("deepseek", "").structured(ResumeProfile, system="x", user="y")


def test_resume_files_become_a_profile(tmp_path):
    text = "Python 后端工程师，本科，使用 FastAPI 开发订单 API。"
    txt = tmp_path / "resume.txt"
    txt.write_text(text, encoding="utf-8")
    docx = tmp_path / "resume.docx"
    from docx import Document

    document = Document()
    document.add_paragraph(text)
    document.save(docx)
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(_tiny_pdf("Python FastAPI engineer"))
    client = ScriptedClient(_profile())
    from agents.resume_profile import ResumeProfileAgent

    agent = ResumeProfileAgent(client)
    for path in (txt, docx, pdf):
        plain = parse_resume(str(path))
        assert plain.strip()
        built = agent.extract(plain)
        assert built.skills[0].name == "Python"
        assert built.skills[0].evidence
    assert client.profile_calls == 3


def test_hybrid_score_names_matches_and_gaps():
    result = MatchAgent().score(_job(), _profile(), default_preferences(), scoring_version=SCORING_VERSION)
    assert "Python" in result.matched_skills
    assert "FastAPI" in result.matched_skills
    assert result.missing_required_skills == ["Kubernetes"]
    assert any(gap.name == "Docker" and gap.status == "MISSING_PREFERRED" for gap in result.skill_gaps)
    assert set(result.dimension_scores) == {
        "skills",
        "responsibilities",
        "experience",
        "education",
        "location",
        "salary",
        "other",
    }
    assert result.evidence_links
    assert result.evidence_from_resume
    assert result.explanation is None
    assert 0 <= result.overall_score <= 100
    assert result.scoring_version == SCORING_VERSION


def test_hard_constraints_are_explicit():
    agent = MatchAgent()
    profile = _profile()
    base = default_preferences()
    fit = agent.score(_job(), profile, {**base, "locations": ["上海"], "min_salary_k": 20}, scoring_version="hybrid-v1")
    assert fit.hard_constraint_passed is True
    place = agent.score(
        _job(location=Location(raw="北京", city="北京")),
        profile,
        {**base, "locations": ["上海"]},
        scoring_version="hybrid-v1",
    )
    assert any(flag.type == "LOCATION_MISMATCH" and flag.severity == "high" for flag in place.risk_flags)
    pay = agent.score(
        _job(salary=Salary(raw="15K")),
        profile,
        {**base, "min_salary_k": 25},
        scoring_version="hybrid-v1",
    )
    assert any(flag.type == "SALARY_BELOW_EXPECTATION" for flag in pay.risk_flags)
    school = agent.score(_job(education=["硕士"]), profile, base, scoring_version="hybrid-v1")
    assert any(flag.type == "EDUCATION_BELOW_REQUIREMENT" for flag in school.risk_flags)
    degree_ok = agent.score(_job(education=["本科"]), profile, base, scoring_version="hybrid-v1")
    assert all(flag.type != "EDUCATION_BELOW_REQUIREMENT" for flag in degree_ok.risk_flags)
    short = _profile()
    short.years_of_experience = 3
    junior = agent.score(
        _job(experience_years=ExperienceRange(raw="5年以上")),
        short,
        base,
        scoring_version="hybrid-v1",
    )
    assert any(flag.type == "EXPERIENCE_BELOW_REQUIREMENT" for flag in junior.risk_flags)
    assert junior.overall_score < fit.overall_score


def test_same_inputs_reuse_one_match_and_one_profile(db: Session):
    user = UserRepository(db).get_or_create_local_user()
    resume = ResumeRepository(db).create_original(user_id=user.id, filename="a.txt", content_text="Python FastAPI")
    UserRepository(db).set_active_resume(user.id, resume.id)
    job, _ = JobRepository(db).upsert_discovered(
        browse_session_id=_session(db, user.id),
        source="boss",
        url=DETAIL,
        company="示例公司",
        title="Python 工程师",
        full_text="负责后端 API 开发，并保证服务稳定可用超过四十个字。",
    )
    client = ScriptedClient(_profile())
    service = MatchService(db, profile_client=client, explanation_client=client)
    first = service.run(job.id)
    second = service.run(job.id)
    db.commit()
    assert first["match_id"] == second["match_id"]
    assert client.profile_calls == 1
    assert client.explain_calls == 1
    assert db.query(JobMatch).filter(JobMatch.status == "COMPLETED").count() == 1


def test_new_resume_and_new_preferences_keep_the_old_match(db: Session):
    user = UserRepository(db).get_or_create_local_user()
    session_id = _session(db, user.id)
    first_resume = ResumeRepository(db).create_original(
        user_id=user.id,
        filename="a.txt",
        content_text="第一份简历 Python",
    )
    job, _ = JobRepository(db).upsert_discovered(
        browse_session_id=session_id,
        source="boss",
        url=DETAIL,
        company="示例公司",
        title="Python 工程师",
        full_text="负责后端 API 开发，并保证服务稳定可用超过四十个字。",
    )
    client = ScriptedClient(_profile())
    service = MatchService(db, profile_client=client, explanation_client=client)
    original = service.run(job.id, resume_version_id=first_resume.id)
    second_resume = ResumeRepository(db).create_original(
        user_id=user.id,
        filename="b.txt",
        content_text="第二份简历 Python FastAPI",
    )
    revised = service.run(job.id, resume_version_id=second_resume.id)
    UserRepository(db).update_preferences(user.id, {"locations": ["上海"], "min_salary_k": 20})
    moved = service.run(job.id, resume_version_id=second_resume.id)
    db.commit()
    rows = db.query(JobMatch).filter(JobMatch.status == "COMPLETED").all()
    assert len(rows) == 3
    assert {original["match_id"], revised["match_id"], moved["match_id"]} == {row.id for row in rows}
    assert db.get(JobMatch, original["match_id"]).overall_score == original["score"]


def test_parallel_runs_create_one_completed_match():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from db.base import Base

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    seed = factory()
    user = UserRepository(seed).get_or_create_local_user()
    resume = ResumeRepository(seed).create_original(user_id=user.id, filename="a.txt", content_text="Python")
    UserRepository(seed).set_active_resume(user.id, resume.id)
    session_id = _session(seed, user.id)
    job, _ = JobRepository(seed).upsert_discovered(
        browse_session_id=session_id,
        source="boss",
        url=DETAIL,
        company="示例公司",
        title="Python 工程师",
        full_text="负责后端 API 开发，并保证服务稳定可用超过四十个字。",
    )
    seed.commit()
    client = ScriptedClient(_profile())
    original = client.complete

    def slow_complete(schema, *, system: str, user: str):
        if schema is ResumeProfile:
            threading.Event().wait(0.05)
        return original(schema, system=system, user=user)

    client.complete = slow_complete
    errors = []

    def work():
        session = factory()
        try:
            MatchService(session, profile_client=client, explanation_client=client).run(job.id)
            session.commit()
        except Exception as exc:
            errors.append(exc)
            session.rollback()
        finally:
            session.close()

    threads = [threading.Thread(target=work), threading.Thread(target=work)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    check = factory()
    completed = check.query(JobMatch).filter(JobMatch.status == "COMPLETED").count()
    check.close()
    engine.dispose()
    assert errors == []
    assert completed == 1
    assert client.profile_calls == 1


def test_missing_resume_has_no_fake_score(db: Session):
    user = UserRepository(db).get_or_create_local_user()
    job, _ = JobRepository(db).upsert_discovered(
        browse_session_id=_session(db, user.id),
        source="boss",
        url=DETAIL,
        company="示例公司",
        title="Python 工程师",
        full_text="负责后端 API 开发，并保证服务稳定可用超过四十个字。",
    )
    outcome = MatchService(db).run(job.id)
    db.commit()
    assert outcome["status"] == "RESUME_NOT_CONFIGURED"
    assert outcome["score"] is None
    assert db.get(JobMatch, outcome["match_id"]).overall_score is None


def test_profile_and_explanation_failures_keep_the_job(db: Session):
    user = UserRepository(db).get_or_create_local_user()
    resume = ResumeRepository(db).create_original(
        user_id=user.id,
        filename="a.txt",
        content_text="Python FastAPI 简历正文",
    )
    UserRepository(db).set_active_resume(user.id, resume.id)
    session_id = _session(db, user.id)
    job, _ = JobRepository(db).upsert_discovered(
        browse_session_id=session_id,
        source="boss",
        url=DETAIL,
        company="示例公司",
        title="Python 工程师",
        full_text="负责后端 API 开发，并保证服务稳定可用超过四十个字。",
    )
    failed = ScriptedClient(_profile(), fail="timeout")
    outcome = MatchService(db, profile_client=failed, explanation_client=failed).run(job.id)
    db.commit()
    assert db.get(Job, job.id) is not None
    assert outcome["status"] == "FAILED"
    assert outcome["score"] is None
    explained = ScriptedClient(_profile(), fail="explanation")
    recovered = MatchService(db, profile_client=explained, explanation_client=explained).run(job.id)
    db.commit()
    row = db.get(JobMatch, recovered["match_id"])
    assert row.status == "COMPLETED"
    assert row.overall_score is not None
    assert row.explanation is None
    assert row.explanation_status == "FAILED"
    assert db.query(Job).count() == 1


def test_event_queues_match_and_refresh_stays_idempotent(tmp_path, monkeypatch):
    _use_db(tmp_path, monkeypatch)
    client = ScriptedClient(_profile())
    configure_clients(client, client)
    before = hub.since(0)[-1]["seq"] if hub.since(0) else 0
    with TestClient(app) as api:
        saved = api.post(
            "/api/resumes",
            json={"filename": "resume.txt", "content_text": "Python FastAPI 后端简历，本科。"},
        )
        first = api.post("/api/jobs/events", json=_event("event-a"))
        second = api.post("/api/jobs/events", json=_event("event-a"))
        job_id = first.json()["data"]["job_id"]
        match = api.get(f"/api/jobs/{job_id}/match")
        session_id = first.json()["data"]["session_id"]
        listing = api.get(f"/api/browse-sessions/{session_id}/jobs")
        forced = api.post(f"/api/jobs/{job_id}/match", json={"force": True, "scoring_version": SCORING_VERSION})
        again = api.get(f"/api/jobs/{job_id}/match")
        status = api.get("/status")
    reset_engine()
    configure_clients(None, None)
    assert saved.status_code == 200
    assert first.status_code == 200
    assert second.json()["data"]["duplicate_event"] is True
    assert match.status_code == 200
    body = match.json()["data"]
    assert body["status"] == "COMPLETED"
    assert body["overall_score"] is not None
    assert body["matched_skills"]
    assert "Kubernetes" in body["missing_required_skills"]
    assert body["evidence_from_resume"]
    assert body["risk_flags"] is not None
    assert body["explanation"]
    assert listing.json()["data"]["jobs"][0]["match"]["status"] == "COMPLETED"
    assert forced.json()["data"]["match_id"] != match.json()["data"]["match_id"]
    assert again.json()["data"]["status"] == "COMPLETED"
    assert status.json()["status"] == "running"
    kinds = {item["type"] for item in hub.since(before)}
    assert {"JOB_SAVED", "MATCH_QUEUED", "MATCH_COMPLETED"} <= kinds
    assert client.profile_calls == 1


def test_match_failure_does_not_drop_the_saved_job(tmp_path, monkeypatch):
    _use_db(tmp_path, monkeypatch)
    configure_clients(ScriptedClient(_profile(), fail="unavailable"), ScriptedClient(_profile(), fail="unavailable"))
    with TestClient(app) as api:
        api.post("/api/resumes", json={"filename": "resume.txt", "content_text": "Python FastAPI 后端简历正文足够长。"})
        response = api.post("/api/jobs/events", json=_event("event-fail"))
        job_id = response.json()["data"]["job_id"]
        match = api.get(f"/api/jobs/{job_id}/match")
    with Session(get_engine()) as db:
        assert db.query(Job).count() == 1
    reset_engine()
    configure_clients(None, None)
    assert response.status_code == 200
    assert match.json()["data"]["status"] == "FAILED"
    assert match.json()["data"]["overall_score"] is None


def test_websocket_receives_a_match_event(tmp_path, monkeypatch):
    _use_db(tmp_path, monkeypatch)
    published = hub.publish({"type": "MATCH_COMPLETED", "job_id": "demo", "status": "COMPLETED", "overall_score": 83})
    with TestClient(app) as api:
        with api.websocket_connect("/api/events") as socket:
            seen = None
            for _ in range(200):
                item = socket.receive_json()
                if item["seq"] == published["seq"]:
                    seen = item
                    break
    reset_engine()
    assert seen is not None
    assert seen["type"] == "MATCH_COMPLETED"
    assert seen["overall_score"] == 83


def _session(db: Session, user_id: str) -> str:
    from db.repositories.sessions import BrowseSessionRepository

    row = BrowseSessionRepository(db).create(user_id=user_id, origin="test")
    return BrowseSessionRepository(db).transition(row.id, "ACTIVE").id


def _tiny_pdf(text: str) -> bytes:
    stream = f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n",
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n",
        (
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
            b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        ),
        b"4 0 obj<</Length " + str(len(stream)).encode("ascii") + b">>stream\n" + stream + b"\nendstream\nendobj\n",
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n",
    ]
    payload = b"%PDF-1.4\n"
    offsets = [0]
    for item in objects:
        offsets.append(len(payload))
        payload += item
    xref = len(payload)
    payload += f"xref\n0 {len(offsets)}\n".encode("ascii")
    payload += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        payload += f"{offset:010d} 00000 n \n".encode("ascii")
    payload += f"trailer<</Size {len(offsets)}/Root 1 0 R>>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    return payload
