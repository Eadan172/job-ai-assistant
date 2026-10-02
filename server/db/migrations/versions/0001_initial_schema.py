"""Initial local schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "resume_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("parent_resume_id", sa.String(length=36), sa.ForeignKey("resume_versions.id"), nullable=True),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("facts_json", sa.JSON(), nullable=True),
        sa.Column("validator_status", sa.String(length=32), nullable=True),
        sa.Column("file_path", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resume_versions_job_id", "resume_versions", ["job_id"])
    op.create_index("ix_resume_versions_content_hash", "resume_versions", ["content_hash"])
    op.create_table(
        "browse_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resume_version_id", sa.String(length=36), sa.ForeignKey("resume_versions.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("export_formats", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_class", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("label"),
    )
    op.create_index("ix_browse_sessions_user_id", "browse_sessions", ["user_id"])
    op.create_index("ix_browse_sessions_status", "browse_sessions", ["status"])
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("browse_session_id", sa.String(length=36), sa.ForeignKey("browse_sessions.id"), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("company", sa.String(length=500), nullable=False),
        sa.Column("salary_text", sa.String(length=200), nullable=False),
        sa.Column("location_text", sa.String(length=200), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("structured_json", sa.JSON(), nullable=True),
        sa.Column("raw_extract_json", sa.JSON(), nullable=True),
        sa.Column("source_spans", sa.JSON(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("fingerprint"),
    )
    op.create_index("ix_jobs_browse_session_id", "jobs", ["browse_session_id"])
    op.create_table(
        "session_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("browse_session_id", sa.String(length=36), sa.ForeignKey("browse_sessions.id"), nullable=False),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("jd_number", sa.String(length=32), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("browse_session_id", "job_id", name="uq_session_job"),
        sa.UniqueConstraint("browse_session_id", "jd_number", name="uq_session_jd_number"),
    )
    op.create_index("ix_session_jobs_browse_session_id", "session_jobs", ["browse_session_id"])
    op.create_index("ix_session_jobs_job_id", "session_jobs", ["job_id"])
    op.create_table(
        "job_matches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("resume_version_id", sa.String(length=36), sa.ForeignKey("resume_versions.id"), nullable=False),
        sa.Column("browse_session_id", sa.String(length=36), sa.ForeignKey("browse_sessions.id"), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("dimension_scores", sa.JSON(), nullable=False),
        sa.Column("matched_skills", sa.JSON(), nullable=False),
        sa.Column("missing_required_skills", sa.JSON(), nullable=False),
        sa.Column("evidence_from_resume", sa.JSON(), nullable=False),
        sa.Column("risk_flags", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("hard_constraint_passed", sa.Boolean(), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("scoring_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "resume_version_id", "scoring_version", name="uq_match_version"),
    )
    op.create_index("ix_job_matches_job_id", "job_matches", ["job_id"])
    op.create_index("ix_job_matches_resume_version_id", "job_matches", ["resume_version_id"])
    op.create_index("ix_job_matches_browse_session_id", "job_matches", ["browse_session_id"])
    op.create_table(
        "tailored_resumes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("resume_version_id", sa.String(length=36), sa.ForeignKey("resume_versions.id"), nullable=False),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("parent_resume_id", sa.String(length=36), sa.ForeignKey("resume_versions.id"), nullable=False),
        sa.Column("browse_session_id", sa.String(length=36), sa.ForeignKey("browse_sessions.id"), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("validator_status", sa.String(length=32), nullable=False),
        sa.Column("revision_count", sa.Integer(), nullable=False),
        sa.Column("keyword_coverage", sa.JSON(), nullable=False),
        sa.Column("critique_json", sa.JSON(), nullable=True),
        sa.Column("file_path_docx", sa.String(length=1000), nullable=True),
        sa.Column("file_path_md", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("resume_version_id"),
    )
    op.create_index("ix_tailored_resumes_job_id", "tailored_resumes", ["job_id"])
    op.create_table(
        "communication_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("browse_session_id", sa.String(length=36), sa.ForeignKey("browse_sessions.id"), nullable=True),
        sa.Column("resume_version_id", sa.String(length=36), sa.ForeignKey("resume_versions.id"), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_communication_sessions_job_id", "communication_sessions", ["job_id"])
    op.create_index("ix_communication_sessions_status", "communication_sessions", ["status"])
    op.create_table(
        "communication_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("communication_sessions.id"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "seq", name="uq_message_seq"),
    )
    op.create_index("ix_communication_messages_session_id", "communication_messages", ["session_id"])
    op.create_table(
        "communication_evaluations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("communication_sessions.id"), nullable=False),
        sa.Column("title", sa.String(length=64), nullable=False),
        sa.Column("overall", sa.Float(), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("weaknesses", sa.JSON(), nullable=False),
        sa.Column("missed_questions", sa.JSON(), nullable=False),
        sa.Column("improvement_actions", sa.JSON(), nullable=False),
        sa.Column("transcript_summary", sa.Text(), nullable=False),
        sa.Column("evidence_messages", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id"),
    )
    op.create_table(
        "export_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("browse_session_id", sa.String(length=36), sa.ForeignKey("browse_sessions.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("formats", sa.JSON(), nullable=False),
        sa.Column("file_xlsx", sa.String(length=1000), nullable=True),
        sa.Column("file_md", sa.String(length=1000), nullable=True),
        sa.Column("error_class", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_export_tasks_browse_session_id", "export_tasks", ["browse_session_id"])
    op.create_index("ix_export_tasks_status", "export_tasks", ["status"])
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("browse_session_id", sa.String(length=36), sa.ForeignKey("browse_sessions.id"), nullable=True),
        sa.Column("agent_name", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("input_length", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("error_class", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_runs_trace_id", "agent_runs", ["trace_id"])


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("export_tasks")
    op.drop_table("communication_evaluations")
    op.drop_table("communication_messages")
    op.drop_table("communication_sessions")
    op.drop_table("tailored_resumes")
    op.drop_table("job_matches")
    op.drop_table("session_jobs")
    op.drop_table("jobs")
    op.drop_table("browse_sessions")
    op.drop_table("resume_versions")
    op.drop_table("users")
