"""Load the active resume, score one job, and store the attempt.

Job persistence is not part of this service. Callers commit the job first.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Optional

from sqlalchemy.orm import Session

from agents.matcher import MatchAgent
from agents.resume_profile import ResumeProfileAgent, StructuredClient
from db.models import Job, JobMatch, ResumeVersion
from db.repositories.jobs import JobRepository
from db.repositories.matches import JobMatchRepository
from db.repositories.resumes import ResumeRepository
from db.repositories.sessions import BrowseSessionRepository, UserRepository
from domain.preferences import SCORING_VERSION, default_preferences, preferences_hash
from domain.schemas import ExperienceRange, JobJD, Location, MatchExplanation, MatchResult, ResumeProfile, Salary
from llm.embeddings import HashEmbeddingProvider
from llm.gateway import LLMGateway

EXPLAIN_SYSTEM = (
    "Explain why the match looks like the supplied JSON. "
    "The scores are already final. Do not propose different scores. "
    'Return {"explanation": "..."} only. '
    "Cover matched skills, missing skills, and the strongest resume evidence."
)

_LOCKS: dict[str, threading.RLock] = {}
_LOCK_GUARD = threading.Lock()


class ProfileUnavailable(RuntimeError):
    """The resume text could not be structured."""


def key_lock(name: str) -> threading.RLock:
    with _LOCK_GUARD:
        lock = _LOCKS.get(name)
        if lock is None:
            lock = threading.RLock()
            _LOCKS[name] = lock
        return lock


class MatchService:
    def __init__(
        self,
        db: Session,
        *,
        profile_client: Optional[StructuredClient] = None,
        explanation_client: Optional[StructuredClient] = None,
        embedder: Optional[HashEmbeddingProvider] = None,
    ) -> None:
        self.db = db
        self.profile_client = profile_client
        self.explanation_client = explanation_client
        self.jobs = JobRepository(db)
        self.matches = JobMatchRepository(db)
        self.resumes = ResumeRepository(db)
        self.sessions = BrowseSessionRepository(db)
        self.users = UserRepository(db)
        self.agent = MatchAgent(embedder)

    def run(
        self,
        job_id: str,
        *,
        browse_session_id: Optional[str] = None,
        resume_version_id: Optional[str] = None,
        scoring_version: Optional[str] = None,
        force: bool = False,
    ) -> dict[str, Any]:
        job = self.jobs.get(job_id)
        if job is None:
            raise LookupError(f"job {job_id} not found")
        resume_id = self._resolve_resume(browse_session_id, resume_version_id)
        if resume_id is None:
            return self._unconfigured(job, browse_session_id)
        version = scoring_version or SCORING_VERSION
        user = self.users.get_or_create_local_user()
        preferences = user.preferences or default_preferences()
        pref_hash = preferences_hash(preferences)
        with key_lock(f"{job.id}|{resume_id}|{version}|{pref_hash}"):
            if not force:
                cached = self.matches.get_exact(
                    job_id=job.id,
                    resume_version_id=resume_id,
                    scoring_version=version,
                    preferences_hash=pref_hash,
                )
                if cached is not None:
                    return _outcome(cached, job)
            existing = None
            if not force:
                existing = self.matches.latest_failed(
                    job_id=job.id,
                    resume_version_id=resume_id,
                    scoring_version=version,
                    preferences_hash=pref_hash,
                )
            row = self.matches.begin(
                job_id=job.id,
                resume_version_id=resume_id,
                scoring_version=version,
                preferences_hash=pref_hash,
                browse_session_id=browse_session_id,
                status="PROCESSING",
                existing=existing,
            )
            try:
                resume = self.resumes.get(resume_id)
                if resume is None:
                    raise LookupError(f"resume {resume_id} not found")
                profile = self._profile(resume)
                result = self.agent.score(self._as_jd(job), profile, preferences, scoring_version=version)
                explanation, explanation_status = self._explain(result)
                result.explanation = explanation
                result.explanation_status = explanation_status
                result.model_version = self._model_version()
                self._store(row, result)
            except ProfileUnavailable as exc:
                self.matches.finish(
                    row,
                    status="FAILED",
                    overall_score=None,
                    explanation=None,
                    explanation_status="FAILED",
                    error_class=str(exc),
                    hard_constraint_passed=False,
                )
            except LookupError:
                raise
            except Exception as exc:
                self.matches.finish(
                    row,
                    status="FAILED",
                    overall_score=None,
                    explanation=None,
                    explanation_status="FAILED",
                    error_class=type(exc).__name__,
                    hard_constraint_passed=False,
                )
            self.db.commit()
            return _outcome(row, job)

    def list_session_jobs(self, session_id: str) -> dict[str, Any]:
        browse = self.sessions.get(session_id)
        if browse is None:
            raise LookupError(f"browse session {session_id} not found")
        jobs = []
        for link in self.jobs.links_for_session(session_id):
            job = self.jobs.get(link.job_id)
            if job is None:
                continue
            match = self.matches.latest_for_job(job.id)
            jobs.append(
                {
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "salary": job.salary_text,
                    "location": job.location_text,
                    "url": job.url,
                    "match": None if match is None else _public_match(match),
                }
            )
        return {"session_id": session_id, "jobs": jobs}

    def _resolve_resume(self, browse_session_id: Optional[str], explicit: Optional[str]) -> Optional[str]:
        if explicit:
            if self.resumes.get(explicit) is None:
                raise LookupError(f"resume {explicit} not found")
            return explicit
        if browse_session_id:
            browse = self.sessions.get(browse_session_id)
            if browse is None:
                raise LookupError(f"browse session {browse_session_id} not found")
            if browse.resume_version_id:
                return browse.resume_version_id
        user = self.users.get_or_create_local_user()
        return user.active_resume_version_id

    def _profile(self, resume: ResumeVersion) -> ResumeProfile:
        with key_lock(f"profile:{resume.id}"):
            facts = resume.facts_json or {}
            if facts.get("profile_content_hash") == resume.content_hash and facts.get("profile"):
                return ResumeProfile.model_validate(facts["profile"])
            client = self.profile_client or self._gateway()
            if client is None:
                raise ProfileUnavailable("PROFILE_PROVIDER_UNAVAILABLE")
            profile = ResumeProfileAgent(client).extract(resume.content_text or "")
            self.resumes.save_profile(
                resume.id,
                profile.model_dump(mode="json"),
                content_hash=resume.content_hash,
                model_version=self._model_version(),
            )
            return profile

    def _explain(self, result: MatchResult) -> tuple[Optional[str], str]:
        client = self.explanation_client
        if client is None and self.profile_client is None:
            client = self._gateway()
        if client is None:
            return None, "FAILED"
        payload = result.model_dump(mode="json")
        payload.pop("explanation", None)
        try:
            explained = client.complete(
                MatchExplanation,
                system=EXPLAIN_SYSTEM,
                user=json.dumps(payload, ensure_ascii=False),
            )
        except Exception:
            return None, "FAILED"
        if isinstance(explained, MatchExplanation):
            return explained.explanation, "COMPLETED"
        try:
            return MatchExplanation.model_validate(explained).explanation, "COMPLETED"
        except Exception:
            return None, "FAILED"

    def _store(self, row: JobMatch, result: MatchResult) -> None:
        self.matches.finish(
            row,
            status="COMPLETED",
            overall_score=result.overall_score,
            dimension_scores=result.dimension_scores,
            matched_skills=result.matched_skills,
            missing_required_skills=result.missing_required_skills,
            evidence_from_resume=result.evidence_from_resume,
            risk_flags=[flag.model_dump() for flag in result.risk_flags],
            explanation=result.explanation,
            explanation_status=result.explanation_status,
            hard_constraint_passed=result.hard_constraint_passed,
            model_version=result.model_version or "",
            result_json=result.model_dump(mode="json"),
            error_class=None,
        )

    def _unconfigured(self, job: Job, browse_session_id: Optional[str]) -> dict[str, Any]:
        with key_lock(f"unconfigured:{job.id}"):
            existing = self.matches.latest_unconfigured(job.id)
            row = existing or self.matches.begin(
                job_id=job.id,
                resume_version_id=None,
                scoring_version=SCORING_VERSION,
                preferences_hash="",
                browse_session_id=browse_session_id,
                status="RESUME_NOT_CONFIGURED",
            )
            if existing is not None and existing.status != "RESUME_NOT_CONFIGURED":
                row = self.matches.begin(
                    job_id=job.id,
                    resume_version_id=None,
                    scoring_version=SCORING_VERSION,
                    preferences_hash="",
                    browse_session_id=browse_session_id,
                    status="RESUME_NOT_CONFIGURED",
                )
            self.matches.finish(
                row,
                status="RESUME_NOT_CONFIGURED",
                overall_score=None,
                explanation=None,
                explanation_status="SKIPPED",
                error_class="RESUME_NOT_CONFIGURED",
                hard_constraint_passed=False,
            )
            self.db.commit()
            return _outcome(row, job)

    def _gateway(self) -> Optional[LLMGateway]:
        user = self.users.get_or_create_local_user()
        llm = (user.preferences or {}).get("llm") or {}
        api_key = str(llm.get("api_key") or "")
        if not api_key:
            return None
        return LLMGateway(str(llm.get("model_type") or "deepseek"), api_key)

    def _model_version(self) -> str:
        for client in (self.profile_client, self.explanation_client):
            version = getattr(client, "model_version", None)
            if version:
                return str(version)
        gateway = self._gateway()
        if gateway is None:
            return ""
        return gateway.model_name

    def _as_jd(self, job: Job) -> JobJD:
        if job.structured_json:
            return JobJD.model_validate(job.structured_json)
        moment = job.captured_at
        return JobJD(
            id=job.id,
            source=job.source,
            url=job.url,
            canonical_url=job.canonical_url,
            title=job.title,
            company=job.company,
            salary=Salary(raw=job.salary_text),
            location=Location(raw=job.location_text),
            full_text=job.full_text,
            experience_years=ExperienceRange(),
            captured_at=moment,
            normalized_at=job.normalized_at or moment,
        )


def _outcome(row: JobMatch, job: Job) -> dict[str, Any]:
    event_type = {
        "COMPLETED": "MATCH_COMPLETED",
        "FAILED": "MATCH_FAILED",
        "RESUME_NOT_CONFIGURED": "RESUME_NOT_CONFIGURED",
        "PROCESSING": "MATCH_PROCESSING",
        "PENDING": "MATCH_QUEUED",
    }.get(row.status, "MATCH_FAILED")
    event = {"type": event_type, "job_id": job.id, "session_id": row.browse_session_id, **_public_match(row)}
    event["title"] = job.title
    event["company"] = job.company
    return {
        "job_id": job.id,
        "match_id": row.id,
        "status": row.status,
        "score": row.overall_score,
        "event": event,
    }


def _public_match(row: JobMatch) -> dict[str, Any]:
    extra = row.result_json or {}
    return {
        "match_id": row.id,
        "status": row.status,
        "overall_score": row.overall_score,
        "dimension_scores": row.dimension_scores or {},
        "matched_skills": row.matched_skills or [],
        "missing_required_skills": row.missing_required_skills or [],
        "matched_responsibilities": extra.get("matched_responsibilities") or [],
        "evidence_from_resume": row.evidence_from_resume or [],
        "evidence_links": extra.get("evidence_links") or [],
        "skill_gaps": extra.get("skill_gaps") or [],
        "risk_flags": row.risk_flags or [],
        "explanation": row.explanation,
        "explanation_status": row.explanation_status,
        "scoring_version": row.scoring_version,
        "model_version": row.model_version,
        "hard_constraint_passed": row.hard_constraint_passed,
    }
