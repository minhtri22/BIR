from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Role = Literal["admin", "analyst", "reviewer", "viewer"]
ProjectStatus = Literal[
    "draft",
    "ingesting",
    "ready_for_analysis",
    "analyzing",
    "review_in_progress",
    "export_ready",
    "archived",
]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: Role


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class CsrfResponse(BaseModel):
    csrf_token: str


class AuthSessionResponse(BaseModel):
    user: UserOut
    csrf_token: str


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    organization_name: str | None = Field(default=None, max_length=180)
    legacy_system_name: str | None = Field(default=None, max_length=180)
    source_type: str | None = Field(default=None, max_length=80)
    snapshot_date: date | None = None


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    organization_name: str | None = Field(default=None, max_length=180)
    legacy_system_name: str | None = Field(default=None, max_length=180)
    source_type: str | None = Field(default=None, max_length=80)
    snapshot_date: date | None = None


class ProjectArchiveRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    organization_name: str | None
    legacy_system_name: str | None
    source_type: str | None
    snapshot_date: date | None
    status: ProjectStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    archive_reason: str | None


class SourceArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    original_path: str
    storage_path: str
    file_extension: str
    size_bytes: int
    sha256: str
    encoding: str
    line_count: int
    analysis_status: str
    candidate_count: int
    created_by: str
    created_at: datetime


class IngestionWarningOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    artifact_id: str | None
    original_path: str
    warning_code: str
    message: str
    created_by: str
    created_at: datetime


class SourceUploadResponse(BaseModel):
    project: ProjectOut
    artifacts: list[SourceArtifactOut]
    warnings: list[IngestionWarningOut]


class SourceContentLine(BaseModel):
    number: int
    escaped_html: str


class SourceContentResponse(BaseModel):
    artifact: SourceArtifactOut
    lines: list[SourceContentLine]


class AnalysisJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_ids: list[str] = Field(default_factory=list)
    configuration: dict[str, Any] = Field(default_factory=dict)


class AnalysisJobOut(BaseModel):
    id: str
    project_id: str
    analyzer_version_id: str
    analyzer_name: str
    analyzer_version: str
    extractor_kind: str
    pattern_set_hash: str
    configuration_hash: str
    configuration: dict[str, Any]
    status: str
    request_fingerprint: str
    requested_by: str
    requested_artifact_count: int
    attempt_no: int
    retry_of_job_id: str | None
    previous_project_status: str
    failure_code: str | None
    failure_message: str | None
    candidate_count: int
    gap_count: int
    question_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime


class BusinessStatementOut(BaseModel):
    id: str
    project_id: str
    analysis_job_id: str
    type: str
    pattern_id: str
    title: str
    statement_text: str
    structured_expression_json: dict[str, Any] | None
    scope_json: dict[str, Any]
    confidence: float
    status: str
    extraction_method: str
    analyzer_version_id: str
    primary_artifact_id: str
    primary_chunk_id: str
    candidate_identity_hash: str
    unresolved_count: int
    revision_no: int
    supersedes_id: str | None
    created_by: str | None
    created_by_kind: str
    created_at: datetime
    updated_at: datetime
    evidence_count: int


class EvidenceOut(BaseModel):
    id: str
    project_id: str
    analysis_job_id: str
    statement_id: str | None
    analysis_gap_id: str | None
    unresolved_question_id: str | None
    artifact_id: str
    artifact_sha256: str
    source_chunk_id: str
    start_line: int
    end_line: int
    excerpt: str
    excerpt_sha256: str
    relation_type: str
    extraction_method: str
    pattern_id: str
    analyzer_version_id: str
    created_by: str | None
    created_by_kind: str
    created_at: datetime


class AnalysisGapOut(BaseModel):
    id: str
    project_id: str
    analysis_job_id: str
    artifact_id: str | None
    source_chunk_id: str | None
    gap_type: str
    title: str
    description: str
    severity: str
    status: str
    analyzer_version_id: str
    identity_hash: str
    created_by: str | None
    created_by_kind: str
    created_at: datetime
    resolved_at: datetime | None
    resolution_note: str | None


class UnresolvedQuestionOut(BaseModel):
    id: str
    project_id: str
    analysis_job_id: str
    statement_id: str | None
    artifact_id: str | None
    source_chunk_id: str | None
    question_type: str
    question_text: str
    status: str
    priority: str
    analyzer_version_id: str
    identity_hash: str
    created_by: str | None
    created_by_kind: str
    created_at: datetime
    answered_at: datetime | None
    answer_text: str | None


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    actor_user_id: str | None
    project_id: str | None
    request_id: str | None
    payload: dict
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    database: str
    worker: str | None = None
