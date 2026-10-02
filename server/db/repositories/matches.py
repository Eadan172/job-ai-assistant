"""Match records keyed by job, resume version, and scoring version."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from db.models import JobMatch


class JobMatchRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_exact(
        self,
        *,
        job_id: str,
        resume_version_id: str,
        scoring_version: str,
    ) -> Optional[JobMatch]:
        return (
            self.db.query(JobMatch)
            .filter(
                JobMatch.job_id == job_id,
                JobMatch.resume_version_id == resume_version_id,
                JobMatch.scoring_version == scoring_version,
            )
            .one_or_none()
        )

    def save(
        self,
        *,
        job_id: str,
        resume_version_id: str,
        scoring_version: str,
        overall_score: float,
        dimension_scores: dict[str, Any],
        matched_skills: list[str],
        missing_required_skills: list[str],
        evidence_from_resume: list[str],
        risk_flags: list[str],
        explanation: str,
        model_version: str,
        browse_session_id: Optional[str] = None,
        hard_constraint_passed: bool = True,
    ) -> tuple[JobMatch, bool]:
        existing = self.get_exact(
            job_id=job_id,
            resume_version_id=resume_version_id,
            scoring_version=scoring_version,
        )
        if existing is not None:
            return existing, False
        row = JobMatch(
            job_id=job_id,
            resume_version_id=resume_version_id,
            browse_session_id=browse_session_id,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            matched_skills=matched_skills,
            missing_required_skills=missing_required_skills,
            evidence_from_resume=evidence_from_resume,
            risk_flags=risk_flags,
            explanation=explanation,
            hard_constraint_passed=hard_constraint_passed,
            model_version=model_version,
            scoring_version=scoring_version,
        )
        self.db.add(row)
        self.db.flush()
        return row, True
