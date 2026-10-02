from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from db.errors import InvalidTransition
from db.models import Job, ResumeVersion, SessionJob
from db.repositories.jobs import JobRepository
from db.repositories.matches import JobMatchRepository
from db.repositories.resumes import ResumeRepository
from db.repositories.sessions import BrowseSessionRepository, UserRepository
from domain.preferences import SCORING_VERSION

DETAIL = "https://www.zhipin.com/job_detail/abc123.html?ka=search"
WHEN = datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc)


def _open_session(db):
    user = UserRepository(db).get_or_create_local_user()
    browse = BrowseSessionRepository(db).create(user_id=user.id, when=WHEN)
    BrowseSessionRepository(db).transition(browse.id, "ACTIVE")
    return user, browse


def test_duplicate_detail_page_stays_one_job(db):
    _, browse = _open_session(db)
    jobs = JobRepository(db)
    first, created_first = jobs.upsert_discovered(
        browse_session_id=browse.id,
        source="Boss直聘",
        url=DETAIL,
        company="示例公司",
        title="Python 工程师",
        salary="25-35K",
        location="上海",
    )
    second, created_second = jobs.upsert_discovered(
        browse_session_id=browse.id,
        source="Boss直聘",
        url="http://www.zhipin.com/job_detail/abc123.html",
        company="示例公司",
        title="Python 工程师",
        full_text="负责后端开发",
    )
    db.commit()
    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    assert second.full_text == "负责后端开发"
    assert db.query(Job).count() == 1
    assert db.query(SessionJob).count() == 1


def test_same_job_can_belong_to_two_sessions(db):
    user = UserRepository(db).get_or_create_local_user()
    sessions = BrowseSessionRepository(db)
    first = sessions.create(user_id=user.id, when=WHEN)
    second = sessions.create(user_id=user.id, when=WHEN)
    jobs = JobRepository(db)
    payload = dict(source="Boss直聘", url=DETAIL, company="示例公司", title="Python 工程师")
    jobs.upsert_discovered(browse_session_id=first.id, **payload)
    jobs.upsert_discovered(browse_session_id=second.id, **payload)
    db.commit()
    assert db.query(Job).count() == 1
    assert db.query(SessionJob).count() == 2
    assert first.label == "20261002-001"
    assert second.label == "20261002-002"


def test_jd_numbers_stay_stable(db):
    _, browse = _open_session(db)
    jobs = JobRepository(db)
    created = []
    for index in range(3):
        job, _ = jobs.upsert_discovered(
            browse_session_id=browse.id,
            source="拉勾网",
            url=f"https://www.lagou.com/wn/jobs/1000{index}.html",
            company="示例公司",
            title=f"工程师 {index}",
        )
        created.append(job.id)
    first_pass = jobs.assign_jd_numbers(browse.id, created[:2])
    again = jobs.assign_jd_numbers(browse.id, created[:2])
    with_new = jobs.assign_jd_numbers(browse.id, created)
    db.commit()
    assert [link.jd_number for link in first_pass] == ["JD-no.01", "JD-no.02"]
    assert [link.jd_number for link in again] == ["JD-no.01", "JD-no.02"]
    assert [link.jd_number for link in with_new] == ["JD-no.01", "JD-no.02", "JD-no.03"]


def test_session_transitions(db):
    user = UserRepository(db).get_or_create_local_user()
    sessions = BrowseSessionRepository(db)
    browse = sessions.create(user_id=user.id, when=WHEN)
    with pytest.raises(InvalidTransition):
        sessions.transition(browse.id, "COMPLETED")
    sessions.transition(browse.id, "ACTIVE")
    sessions.transition(browse.id, "FINALIZING")
    sessions.transition(browse.id, "FAILED", error_class="ExportError")
    recovered = sessions.transition(browse.id, "ACTIVE")
    assert recovered.status == "ACTIVE"
    sessions.transition(recovered.id, "FINALIZING")
    finished = sessions.transition(recovered.id, "COMPLETED")
    db.commit()
    assert finished.status == "COMPLETED"
    assert finished.finalized_at is not None
    with pytest.raises(InvalidTransition):
        sessions.transition(finished.id, "ACTIVE")


def test_tailored_resume_does_not_change_original(db):
    user, browse = _open_session(db)
    job, _ = JobRepository(db).upsert_discovered(
        browse_session_id=browse.id,
        source="Boss直聘",
        url=DETAIL,
        company="示例公司",
        title="Python 工程师",
    )
    resumes = ResumeRepository(db)
    original = resumes.create_original(user_id=user.id, filename="resume.txt", content_text="原始经历：Python 后端")
    original_hash = original.content_hash
    tailored = resumes.create_tailored(parent_id=original.id, job_id=job.id, content_text="重排后的 Python 后端经历")
    with pytest.raises(ValueError):
        resumes.create_original(user_id=user.id, filename="empty.txt", content_text="  ")
    db.commit()
    stored = db.get(ResumeVersion, original.id)
    assert stored.content_text == "原始经历：Python 后端"
    assert stored.content_hash == original_hash
    assert tailored.kind == "tailored"
    assert tailored.version == 2
    assert tailored.content_text != stored.content_text


def test_match_keeps_the_first_score_for_a_version(db):
    user, browse = _open_session(db)
    job, _ = JobRepository(db).upsert_discovered(
        browse_session_id=browse.id,
        source="Boss直聘",
        url=DETAIL,
        company="示例公司",
        title="Python 工程师",
    )
    resume = ResumeRepository(db).create_original(
        user_id=user.id,
        filename="resume.txt",
        content_text="Python 后端",
    )
    matches = JobMatchRepository(db)
    payload = dict(
        job_id=job.id,
        resume_version_id=resume.id,
        scoring_version=SCORING_VERSION,
        dimension_scores={"skills": 80},
        matched_skills=["Python"],
        missing_required_skills=[],
        evidence_from_resume=["Python 后端"],
        risk_flags=[],
        explanation="技能有对应经历",
        model_version="deterministic",
        browse_session_id=browse.id,
    )
    first, created_first = matches.save(overall_score=80, **payload)
    second, created_second = matches.save(overall_score=10, **payload)
    db.commit()
    assert created_first is True
    assert created_second is False
    assert second.id == first.id
    assert second.overall_score == 80


def test_missing_session_is_rejected(db):
    with pytest.raises(IntegrityError):
        JobRepository(db).upsert_discovered(
            browse_session_id="missing-session",
            source="Boss直聘",
            url=DETAIL,
            company="示例公司",
            title="Python 工程师",
        )
