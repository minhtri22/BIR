from __future__ import annotations

import uuid

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.database import Base
from apps.api.app.time import utc_now


def new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)

    sessions: Mapped[list[SessionRecord]] = relationship(back_populates="user")


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)
    last_seen_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)
    idle_expires_at: Mapped[object] = mapped_column(DateTime, nullable=False)
    absolute_expires_at: Mapped[object] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class CsrfNonce(Base):
    __tablename__ = "csrf_nonces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)
    expires_at: Mapped[object] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)


class LoginRateLimit(Base):
    __tablename__ = "login_rate_limits"

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_started_at: Mapped[object] = mapped_column(DateTime, nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    legacy_system_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    snapshot_date: Mapped[object | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)
    archived_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    archive_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class SourceArtifact(Base):
    __tablename__ = "source_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    file_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    encoding: Mapped[str] = mapped_column(String(40), nullable=False)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
    analysis_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_analyzed")
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)


class IngestionWarning(Base):
    __tablename__ = "ingestion_warnings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_artifacts.id"),
        nullable=True,
        index=True,
    )
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    warning_code: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)


class AnalyzerVersion(Base):
    __tablename__ = "analyzer_versions"
    __table_args__ = (
        UniqueConstraint(
            "analyzer_name",
            "analyzer_version",
            "configuration_hash",
            name="uq_analyzer_versions_identity",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    analyzer_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    analyzer_version: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    extractor_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    configuration_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    pattern_set_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "request_fingerprint",
            "attempt_no",
            name="uq_analysis_jobs_project_request_attempt",
        ),
        CheckConstraint("requested_artifact_count >= 1", name="ck_analysis_jobs_artifact_count"),
        CheckConstraint("attempt_no >= 1", name="ck_analysis_jobs_attempt_no"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    analyzer_version_id: Mapped[str] = mapped_column(
        ForeignKey("analyzer_versions.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    requested_artifact_count: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    retry_of_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("analysis_jobs.id"),
        nullable=True,
        index=True,
    )
    previous_project_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ready_for_analysis",
    )
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False, index=True)
    started_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)


class AnalysisJobArtifact(Base):
    __tablename__ = "analysis_job_artifacts"

    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id"), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("source_artifacts.id"), primary_key=True, index=True)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)


class SourceChunk(Base):
    __tablename__ = "source_chunks"
    __table_args__ = (
        UniqueConstraint(
            "analysis_job_id",
            "artifact_id",
            "chunk_index",
            name="uq_source_chunks_job_artifact_index",
        ),
        UniqueConstraint(
            "analysis_job_id",
            "artifact_id",
            "start_line",
            "end_line",
            "content_hash",
            name="uq_source_chunks_job_artifact_range_hash",
        ),
        CheckConstraint("start_line >= 1", name="ck_source_chunks_start_line"),
        CheckConstraint("end_line >= start_line", name="ck_source_chunks_end_line"),
        CheckConstraint("line_count >= 1", name="ck_source_chunks_line_count"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("source_artifacts.id"), nullable=False, index=True)
    analysis_job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id"), nullable=False, index=True)
    analyzer_version_id: Mapped[str] = mapped_column(
        ForeignKey("analyzer_versions.id"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chunk_type: Mapped[str] = mapped_column(String(32), nullable=False, default="line_window", index=True)
    parent_chunk_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_chunks.id"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)


class BusinessStatement(Base):
    __tablename__ = "business_statements"
    __table_args__ = (
        UniqueConstraint(
            "analysis_job_id",
            "candidate_identity_hash",
            name="uq_business_statements_candidate_identity",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_business_statements_confidence"),
        CheckConstraint("unresolved_count >= 0", name="ck_business_statements_unresolved_count"),
        CheckConstraint("revision_no >= 1", name="ck_business_statements_revision_no"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    analysis_job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    pattern_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    statement_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_expression_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scope_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="candidate", index=True)
    extraction_method: Mapped[str] = mapped_column(String(32), nullable=False, default="static", index=True)
    analyzer_version_id: Mapped[str] = mapped_column(
        ForeignKey("analyzer_versions.id"),
        nullable=False,
        index=True,
    )
    primary_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("source_artifacts.id"),
        nullable=False,
        index=True,
    )
    primary_chunk_id: Mapped[str] = mapped_column(ForeignKey("source_chunks.id"), nullable=False, index=True)
    candidate_identity_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    unresolved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("business_statements.id"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_by_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="system", index=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False, index=True)
    updated_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False)


class AnalysisGap(Base):
    __tablename__ = "analysis_gaps"
    __table_args__ = (
        UniqueConstraint(
            "analysis_job_id",
            "identity_hash",
            name="uq_analysis_gaps_identity",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    analysis_job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id"), nullable=False, index=True)
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("source_artifacts.id"), nullable=True, index=True)
    source_chunk_id: Mapped[str | None] = mapped_column(ForeignKey("source_chunks.id"), nullable=True, index=True)
    gap_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    analyzer_version_id: Mapped[str] = mapped_column(
        ForeignKey("analyzer_versions.id"),
        nullable=False,
        index=True,
    )
    identity_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_by_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="system", index=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False, index=True)
    resolved_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class UnresolvedQuestion(Base):
    __tablename__ = "unresolved_questions"
    __table_args__ = (
        UniqueConstraint(
            "analysis_job_id",
            "identity_hash",
            name="uq_unresolved_questions_identity",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    analysis_job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id"), nullable=False, index=True)
    statement_id: Mapped[str | None] = mapped_column(
        ForeignKey("business_statements.id"),
        nullable=True,
        index=True,
    )
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("source_artifacts.id"), nullable=True, index=True)
    source_chunk_id: Mapped[str | None] = mapped_column(ForeignKey("source_chunks.id"), nullable=True, index=True)
    question_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", index=True)
    analyzer_version_id: Mapped[str] = mapped_column(
        ForeignKey("analyzer_versions.id"),
        nullable=False,
        index=True,
    )
    identity_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_by_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="system", index=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False, index=True)
    answered_at: Mapped[object | None] = mapped_column(DateTime, nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(
            "((CASE WHEN statement_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN analysis_gap_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN unresolved_question_id IS NOT NULL THEN 1 ELSE 0 END)) = 1",
            name="ck_evidence_exactly_one_target",
        ),
        CheckConstraint("start_line >= 1", name="ck_evidence_start_line"),
        CheckConstraint("end_line >= start_line", name="ck_evidence_end_line"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    analysis_job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id"), nullable=False, index=True)
    statement_id: Mapped[str | None] = mapped_column(
        ForeignKey("business_statements.id"),
        nullable=True,
        index=True,
    )
    analysis_gap_id: Mapped[str | None] = mapped_column(
        ForeignKey("analysis_gaps.id"),
        nullable=True,
        index=True,
    )
    unresolved_question_id: Mapped[str | None] = mapped_column(
        ForeignKey("unresolved_questions.id"),
        nullable=True,
        index=True,
    )
    artifact_id: Mapped[str] = mapped_column(ForeignKey("source_artifacts.id"), nullable=False, index=True)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_chunk_id: Mapped[str] = mapped_column(ForeignKey("source_chunks.id"), nullable=False, index=True)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False, default="supports", index=True)
    extraction_method: Mapped[str] = mapped_column(String(32), nullable=False, default="static", index=True)
    pattern_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    analyzer_version_id: Mapped[str] = mapped_column(
        ForeignKey("analyzer_versions.id"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_by_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="system", index=True)
    created_at: Mapped[object] = mapped_column(DateTime, default=utc_now, nullable=False, index=True)
