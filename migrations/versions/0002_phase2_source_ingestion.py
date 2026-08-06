"""phase2 source ingestion

Revision ID: 0002_phase2_source_ingestion
Revises: 0001_phase1_foundation
Create Date: 2026-08-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_phase2_source_ingestion"
down_revision: Union[str, None] = "0001_phase1_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("original_path", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("file_extension", sa.String(length=16), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("encoding", sa.String(length=40), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("analysis_status", sa.String(length=32), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index(op.f("ix_source_artifacts_created_by"), "source_artifacts", ["created_by"], unique=False)
    op.create_index(op.f("ix_source_artifacts_project_id"), "source_artifacts", ["project_id"], unique=False)
    op.create_index(op.f("ix_source_artifacts_sha256"), "source_artifacts", ["sha256"], unique=False)

    op.create_table(
        "ingestion_warnings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_id", sa.String(length=36), nullable=True),
        sa.Column("original_path", sa.Text(), nullable=False),
        sa.Column("warning_code", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["source_artifacts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingestion_warnings_artifact_id"), "ingestion_warnings", ["artifact_id"], unique=False)
    op.create_index(op.f("ix_ingestion_warnings_created_by"), "ingestion_warnings", ["created_by"], unique=False)
    op.create_index(op.f("ix_ingestion_warnings_project_id"), "ingestion_warnings", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ingestion_warnings_project_id"), table_name="ingestion_warnings")
    op.drop_index(op.f("ix_ingestion_warnings_created_by"), table_name="ingestion_warnings")
    op.drop_index(op.f("ix_ingestion_warnings_artifact_id"), table_name="ingestion_warnings")
    op.drop_table("ingestion_warnings")
    op.drop_index(op.f("ix_source_artifacts_sha256"), table_name="source_artifacts")
    op.drop_index(op.f("ix_source_artifacts_project_id"), table_name="source_artifacts")
    op.drop_index(op.f("ix_source_artifacts_created_by"), table_name="source_artifacts")
    op.drop_table("source_artifacts")
