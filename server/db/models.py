"""SQLite tables for the local job workbench.

`resume_versions.job_id` is an indexed value without a foreign key.
A real FK would cycle through browse_sessions and jobs on SQLite.
Tailored rows enforce the job link in `tailored_resumes`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(320), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    resumes: Mapped[list[ResumeVersion]] = relationship(back_populates="user")
    browse_sessions: Mapped[list[BrowseSession]] = relationship(back_populates="user")


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"))
    parent_resume_id: Mapped[Optional[str]] = mapped_column(ForeignKey("resume_versions.id"))
    job_id: Mapped[Optional[str]] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(32), default="original")
    filename: Mapped[str] = mapped_column(String(500), default="")
    content_text: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    facts_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    validator_status: Mapped[Optional[str]] = mapped_column(String(32))
    file_path: Mapped[Optional[str]] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[Optional[User]] = relationship(back_populates="resumes")
    parent: Mapped[Optional[ResumeVersion]] = relationship(
        remote_side="ResumeVersion.id",
        back_populates="children",
    )
    children: Mapped[list[ResumeVersion]] = relationship(back_populates="parent")


class BrowseSession(Base):
    __tablename__ = "browse_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), index=True)
    resume_version_id: Mapped[Optional[str]] = mapped_column(ForeignKey("resume_versions.id"))
    status: Mapped[str] = mapped_column(String(32), default="IDLE", index=True)
    label: Mapped[str] = mapped_column(String(32), unique=True)
    threshold: Mapped[float] = mapped_column(Float, default=70)
    export_formats: Mapped[Optional[list[str]]] = mapped_column(JSON)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_class: Mapped[Optional[str]] = mapped_column(String(200))
    origin: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[Optional[User]] = relationship(back_populates="browse_sessions")
    resume_version: Mapped[Optional[ResumeVersion]] = relationship()
    jobs: Mapped[list[Job]] = relationship(back_populates="origin_session")
    links: Mapped[list[SessionJob]] = relationship(back_populates="browse_session")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    browse_session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("browse_sessions.id"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    source: Mapped[str] = mapped_column(String(64), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    canonical_url: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(500), default="")
    company: Mapped[str] = mapped_column(String(500), default="")
    salary_text: Mapped[str] = mapped_column(String(200), default="")
    location_text: Mapped[str] = mapped_column(String(200), default="")
    full_text: Mapped[str] = mapped_column(Text, default="")
    structured_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    raw_extract_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    source_spans: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    normalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    origin_session: Mapped[Optional[BrowseSession]] = relationship(back_populates="jobs")
    links: Mapped[list[SessionJob]] = relationship(back_populates="job")
    matches: Mapped[list[JobMatch]] = relationship(back_populates="job")


class SessionJob(Base):
    __tablename__ = "session_jobs"
    __table_args__ = (
        UniqueConstraint("browse_session_id", "job_id", name="uq_session_job"),
        UniqueConstraint("browse_session_id", "jd_number", name="uq_session_jd_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    browse_session_id: Mapped[str] = mapped_column(ForeignKey("browse_sessions.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    jd_number: Mapped[Optional[str]] = mapped_column(String(32))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    browse_session: Mapped[BrowseSession] = relationship(back_populates="links")
    job: Mapped[Job] = relationship(back_populates="links")


class JobMatch(Base):
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "resume_version_id",
            "scoring_version",
            name="uq_match_version",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    resume_version_id: Mapped[str] = mapped_column(ForeignKey("resume_versions.id"), index=True)
    browse_session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("browse_sessions.id"), index=True)
    overall_score: Mapped[float] = mapped_column(Float, default=0)
    dimension_scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    matched_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    missing_required_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_from_resume: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text, default="")
    hard_constraint_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    model_version: Mapped[str] = mapped_column(String(100), default="")
    scoring_version: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[Job] = relationship(back_populates="matches")
    resume_version: Mapped[ResumeVersion] = relationship()


class TailoredResume(Base):
    __tablename__ = "tailored_resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    resume_version_id: Mapped[str] = mapped_column(ForeignKey("resume_versions.id"), unique=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    parent_resume_id: Mapped[str] = mapped_column(ForeignKey("resume_versions.id"))
    browse_session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("browse_sessions.id"))
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    validator_status: Mapped[str] = mapped_column(String(32), default="DRAFT")
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    keyword_coverage: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    critique_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    file_path_docx: Mapped[Optional[str]] = mapped_column(String(1000))
    file_path_md: Mapped[Optional[str]] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CommunicationSession(Base):
    __tablename__ = "communication_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    browse_session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("browse_sessions.id"))
    resume_version_id: Mapped[Optional[str]] = mapped_column(ForeignKey("resume_versions.id"))
    role: Mapped[str] = mapped_column(String(32), default="hr")
    status: Mapped[str] = mapped_column(String(32), default="CREATED", index=True)
    title: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list[CommunicationMessage]] = relationship(back_populates="session")
    evaluation: Mapped[Optional[CommunicationEvaluation]] = relationship(
        back_populates="session",
        uselist=False,
    )


class CommunicationMessage(Base):
    __tablename__ = "communication_messages"
    __table_args__ = (UniqueConstraint("session_id", "seq", name="uq_message_seq"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("communication_sessions.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[CommunicationSession] = relationship(back_populates="messages")


class CommunicationEvaluation(Base):
    __tablename__ = "communication_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("communication_sessions.id"), unique=True)
    title: Mapped[str] = mapped_column(String(64))
    overall: Mapped[float] = mapped_column(Float, default=0)
    dimensions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSON, default=list)
    missed_questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    improvement_actions: Mapped[list[str]] = mapped_column(JSON, default=list)
    transcript_summary: Mapped[str] = mapped_column(Text, default="")
    evidence_messages: Mapped[list[str]] = mapped_column(JSON, default=list)
    model_version: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[CommunicationSession] = relationship(back_populates="evaluation")


class JobEvent(Base):
    """Idempotency record. A repeated event id must not create another job."""

    __tablename__ = "job_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64))
    fingerprint: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    job_id: Mapped[Optional[str]] = mapped_column(ForeignKey("jobs.id"))
    browse_session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("browse_sessions.id"))
    url: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="accepted")
    error_class: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExportTask(Base):
    __tablename__ = "export_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    browse_session_id: Mapped[str] = mapped_column(ForeignKey("browse_sessions.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    threshold: Mapped[float] = mapped_column(Float, default=70)
    formats: Mapped[list[str]] = mapped_column(JSON, default=list)
    file_xlsx: Mapped[Optional[str]] = mapped_column(String(1000))
    file_md: Mapped[Optional[str]] = mapped_column(String(1000))
    error_class: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    trace_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    browse_session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("browse_sessions.id"))
    agent_name: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[str] = mapped_column(String(100), default="")
    input_hash: Mapped[str] = mapped_column(String(64), default="")
    input_length: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_class: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
