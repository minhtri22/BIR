"""phase3 static extraction

Revision ID: 0003_phase3_static_extraction
Revises: 0002_phase2_source_ingestion
Create Date: 2026-08-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_phase3_static_extraction"
down_revision: Union[str, None] = "0002_phase2_source_ingestion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ACTIVE_JOB_WHERE = sa.text("status IN ('queued', 'running')")
TARGET_STATEMENT_WHERE = sa.text("statement_id IS NOT NULL")
TARGET_GAP_WHERE = sa.text("analysis_gap_id IS NOT NULL")
TARGET_QUESTION_WHERE = sa.text("unresolved_question_id IS NOT NULL")


def upgrade() -> None:
    op.create_table(
        "analyzer_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("analyzer_name", sa.String(length=80), nullable=False),
        sa.Column("analyzer_version", sa.String(length=40), nullable=False),
        sa.Column("extractor_kind", sa.String(length=32), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("configuration_hash", sa.String(length=64), nullable=False),
        sa.Column("pattern_set_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analyzer_name",
            "analyzer_version",
            "configuration_hash",
            name="uq_analyzer_versions_identity",
        ),
    )
    op.create_index(op.f("ix_analyzer_versions_analyzer_name"), "analyzer_versions", ["analyzer_name"])
    op.create_index(op.f("ix_analyzer_versions_analyzer_version"), "analyzer_versions", ["analyzer_version"])
    op.create_index(op.f("ix_analyzer_versions_configuration_hash"), "analyzer_versions", ["configuration_hash"])
    op.create_index(op.f("ix_analyzer_versions_extractor_kind"), "analyzer_versions", ["extractor_kind"])

    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("analyzer_version_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("requested_by", sa.String(length=36), nullable=False),
        sa.Column("requested_artifact_count", sa.Integer(), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("retry_of_job_id", sa.String(length=36), nullable=True),
        sa.Column("previous_project_status", sa.String(length=32), nullable=False),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("gap_count", sa.Integer(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("requested_artifact_count >= 1", name="ck_analysis_jobs_artifact_count"),
        sa.CheckConstraint("attempt_no >= 1", name="ck_analysis_jobs_attempt_no"),
        sa.ForeignKeyConstraint(["analyzer_version_id"], ["analyzer_versions.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["retry_of_job_id"], ["analysis_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "request_fingerprint",
            "attempt_no",
            name="uq_analysis_jobs_project_request_attempt",
        ),
    )
    op.create_index(op.f("ix_analysis_jobs_analyzer_version_id"), "analysis_jobs", ["analyzer_version_id"])
    op.create_index(op.f("ix_analysis_jobs_created_at"), "analysis_jobs", ["created_at"])
    op.create_index(op.f("ix_analysis_jobs_failure_code"), "analysis_jobs", ["failure_code"])
    op.create_index(op.f("ix_analysis_jobs_project_id"), "analysis_jobs", ["project_id"])
    op.create_index(op.f("ix_analysis_jobs_requested_by"), "analysis_jobs", ["requested_by"])
    op.create_index(op.f("ix_analysis_jobs_request_fingerprint"), "analysis_jobs", ["request_fingerprint"])
    op.create_index(op.f("ix_analysis_jobs_retry_of_job_id"), "analysis_jobs", ["retry_of_job_id"])
    op.create_index(op.f("ix_analysis_jobs_status"), "analysis_jobs", ["status"])
    op.create_index(
        "uq_analysis_jobs_active_project",
        "analysis_jobs",
        ["project_id"],
        unique=True,
        sqlite_where=ACTIVE_JOB_WHERE,
        postgresql_where=ACTIVE_JOB_WHERE,
    )
    op.create_index(
        "uq_analysis_jobs_active_request",
        "analysis_jobs",
        ["project_id", "request_fingerprint"],
        unique=True,
        sqlite_where=ACTIVE_JOB_WHERE,
        postgresql_where=ACTIVE_JOB_WHERE,
    )

    op.create_table(
        "analysis_job_artifacts",
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["source_artifacts.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"]),
        sa.PrimaryKeyConstraint("job_id", "artifact_id"),
    )
    op.create_index(op.f("ix_analysis_job_artifacts_artifact_id"), "analysis_job_artifacts", ["artifact_id"])
    op.create_index(op.f("ix_analysis_job_artifacts_artifact_sha256"), "analysis_job_artifacts", ["artifact_sha256"])
    op.create_index(op.f("ix_analysis_job_artifacts_status"), "analysis_job_artifacts", ["status"])

    op.create_table(
        "source_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_job_id", sa.String(length=36), nullable=False),
        sa.Column("analyzer_version_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("chunk_type", sa.String(length=32), nullable=False),
        sa.Column("parent_chunk_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("start_line >= 1", name="ck_source_chunks_start_line"),
        sa.CheckConstraint("end_line >= start_line", name="ck_source_chunks_end_line"),
        sa.CheckConstraint("line_count >= 1", name="ck_source_chunks_line_count"),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["analyzer_version_id"], ["analyzer_versions.id"]),
        sa.ForeignKeyConstraint(["artifact_id"], ["source_artifacts.id"]),
        sa.ForeignKeyConstraint(["parent_chunk_id"], ["source_chunks.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_job_id",
            "artifact_id",
            "chunk_index",
            name="uq_source_chunks_job_artifact_index",
        ),
        sa.UniqueConstraint(
            "analysis_job_id",
            "artifact_id",
            "start_line",
            "end_line",
            "content_hash",
            name="uq_source_chunks_job_artifact_range_hash",
        ),
    )
    op.create_index(op.f("ix_source_chunks_analysis_job_id"), "source_chunks", ["analysis_job_id"])
    op.create_index(op.f("ix_source_chunks_analyzer_version_id"), "source_chunks", ["analyzer_version_id"])
    op.create_index(op.f("ix_source_chunks_artifact_id"), "source_chunks", ["artifact_id"])
    op.create_index(op.f("ix_source_chunks_chunk_type"), "source_chunks", ["chunk_type"])
    op.create_index(op.f("ix_source_chunks_content_hash"), "source_chunks", ["content_hash"])
    op.create_index(op.f("ix_source_chunks_end_line"), "source_chunks", ["end_line"])
    op.create_index(op.f("ix_source_chunks_parent_chunk_id"), "source_chunks", ["parent_chunk_id"])
    op.create_index(op.f("ix_source_chunks_project_id"), "source_chunks", ["project_id"])
    op.create_index(op.f("ix_source_chunks_start_line"), "source_chunks", ["start_line"])

    op.create_table(
        "business_statements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_job_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("pattern_id", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("statement_text", sa.Text(), nullable=False),
        sa.Column("structured_expression_json", sa.JSON(), nullable=True),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("extraction_method", sa.String(length=32), nullable=False),
        sa.Column("analyzer_version_id", sa.String(length=36), nullable=False),
        sa.Column("primary_artifact_id", sa.String(length=36), nullable=False),
        sa.Column("primary_chunk_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_identity_hash", sa.String(length=64), nullable=False),
        sa.Column("unresolved_count", sa.Integer(), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("supersedes_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_by_kind", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_business_statements_confidence"),
        sa.CheckConstraint("revision_no >= 1", name="ck_business_statements_revision_no"),
        sa.CheckConstraint("unresolved_count >= 0", name="ck_business_statements_unresolved_count"),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["analyzer_version_id"], ["analyzer_versions.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["primary_artifact_id"], ["source_artifacts.id"]),
        sa.ForeignKeyConstraint(["primary_chunk_id"], ["source_chunks.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["supersedes_id"], ["business_statements.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_job_id",
            "candidate_identity_hash",
            name="uq_business_statements_candidate_identity",
        ),
    )
    op.create_index(op.f("ix_business_statements_analysis_job_id"), "business_statements", ["analysis_job_id"])
    op.create_index(op.f("ix_business_statements_analyzer_version_id"), "business_statements", ["analyzer_version_id"])
    op.create_index(op.f("ix_business_statements_candidate_identity_hash"), "business_statements", ["candidate_identity_hash"])
    op.create_index(op.f("ix_business_statements_confidence"), "business_statements", ["confidence"])
    op.create_index(op.f("ix_business_statements_created_at"), "business_statements", ["created_at"])
    op.create_index(op.f("ix_business_statements_created_by"), "business_statements", ["created_by"])
    op.create_index(op.f("ix_business_statements_created_by_kind"), "business_statements", ["created_by_kind"])
    op.create_index(op.f("ix_business_statements_extraction_method"), "business_statements", ["extraction_method"])
    op.create_index(op.f("ix_business_statements_pattern_id"), "business_statements", ["pattern_id"])
    op.create_index(op.f("ix_business_statements_primary_artifact_id"), "business_statements", ["primary_artifact_id"])
    op.create_index(op.f("ix_business_statements_primary_chunk_id"), "business_statements", ["primary_chunk_id"])
    op.create_index(op.f("ix_business_statements_project_id"), "business_statements", ["project_id"])
    op.create_index(op.f("ix_business_statements_status"), "business_statements", ["status"])
    op.create_index(op.f("ix_business_statements_supersedes_id"), "business_statements", ["supersedes_id"])
    op.create_index(op.f("ix_business_statements_type"), "business_statements", ["type"])

    op.create_table(
        "analysis_gaps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_job_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_id", sa.String(length=36), nullable=True),
        sa.Column("source_chunk_id", sa.String(length=36), nullable=True),
        sa.Column("gap_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("analyzer_version_id", sa.String(length=36), nullable=False),
        sa.Column("identity_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_by_kind", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["analyzer_version_id"], ["analyzer_versions.id"]),
        sa.ForeignKeyConstraint(["artifact_id"], ["source_artifacts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["source_chunks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_job_id", "identity_hash", name="uq_analysis_gaps_identity"),
    )
    op.create_index(op.f("ix_analysis_gaps_analysis_job_id"), "analysis_gaps", ["analysis_job_id"])
    op.create_index(op.f("ix_analysis_gaps_analyzer_version_id"), "analysis_gaps", ["analyzer_version_id"])
    op.create_index(op.f("ix_analysis_gaps_artifact_id"), "analysis_gaps", ["artifact_id"])
    op.create_index(op.f("ix_analysis_gaps_created_at"), "analysis_gaps", ["created_at"])
    op.create_index(op.f("ix_analysis_gaps_created_by"), "analysis_gaps", ["created_by"])
    op.create_index(op.f("ix_analysis_gaps_created_by_kind"), "analysis_gaps", ["created_by_kind"])
    op.create_index(op.f("ix_analysis_gaps_gap_type"), "analysis_gaps", ["gap_type"])
    op.create_index(op.f("ix_analysis_gaps_identity_hash"), "analysis_gaps", ["identity_hash"])
    op.create_index(op.f("ix_analysis_gaps_project_id"), "analysis_gaps", ["project_id"])
    op.create_index(op.f("ix_analysis_gaps_severity"), "analysis_gaps", ["severity"])
    op.create_index(op.f("ix_analysis_gaps_source_chunk_id"), "analysis_gaps", ["source_chunk_id"])
    op.create_index(op.f("ix_analysis_gaps_status"), "analysis_gaps", ["status"])

    op.create_table(
        "unresolved_questions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_job_id", sa.String(length=36), nullable=False),
        sa.Column("statement_id", sa.String(length=36), nullable=True),
        sa.Column("artifact_id", sa.String(length=36), nullable=True),
        sa.Column("source_chunk_id", sa.String(length=36), nullable=True),
        sa.Column("question_type", sa.String(length=60), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("analyzer_version_id", sa.String(length=36), nullable=False),
        sa.Column("identity_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_by_kind", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["analyzer_version_id"], ["analyzer_versions.id"]),
        sa.ForeignKeyConstraint(["artifact_id"], ["source_artifacts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["source_chunks.id"]),
        sa.ForeignKeyConstraint(["statement_id"], ["business_statements.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_job_id", "identity_hash", name="uq_unresolved_questions_identity"),
    )
    op.create_index(op.f("ix_unresolved_questions_analysis_job_id"), "unresolved_questions", ["analysis_job_id"])
    op.create_index(op.f("ix_unresolved_questions_analyzer_version_id"), "unresolved_questions", ["analyzer_version_id"])
    op.create_index(op.f("ix_unresolved_questions_artifact_id"), "unresolved_questions", ["artifact_id"])
    op.create_index(op.f("ix_unresolved_questions_created_at"), "unresolved_questions", ["created_at"])
    op.create_index(op.f("ix_unresolved_questions_created_by"), "unresolved_questions", ["created_by"])
    op.create_index(op.f("ix_unresolved_questions_created_by_kind"), "unresolved_questions", ["created_by_kind"])
    op.create_index(op.f("ix_unresolved_questions_identity_hash"), "unresolved_questions", ["identity_hash"])
    op.create_index(op.f("ix_unresolved_questions_priority"), "unresolved_questions", ["priority"])
    op.create_index(op.f("ix_unresolved_questions_project_id"), "unresolved_questions", ["project_id"])
    op.create_index(op.f("ix_unresolved_questions_question_type"), "unresolved_questions", ["question_type"])
    op.create_index(op.f("ix_unresolved_questions_source_chunk_id"), "unresolved_questions", ["source_chunk_id"])
    op.create_index(op.f("ix_unresolved_questions_statement_id"), "unresolved_questions", ["statement_id"])
    op.create_index(op.f("ix_unresolved_questions_status"), "unresolved_questions", ["status"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_job_id", sa.String(length=36), nullable=False),
        sa.Column("statement_id", sa.String(length=36), nullable=True),
        sa.Column("analysis_gap_id", sa.String(length=36), nullable=True),
        sa.Column("unresolved_question_id", sa.String(length=36), nullable=True),
        sa.Column("artifact_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_chunk_id", sa.String(length=36), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("excerpt_sha256", sa.String(length=64), nullable=False),
        sa.Column("relation_type", sa.String(length=40), nullable=False),
        sa.Column("extraction_method", sa.String(length=32), nullable=False),
        sa.Column("pattern_id", sa.String(length=80), nullable=False),
        sa.Column("analyzer_version_id", sa.String(length=36), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_by_kind", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("start_line >= 1", name="ck_evidence_start_line"),
        sa.CheckConstraint("end_line >= start_line", name="ck_evidence_end_line"),
        sa.CheckConstraint(
            "((CASE WHEN statement_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN analysis_gap_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN unresolved_question_id IS NOT NULL THEN 1 ELSE 0 END)) = 1",
            name="ck_evidence_exactly_one_target",
        ),
        sa.ForeignKeyConstraint(["analysis_gap_id"], ["analysis_gaps.id"]),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["analyzer_version_id"], ["analyzer_versions.id"]),
        sa.ForeignKeyConstraint(["artifact_id"], ["source_artifacts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["source_chunks.id"]),
        sa.ForeignKeyConstraint(["statement_id"], ["business_statements.id"]),
        sa.ForeignKeyConstraint(["unresolved_question_id"], ["unresolved_questions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evidence_analysis_gap_id"), "evidence", ["analysis_gap_id"])
    op.create_index(op.f("ix_evidence_analysis_job_id"), "evidence", ["analysis_job_id"])
    op.create_index(op.f("ix_evidence_analyzer_version_id"), "evidence", ["analyzer_version_id"])
    op.create_index(op.f("ix_evidence_artifact_id"), "evidence", ["artifact_id"])
    op.create_index(op.f("ix_evidence_artifact_sha256"), "evidence", ["artifact_sha256"])
    op.create_index(op.f("ix_evidence_created_at"), "evidence", ["created_at"])
    op.create_index(op.f("ix_evidence_created_by"), "evidence", ["created_by"])
    op.create_index(op.f("ix_evidence_created_by_kind"), "evidence", ["created_by_kind"])
    op.create_index(op.f("ix_evidence_end_line"), "evidence", ["end_line"])
    op.create_index(op.f("ix_evidence_extraction_method"), "evidence", ["extraction_method"])
    op.create_index(op.f("ix_evidence_pattern_id"), "evidence", ["pattern_id"])
    op.create_index(op.f("ix_evidence_project_id"), "evidence", ["project_id"])
    op.create_index(op.f("ix_evidence_relation_type"), "evidence", ["relation_type"])
    op.create_index(op.f("ix_evidence_source_chunk_id"), "evidence", ["source_chunk_id"])
    op.create_index(op.f("ix_evidence_start_line"), "evidence", ["start_line"])
    op.create_index(op.f("ix_evidence_statement_id"), "evidence", ["statement_id"])
    op.create_index(op.f("ix_evidence_unresolved_question_id"), "evidence", ["unresolved_question_id"])
    op.create_index(
        "uq_evidence_statement_range",
        "evidence",
        ["statement_id", "artifact_id", "start_line", "end_line", "relation_type", "analyzer_version_id"],
        unique=True,
        sqlite_where=TARGET_STATEMENT_WHERE,
        postgresql_where=TARGET_STATEMENT_WHERE,
    )
    op.create_index(
        "uq_evidence_gap_range",
        "evidence",
        ["analysis_gap_id", "artifact_id", "start_line", "end_line", "relation_type", "analyzer_version_id"],
        unique=True,
        sqlite_where=TARGET_GAP_WHERE,
        postgresql_where=TARGET_GAP_WHERE,
    )
    op.create_index(
        "uq_evidence_question_range",
        "evidence",
        ["unresolved_question_id", "artifact_id", "start_line", "end_line", "relation_type", "analyzer_version_id"],
        unique=True,
        sqlite_where=TARGET_QUESTION_WHERE,
        postgresql_where=TARGET_QUESTION_WHERE,
    )


def downgrade() -> None:
    op.drop_index("uq_evidence_question_range", table_name="evidence")
    op.drop_index("uq_evidence_gap_range", table_name="evidence")
    op.drop_index("uq_evidence_statement_range", table_name="evidence")
    op.drop_index(op.f("ix_evidence_unresolved_question_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_statement_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_start_line"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_source_chunk_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_relation_type"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_project_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_pattern_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_extraction_method"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_end_line"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_created_by_kind"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_created_by"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_created_at"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_artifact_sha256"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_artifact_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_analyzer_version_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_analysis_job_id"), table_name="evidence")
    op.drop_index(op.f("ix_evidence_analysis_gap_id"), table_name="evidence")
    op.drop_table("evidence")

    op.drop_index(op.f("ix_unresolved_questions_status"), table_name="unresolved_questions")
    op.drop_index(op.f("ix_unresolved_questions_statement_id"), table_name="unresolved_questions")
    op.drop_index(op.f("ix_unresolved_questions_source_chunk_id"), table_name="unresolved_questions")
    op.drop_index(op.f("ix_unresolved_questions_question_type"), table_name="unresolved_questions")
    op.drop_index(op.f("ix_unresolved_questions_project_id"), table_name="unresolved_questions")
    op.drop_index(op.f("ix_unresolved_questions_priority"), table_name="unresolved_questions")
    op.drop_index(op.f("ix_unresolved_questions_identity_hash"), table_name="unresolved_questions")
    op.drop_index(op.f("ix_unresolved_questions_created_by_kind"), table_name="unresolved_questions")
    op.drop_index(op.f("ix_unresolved_questions_created_by"), table_name="unresolved_questions")
    op.drop_index(op.f("ix_unresolved_questions_created_at"), table_name="unresolved_questions")
    op.drop_index(op.f("ix_unresolved_questions_artifact_id"), table_name="unresolved_questions")
    op.drop_index(op.f("ix_unresolved_questions_analyzer_version_id"), table_name="unresolved_questions")
    op.drop_index(op.f("ix_unresolved_questions_analysis_job_id"), table_name="unresolved_questions")
    op.drop_table("unresolved_questions")

    op.drop_index(op.f("ix_analysis_gaps_status"), table_name="analysis_gaps")
    op.drop_index(op.f("ix_analysis_gaps_source_chunk_id"), table_name="analysis_gaps")
    op.drop_index(op.f("ix_analysis_gaps_severity"), table_name="analysis_gaps")
    op.drop_index(op.f("ix_analysis_gaps_project_id"), table_name="analysis_gaps")
    op.drop_index(op.f("ix_analysis_gaps_identity_hash"), table_name="analysis_gaps")
    op.drop_index(op.f("ix_analysis_gaps_gap_type"), table_name="analysis_gaps")
    op.drop_index(op.f("ix_analysis_gaps_created_by_kind"), table_name="analysis_gaps")
    op.drop_index(op.f("ix_analysis_gaps_created_by"), table_name="analysis_gaps")
    op.drop_index(op.f("ix_analysis_gaps_created_at"), table_name="analysis_gaps")
    op.drop_index(op.f("ix_analysis_gaps_artifact_id"), table_name="analysis_gaps")
    op.drop_index(op.f("ix_analysis_gaps_analyzer_version_id"), table_name="analysis_gaps")
    op.drop_index(op.f("ix_analysis_gaps_analysis_job_id"), table_name="analysis_gaps")
    op.drop_table("analysis_gaps")

    op.drop_index(op.f("ix_business_statements_type"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_supersedes_id"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_status"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_project_id"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_primary_chunk_id"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_primary_artifact_id"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_pattern_id"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_extraction_method"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_created_by_kind"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_created_by"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_created_at"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_confidence"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_candidate_identity_hash"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_analyzer_version_id"), table_name="business_statements")
    op.drop_index(op.f("ix_business_statements_analysis_job_id"), table_name="business_statements")
    op.drop_table("business_statements")

    op.drop_index(op.f("ix_source_chunks_start_line"), table_name="source_chunks")
    op.drop_index(op.f("ix_source_chunks_project_id"), table_name="source_chunks")
    op.drop_index(op.f("ix_source_chunks_parent_chunk_id"), table_name="source_chunks")
    op.drop_index(op.f("ix_source_chunks_end_line"), table_name="source_chunks")
    op.drop_index(op.f("ix_source_chunks_content_hash"), table_name="source_chunks")
    op.drop_index(op.f("ix_source_chunks_chunk_type"), table_name="source_chunks")
    op.drop_index(op.f("ix_source_chunks_artifact_id"), table_name="source_chunks")
    op.drop_index(op.f("ix_source_chunks_analyzer_version_id"), table_name="source_chunks")
    op.drop_index(op.f("ix_source_chunks_analysis_job_id"), table_name="source_chunks")
    op.drop_table("source_chunks")

    op.drop_index(op.f("ix_analysis_job_artifacts_status"), table_name="analysis_job_artifacts")
    op.drop_index(op.f("ix_analysis_job_artifacts_artifact_sha256"), table_name="analysis_job_artifacts")
    op.drop_index(op.f("ix_analysis_job_artifacts_artifact_id"), table_name="analysis_job_artifacts")
    op.drop_table("analysis_job_artifacts")

    op.drop_index("uq_analysis_jobs_active_request", table_name="analysis_jobs")
    op.drop_index("uq_analysis_jobs_active_project", table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_status"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_retry_of_job_id"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_request_fingerprint"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_requested_by"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_project_id"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_failure_code"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_created_at"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_analyzer_version_id"), table_name="analysis_jobs")
    op.drop_table("analysis_jobs")

    op.drop_index(op.f("ix_analyzer_versions_extractor_kind"), table_name="analyzer_versions")
    op.drop_index(op.f("ix_analyzer_versions_configuration_hash"), table_name="analyzer_versions")
    op.drop_index(op.f("ix_analyzer_versions_analyzer_version"), table_name="analyzer_versions")
    op.drop_index(op.f("ix_analyzer_versions_analyzer_name"), table_name="analyzer_versions")
    op.drop_table("analyzer_versions")
