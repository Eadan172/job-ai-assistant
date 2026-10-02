"""Job events and browse-session origin.

Revision ID: 0002_job_events
Revises: 0001_initial
Create Date: 2026-10-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_job_events"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("browse_sessions", sa.Column("origin", sa.String(length=64), nullable=True))
    op.create_table(
        "job_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("browse_session_id", sa.String(length=36), sa.ForeignKey("browse_sessions.id"), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_class", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_events_fingerprint", "job_events", ["fingerprint"])


def downgrade() -> None:
    op.drop_table("job_events")
    op.drop_column("browse_sessions", "origin")
