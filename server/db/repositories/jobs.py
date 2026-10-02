"""Job identity and per-session JD numbers."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from db.models import Job, SessionJob, utcnow
from domain.naming import format_jd_number
from utils.fingerprint import build_job_fingerprint


class JobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, job_id: str) -> Optional[Job]:
        return self.db.get(Job, job_id)

    def get_by_fingerprint(self, fingerprint: str) -> Optional[Job]:
        return self.db.query(Job).filter(Job.fingerprint == fingerprint).one_or_none()

    def upsert_discovered(
        self,
        *,
        browse_session_id: str,
        source: str,
        url: str,
        company: str,
        title: str,
        salary: str = "",
        location: str = "",
        full_text: str = "",
        raw_extract: Optional[dict[str, Any]] = None,
        captured_at: Optional[datetime] = None,
    ) -> tuple[Job, bool]:
        fingerprint, canonical = build_job_fingerprint(
            source=source,
            url=url,
            company=company,
            title=title,
            salary=salary,
            location=location,
        )
        seen_at = captured_at or utcnow()
        existing = self.get_by_fingerprint(fingerprint)
        created = existing is None
        if existing is None:
            existing = Job(
                browse_session_id=browse_session_id,
                fingerprint=fingerprint,
                source=source,
                url=url,
                canonical_url=canonical,
                title=title,
                company=company,
                salary_text=salary,
                location_text=location,
                full_text=full_text,
                raw_extract_json=raw_extract,
                content_hash=_hash_text(full_text),
                captured_at=seen_at,
            )
            self.db.add(existing)
            self.db.flush()
        elif full_text and not existing.full_text:
            existing.full_text = full_text
            existing.content_hash = _hash_text(full_text)
            if raw_extract is not None:
                existing.raw_extract_json = raw_extract
            if canonical and not existing.canonical_url:
                existing.canonical_url = canonical
            self.db.flush()

        self._touch_link(browse_session_id, existing.id, seen_at)
        return existing, created

    def assign_jd_numbers(self, browse_session_id: str, eligible_job_ids: list[str]) -> list[SessionJob]:
        links = (
            self.db.query(SessionJob)
            .filter(SessionJob.browse_session_id == browse_session_id)
            .all()
        )
        by_job = {link.job_id: link for link in links}
        used = {link.jd_number for link in links if link.jd_number}
        next_index = 1
        ordered: list[SessionJob] = []
        for job_id in eligible_job_ids:
            link = by_job.get(job_id)
            if link is None:
                raise LookupError(f"job {job_id} is not in session {browse_session_id}")
            if not link.jd_number:
                while True:
                    label = format_jd_number(next_index)
                    next_index += 1
                    if label not in used:
                        used.add(label)
                        link.jd_number = label
                        break
            ordered.append(link)
        self.db.flush()
        return ordered

    def _touch_link(self, browse_session_id: str, job_id: str, seen_at: datetime) -> SessionJob:
        link = (
            self.db.query(SessionJob)
            .filter(
                SessionJob.browse_session_id == browse_session_id,
                SessionJob.job_id == job_id,
            )
            .one_or_none()
        )
        if link is None:
            link = SessionJob(
                browse_session_id=browse_session_id,
                job_id=job_id,
                first_seen_at=seen_at,
                last_seen_at=seen_at,
            )
            self.db.add(link)
        else:
            link.last_seen_at = seen_at
        self.db.flush()
        return link


def _hash_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()
