"""Match status, preference history, and the active resume pointer.

Revision ID: 0003_match_status
Revises: 0002_job_events
Create Date: 2026-10-03
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_match_status"
down_revision = "0002_job_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("active_resume_version_id", sa.String(length=36), nullable=True))
    with op.batch_alter_table("job_matches") as batch:
        batch.add_column(sa.Column("status", sa.String(length=32), nullable=False, server_default="COMPLETED"))
        batch.add_column(sa.Column("explanation_status", sa.String(length=32), nullable=False, server_default=""))
        batch.add_column(sa.Column("preferences_hash", sa.String(length=64), nullable=False, server_default=""))
        batch.add_column(sa.Column("result_json", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("error_class", sa.String(length=200), nullable=True))
        batch.alter_column("resume_version_id", existing_type=sa.String(length=36), nullable=True)
        batch.alter_column("overall_score", existing_type=sa.Float(), nullable=True)
        batch.alter_column("explanation", existing_type=sa.Text(), nullable=True)
        batch.drop_constraint("uq_match_version", type_="unique")
    op.create_index("ix_job_matches_status", "job_matches", ["status"])


def downgrade() -> None:
    op.drop_index("ix_job_matches_status", table_name="job_matches")
    with op.batch_alter_table("job_matches") as batch:
        batch.drop_column("error_class")
        batch.drop_column("result_json")
        batch.drop_column("preferences_hash")
        batch.drop_column("explanation_status")
        batch.drop_column("status")
    op.drop_column("users", "active_resume_version_id")
