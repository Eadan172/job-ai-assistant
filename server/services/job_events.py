"""Normalize a discovered job and store it once per fingerprint."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from db.models import BrowseSession, JobEvent, utcnow
from db.repositories.jobs import JobRepository
from db.repositories.sessions import BrowseSessionRepository, UserRepository
from domain.events import JobEventIn, RawJob
from domain.schemas import ExperienceRange, JobJD, Location, Salary
from utils.fingerprint import build_job_fingerprint

MIN_BODY_LENGTH = 40


class IncompleteJobError(ValueError):
    """The page did not contain a usable job description."""


class JobEventService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.sessions = BrowseSessionRepository(db)
        self.jobs = JobRepository(db)

    def handle(self, event: JobEventIn) -> dict:
        existing = self.db.get(JobEvent, event.event_id)
        if existing is not None:
            return _result(existing, duplicate_event=True, created=False)

        if event.event_type == "job.extraction_failed":
            row = JobEvent(
                id=event.event_id,
                event_type=event.event_type,
                url=event.url,
                status="failed",
                error_class="EXTRACTION_FAILED",
                created_at=_as_utc(event.captured_at),
            )
            self.db.add(row)
            self.db.flush()
            return _result(row, duplicate_event=False, created=False)

        if event.event_type != "job.discovered":
            raise IncompleteJobError(f"unsupported event type: {event.event_type}")
        raw = _require_complete(event.raw_job)
        browse = self._resolve_session(event.session_id)
        captured_at = _as_utc(event.captured_at)
        fingerprint, canonical = build_job_fingerprint(
            source=event.source,
            url=event.url,
            company=raw.company,
            title=raw.title,
            salary=raw.salary,
            location=raw.location,
        )
        job, created = self.jobs.upsert_discovered(
            browse_session_id=browse.id,
            source=event.source,
            url=event.url,
            company=raw.company,
            title=raw.title,
            salary=raw.salary,
            location=raw.location,
            full_text=raw.full_text,
            raw_extract=raw.model_dump(),
            captured_at=captured_at,
        )
        if not job.structured_json:
            normalized_at = utcnow()
            jd = JobJD(
                id=job.id,
                source=event.source,
                url=event.url,
                canonical_url=canonical,
                title=raw.title,
                company=raw.company,
                salary=Salary(raw=raw.salary),
                location=Location(raw=raw.location),
                responsibilities=raw.responsibilities,
                required_skills=raw.required_skills,
                preferred_skills=raw.preferred_skills,
                experience_years=ExperienceRange(raw=raw.experience_years) if raw.experience_years else None,
                education=raw.education,
                benefits=raw.benefits,
                full_text=raw.full_text,
                source_spans={
                    "responsibilities": list(raw.responsibilities),
                    "required_skills": list(raw.required_skills),
                    "preferred_skills": list(raw.preferred_skills),
                    "experience_years": [raw.experience_years] if raw.experience_years else [],
                    "education": list(raw.education),
                    "benefits": list(raw.benefits),
                },
                captured_at=captured_at,
                normalized_at=normalized_at,
            )
            job.structured_json = jd.model_dump(mode="json")
            job.source_spans = jd.source_spans
            job.normalized_at = normalized_at
            if canonical:
                job.canonical_url = canonical
        row = JobEvent(
            id=event.event_id,
            event_type=event.event_type,
            fingerprint=fingerprint,
            job_id=job.id,
            browse_session_id=browse.id,
            url=event.url,
            status="accepted",
            created_at=captured_at,
        )
        self.db.add(row)
        self.db.flush()
        payload = _result(row, duplicate_event=False, created=created)
        payload["session_origin"] = browse.origin
        return payload

    def _resolve_session(self, session_id: Optional[str]) -> BrowseSession:
        if session_id:
            row = self.sessions.get(session_id)
            if row is None:
                raise LookupError(f"browse session {session_id} not found")
            if row.status == "IDLE":
                row = self.sessions.transition(row.id, "ACTIVE")
            if row.status == "ACTIVE":
                return row
        active = self.sessions.latest_active()
        if active is not None:
            return active
        user = self.users.get_or_create_local_user()
        created = self.sessions.create(user_id=user.id, origin="extension_auto")
        return self.sessions.transition(created.id, "ACTIVE")


def _require_complete(raw: Optional[RawJob]) -> RawJob:
    if raw is None or not raw.title.strip() or not raw.company.strip():
        raise IncompleteJobError("title and company are required")
    if len(raw.full_text.strip()) < MIN_BODY_LENGTH:
        raise IncompleteJobError("job body is incomplete")
    return raw


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _result(row: JobEvent, *, duplicate_event: bool, created: bool) -> dict:
    return {
        "event_id": row.id,
        "event_type": row.event_type,
        "duplicate_event": duplicate_event,
        "created": created,
        "job_id": row.job_id,
        "session_id": row.browse_session_id,
        "fingerprint": row.fingerprint,
        "status": row.status,
    }
