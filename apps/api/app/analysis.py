from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.app.audit import record_audit_event
from apps.api.app.config import Settings
from apps.api.app.ingestion import ArtifactIntegrityError, IngestionRejectedError, read_artifact_text
from apps.api.app.models import (
    AnalysisGap,
    AnalysisJob,
    AnalysisJobArtifact,
    AnalyzerVersion,
    BusinessStatement,
    Evidence,
    Project,
    SourceArtifact,
    SourceChunk,
    UnresolvedQuestion,
)
from apps.api.app.time import utc_now
from packages.domain.project_state import ProjectStateError, assert_project_transition
from packages.extraction.static import (
    STATIC_ANALYZER_NAME,
    STATIC_ANALYZER_VERSION,
    StaticExtractionConfigError,
    candidate_identity_hash,
    canonical_json,
    canonicalize_configuration,
    extract_from_chunks,
    generic_identity_hash,
    make_source_chunks,
)

ACTIVE_JOB_STATUSES = ("queued", "running")
TERMINAL_JOB_STATUSES = ("succeeded", "failed", "cancelled")
STABLE_ANALYSIS_PROJECT_STATUSES = ("ready_for_analysis", "review_in_progress", "export_ready")


class AnalysisError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class AnalysisConflictError(AnalysisError):
    pass


class AnalysisValidationError(AnalysisError):
    pass


class AnalysisNotFoundError(AnalysisError):
    pass


@dataclass(frozen=True)
class AnalysisJobDecision:
    job: AnalysisJob
    created: bool
    status_code: int


def create_analysis_job(
    db: Session,
    project: Project,
    *,
    artifact_ids: list[str] | None,
    configuration: dict[str, Any] | None,
    actor_user_id: str,
    actor_role: str,
    request_id: str | None,
) -> AnalysisJobDecision:
    if project.status == "archived":
        raise AnalysisConflictError("project_archived", "Archived projects are read-only.")

    canonical = _canonical_configuration(configuration)
    artifacts = _resolve_artifacts(db, project.id, artifact_ids)
    analyzer = _get_or_create_analyzer_version(db, canonical)
    request_fingerprint = _request_fingerprint(project.id, artifacts, analyzer)

    active_job = _active_project_job(db, project.id)
    if active_job is not None:
        raise AnalysisConflictError(
            "analysis_job_active",
            "Project already has an active analysis job.",
        )

    succeeded_job = _latest_job_for_status(db, project.id, request_fingerprint, "succeeded")
    if succeeded_job is not None:
        return AnalysisJobDecision(job=succeeded_job, created=False, status_code=200)

    latest_attempt = _latest_job_for_fingerprint(db, project.id, request_fingerprint)
    attempt_no = 1
    retry_of_job_id = None
    if latest_attempt is not None:
        if latest_attempt.status in ACTIVE_JOB_STATUSES:
            raise AnalysisConflictError("analysis_job_active", "Analysis request is already active.")
        if latest_attempt.status not in TERMINAL_JOB_STATUSES:
            raise AnalysisConflictError("analysis_job_not_retryable", "Analysis request is not retryable.")
        attempt_no = latest_attempt.attempt_no + 1
        if latest_attempt.status in {"failed", "cancelled"}:
            retry_of_job_id = latest_attempt.id

    return _insert_analysis_job(
        db,
        project,
        artifacts=artifacts,
        analyzer=analyzer,
        request_fingerprint=request_fingerprint,
        attempt_no=attempt_no,
        retry_of_job_id=retry_of_job_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        request_id=request_id,
    )


def retry_analysis_job(
    db: Session,
    project: Project,
    *,
    job_id: str,
    actor_user_id: str,
    actor_role: str,
    request_id: str | None,
) -> AnalysisJobDecision:
    if project.status == "archived":
        raise AnalysisConflictError("project_archived", "Archived projects are read-only.")

    target = db.get(AnalysisJob, job_id)
    if target is None or target.project_id != project.id:
        raise AnalysisNotFoundError("analysis_job_not_found", "Analysis job not found.")
    if target.status not in {"failed", "cancelled"}:
        raise AnalysisConflictError("analysis_job_not_retryable", "Only failed or cancelled jobs can be retried.")

    active_job = _active_project_job(db, project.id)
    if active_job is not None:
        raise AnalysisConflictError("analysis_job_active", "Project already has an active analysis job.")

    succeeded_job = _latest_job_for_status(db, project.id, target.request_fingerprint, "succeeded")
    if succeeded_job is not None:
        return AnalysisJobDecision(job=succeeded_job, created=False, status_code=200)

    analyzer = db.get(AnalyzerVersion, target.analyzer_version_id)
    if analyzer is None:
        raise AnalysisValidationError("analyzer_version_missing", "Analyzer version for retry is missing.")

    artifacts = _artifacts_for_job(db, target)
    if not artifacts:
        raise AnalysisValidationError("analysis_artifacts_missing", "Analysis job has no retryable artifacts.")

    latest_attempt = _latest_job_for_fingerprint(db, project.id, target.request_fingerprint)
    attempt_no = (latest_attempt.attempt_no + 1) if latest_attempt is not None else 1
    return _insert_analysis_job(
        db,
        project,
        artifacts=artifacts,
        analyzer=analyzer,
        request_fingerprint=target.request_fingerprint,
        attempt_no=attempt_no,
        retry_of_job_id=target.id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        request_id=request_id,
    )


def process_analysis_job_by_id(
    session_factory: Callable[[], Session],
    settings: Settings,
    job_id: str,
    request_id: str | None,
) -> None:
    with session_factory() as db:
        process_analysis_job(db, settings, job_id=job_id, request_id=request_id)


def process_analysis_job(
    db: Session,
    settings: Settings,
    *,
    job_id: str,
    request_id: str | None,
) -> None:
    job = db.get(AnalysisJob, job_id)
    if job is None or job.status != "queued":
        return

    try:
        _mark_job_running(db, job)
        _persist_analysis_outputs(db, settings, job_id, request_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        _record_analysis_failure(
            db,
            job_id=job_id,
            request_id=request_id,
            code=_failure_code(exc),
            message=_safe_failure_message(exc),
        )


def _insert_analysis_job(
    db: Session,
    project: Project,
    *,
    artifacts: list[SourceArtifact],
    analyzer: AnalyzerVersion,
    request_fingerprint: str,
    attempt_no: int,
    retry_of_job_id: str | None,
    actor_user_id: str,
    actor_role: str,
    request_id: str | None,
) -> AnalysisJobDecision:
    previous_status = (
        project.status if project.status in STABLE_ANALYSIS_PROJECT_STATUSES else "ready_for_analysis"
    )
    try:
        assert_project_transition(previous_status, "analyzing", actor_role, "start_analysis")
    except ProjectStateError as exc:
        raise AnalysisConflictError("invalid_project_state", str(exc)) from exc

    now = utc_now()
    project.status = "analyzing"
    project.updated_at = now
    job = AnalysisJob(
        project_id=project.id,
        analyzer_version_id=analyzer.id,
        status="queued",
        request_fingerprint=request_fingerprint,
        requested_by=actor_user_id,
        requested_artifact_count=len(artifacts),
        attempt_no=attempt_no,
        retry_of_job_id=retry_of_job_id,
        previous_project_status=previous_status,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.flush()

    for artifact in artifacts:
        artifact.analysis_status = "queued"
        db.add(
            AnalysisJobArtifact(
                job_id=job.id,
                artifact_id=artifact.id,
                artifact_sha256=artifact.sha256,
                status="queued",
                created_at=now,
            )
        )

    record_audit_event(
        db,
        "ANALYSIS_STARTED",
        actor_user_id=actor_user_id,
        project_id=project.id,
        request_id=request_id,
        payload={
            "analysis_job_id": job.id,
            "request_fingerprint": request_fingerprint,
            "attempt_no": attempt_no,
            "artifact_count": len(artifacts),
            "previous_status": previous_status,
            "analyzer_name": analyzer.analyzer_name,
            "analyzer_version": analyzer.analyzer_version,
            "configuration_hash": analyzer.configuration_hash,
        },
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AnalysisConflictError("analysis_job_conflict", "Analysis job conflicts with an existing request.") from exc
    db.refresh(job)
    return AnalysisJobDecision(job=job, created=True, status_code=201)


def _mark_job_running(db: Session, job: AnalysisJob) -> None:
    now = utc_now()
    job.status = "running"
    job.started_at = now
    job.updated_at = now
    for row in db.scalars(select(AnalysisJobArtifact).where(AnalysisJobArtifact.job_id == job.id)):
        row.status = "running"
        artifact = db.get(SourceArtifact, row.artifact_id)
        if artifact is not None:
            artifact.analysis_status = "analyzing"
    db.commit()


def _persist_analysis_outputs(db: Session, settings: Settings, job_id: str, request_id: str | None) -> None:
    job = db.get(AnalysisJob, job_id)
    if job is None:
        raise AnalysisValidationError("analysis_job_missing", "Analysis job no longer exists.")
    analyzer = db.get(AnalyzerVersion, job.analyzer_version_id)
    project = db.get(Project, job.project_id)
    if analyzer is None or project is None:
        raise AnalysisValidationError("analysis_context_missing", "Analysis context is missing.")

    job_artifacts = list(
        db.scalars(
            select(AnalysisJobArtifact)
            .where(AnalysisJobArtifact.job_id == job.id)
            .order_by(AnalysisJobArtifact.artifact_id.asc())
        )
    )
    candidate_count = 0
    gap_count = 0
    question_count = 0
    seen_candidates: set[str] = set()
    seen_gaps: set[str] = set()
    seen_questions: set[str] = set()

    for job_artifact in job_artifacts:
        artifact = db.get(SourceArtifact, job_artifact.artifact_id)
        if artifact is None:
            raise AnalysisValidationError("analysis_artifact_missing", "Analysis artifact is missing.")
        if artifact.sha256 != job_artifact.artifact_sha256:
            raise AnalysisValidationError(
                "artifact_hash_changed",
                "Artifact hash no longer matches the analysis request.",
            )

        text = read_artifact_text(artifact, settings)
        chunk_drafts = make_source_chunks(text, analyzer.configuration_json)
        chunk_rows = _persist_chunks(db, job, analyzer, artifact, chunk_drafts)
        extraction_by_chunk = extract_from_chunks(chunk_drafts, analyzer.configuration_json)
        artifact_candidate_count = 0
        artifact_gap_count = 0
        artifact_question_count = 0

        for chunk_draft in chunk_drafts:
            chunk_row = chunk_rows[chunk_draft.chunk_index]
            draft = extraction_by_chunk[chunk_draft.chunk_index]

            for candidate in draft.candidates:
                identity = candidate_identity_hash(
                    artifact_sha256=artifact.sha256,
                    analyzer_name=analyzer.analyzer_name,
                    analyzer_version=analyzer.analyzer_version,
                    configuration_hash=analyzer.configuration_hash,
                    pattern_id=candidate.pattern_id,
                    statement_type=candidate.type,
                    scope=candidate.scope,
                    structured_expression=candidate.structured_expression,
                    evidence_ranges=[
                        {
                            "artifact_sha256": artifact.sha256,
                            "start_line": candidate.evidence.start_line,
                            "end_line": candidate.evidence.end_line,
                            "relation_type": candidate.evidence.relation_type,
                        }
                    ],
                )
                if identity in seen_candidates:
                    continue
                seen_candidates.add(identity)
                statement = BusinessStatement(
                    project_id=job.project_id,
                    analysis_job_id=job.id,
                    type=candidate.type,
                    pattern_id=candidate.pattern_id,
                    title=candidate.title,
                    statement_text=candidate.statement_text,
                    structured_expression_json=candidate.structured_expression,
                    scope_json=candidate.scope,
                    confidence=candidate.confidence,
                    status="candidate",
                    extraction_method="static",
                    analyzer_version_id=analyzer.id,
                    primary_artifact_id=artifact.id,
                    primary_chunk_id=chunk_row.id,
                    candidate_identity_hash=identity,
                    unresolved_count=0,
                    revision_no=1,
                    created_by=None,
                    created_by_kind="system",
                )
                db.add(statement)
                db.flush()
                db.add(
                    _evidence_row(
                        job=job,
                        analyzer=analyzer,
                        artifact=artifact,
                        chunk=chunk_row,
                        pattern_id=candidate.pattern_id,
                        start_line=candidate.evidence.start_line,
                        end_line=candidate.evidence.end_line,
                        excerpt=candidate.evidence.excerpt,
                        relation_type=candidate.evidence.relation_type,
                        statement_id=statement.id,
                    )
                )
                candidate_count += 1
                artifact_candidate_count += 1

            for gap in draft.gaps:
                identity = _gap_identity(analyzer, artifact, gap.identity_source)
                if identity in seen_gaps:
                    continue
                seen_gaps.add(identity)
                gap_row = AnalysisGap(
                    project_id=job.project_id,
                    analysis_job_id=job.id,
                    artifact_id=artifact.id,
                    source_chunk_id=chunk_row.id,
                    gap_type=gap.gap_type,
                    title=gap.title,
                    description=gap.description,
                    severity=gap.severity,
                    status="open",
                    analyzer_version_id=analyzer.id,
                    identity_hash=identity,
                    created_by=None,
                    created_by_kind="system",
                )
                db.add(gap_row)
                db.flush()
                db.add(
                    _evidence_row(
                        job=job,
                        analyzer=analyzer,
                        artifact=artifact,
                        chunk=chunk_row,
                        pattern_id=gap.pattern_id,
                        start_line=gap.evidence.start_line,
                        end_line=gap.evidence.end_line,
                        excerpt=gap.evidence.excerpt,
                        relation_type="identifies_gap",
                        analysis_gap_id=gap_row.id,
                    )
                )
                gap_count += 1
                artifact_gap_count += 1

            for question in draft.questions:
                identity = _question_identity(analyzer, artifact, question.identity_source)
                if identity in seen_questions:
                    continue
                seen_questions.add(identity)
                question_row = UnresolvedQuestion(
                    project_id=job.project_id,
                    analysis_job_id=job.id,
                    statement_id=None,
                    artifact_id=artifact.id,
                    source_chunk_id=chunk_row.id,
                    question_type=question.question_type,
                    question_text=question.question_text,
                    status="open",
                    priority=question.priority,
                    analyzer_version_id=analyzer.id,
                    identity_hash=identity,
                    created_by=None,
                    created_by_kind="system",
                )
                db.add(question_row)
                db.flush()
                db.add(
                    _evidence_row(
                        job=job,
                        analyzer=analyzer,
                        artifact=artifact,
                        chunk=chunk_row,
                        pattern_id=question.pattern_id,
                        start_line=question.evidence.start_line,
                        end_line=question.evidence.end_line,
                        excerpt=question.evidence.excerpt,
                        relation_type="raises_question",
                        unresolved_question_id=question_row.id,
                    )
                )
                question_count += 1
                artifact_question_count += 1

        if chunk_rows and artifact_candidate_count == 0 and artifact_gap_count == 0 and artifact_question_count == 0:
            first_chunk = chunk_rows[min(chunk_rows)]
            first_line = first_chunk.content.splitlines()[0]
            evidence = _evidence_row(
                job=job,
                analyzer=analyzer,
                artifact=artifact,
                chunk=first_chunk,
                pattern_id="comment_adjacent_logic",
                start_line=first_chunk.start_line,
                end_line=first_chunk.start_line,
                excerpt=first_line,
                relation_type="identifies_gap",
            )
            identity = _gap_identity(
                analyzer,
                artifact,
                {
                    "pattern_id": "insufficient_static_signals",
                    "range": [first_chunk.start_line, first_chunk.start_line],
                },
            )
            gap_row = AnalysisGap(
                project_id=job.project_id,
                analysis_job_id=job.id,
                artifact_id=artifact.id,
                source_chunk_id=first_chunk.id,
                gap_type="insufficient_evidence",
                title="No static business candidate found",
                description="Static extraction did not find an evidence-backed business statement in this artifact.",
                severity="low",
                status="open",
                analyzer_version_id=analyzer.id,
                identity_hash=identity,
                created_by=None,
                created_by_kind="system",
            )
            db.add(gap_row)
            db.flush()
            evidence.analysis_gap_id = gap_row.id
            db.add(evidence)
            gap_count += 1

        db.flush()
        artifact.analysis_status = "analyzed"
        artifact.candidate_count = int(
            db.scalar(
                select(func.count())
                .select_from(BusinessStatement)
                .where(BusinessStatement.primary_artifact_id == artifact.id)
            )
            or 0
        )
        job_artifact.status = "succeeded"

    assert_project_transition("analyzing", "review_in_progress", "system", "complete_analysis")
    now = utc_now()
    project.status = "review_in_progress"
    project.updated_at = now
    job.status = "succeeded"
    job.candidate_count = candidate_count
    job.gap_count = gap_count
    job.question_count = question_count
    job.completed_at = now
    job.updated_at = now
    record_audit_event(
        db,
        "ANALYSIS_COMPLETED",
        actor_user_id=job.requested_by,
        project_id=job.project_id,
        request_id=request_id,
        payload={
            "analysis_job_id": job.id,
            "request_fingerprint": job.request_fingerprint,
            "attempt_no": job.attempt_no,
            "candidate_count": candidate_count,
            "gap_count": gap_count,
            "question_count": question_count,
        },
    )


def _persist_chunks(
    db: Session,
    job: AnalysisJob,
    analyzer: AnalyzerVersion,
    artifact: SourceArtifact,
    chunk_drafts,
) -> dict[int, SourceChunk]:
    rows: dict[int, SourceChunk] = {}
    for draft in chunk_drafts:
        row = SourceChunk(
            project_id=job.project_id,
            artifact_id=artifact.id,
            analysis_job_id=job.id,
            analyzer_version_id=analyzer.id,
            chunk_index=draft.chunk_index,
            start_line=draft.start_line,
            end_line=draft.end_line,
            line_count=draft.line_count,
            content=draft.content,
            content_hash=draft.content_hash,
            chunk_type=draft.chunk_type,
        )
        db.add(row)
        db.flush()
        rows[draft.chunk_index] = row
    return rows


def _evidence_row(
    *,
    job: AnalysisJob,
    analyzer: AnalyzerVersion,
    artifact: SourceArtifact,
    chunk: SourceChunk,
    pattern_id: str,
    start_line: int,
    end_line: int,
    excerpt: str,
    relation_type: str,
    statement_id: str | None = None,
    analysis_gap_id: str | None = None,
    unresolved_question_id: str | None = None,
) -> Evidence:
    return Evidence(
        project_id=job.project_id,
        analysis_job_id=job.id,
        statement_id=statement_id,
        analysis_gap_id=analysis_gap_id,
        unresolved_question_id=unresolved_question_id,
        artifact_id=artifact.id,
        artifact_sha256=artifact.sha256,
        source_chunk_id=chunk.id,
        start_line=start_line,
        end_line=end_line,
        excerpt=excerpt,
        excerpt_sha256=hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
        relation_type=relation_type,
        extraction_method="static",
        pattern_id=pattern_id,
        analyzer_version_id=analyzer.id,
        created_by=None,
        created_by_kind="system",
    )


def _record_analysis_failure(
    db: Session,
    *,
    job_id: str,
    request_id: str | None,
    code: str,
    message: str,
) -> None:
    try:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            return
        project = db.get(Project, job.project_id)
        now = utc_now()
        job.status = "failed"
        job.failure_code = code
        job.failure_message = message
        job.completed_at = now
        job.updated_at = now

        for row in db.scalars(select(AnalysisJobArtifact).where(AnalysisJobArtifact.job_id == job.id)):
            row.status = "failed"
            artifact = db.get(SourceArtifact, row.artifact_id)
            if artifact is not None:
                artifact.analysis_status = "analysis_failed"

        if project is not None and project.status != "archived":
            target_status = (
                job.previous_project_status
                if job.previous_project_status in STABLE_ANALYSIS_PROJECT_STATUSES
                else "ready_for_analysis"
            )
            active_other = db.scalar(
                select(func.count())
                .select_from(AnalysisJob)
                .where(
                    AnalysisJob.project_id == job.project_id,
                    AnalysisJob.id != job.id,
                    AnalysisJob.status.in_(ACTIVE_JOB_STATUSES),
                )
            )
            if project.status == "analyzing" and not active_other:
                assert_project_transition("analyzing", target_status, "system", "fail_or_cancel_analysis")
                project.status = target_status
                project.updated_at = now

        record_audit_event(
            db,
            "ANALYSIS_FAILED_OR_CANCELLED",
            actor_user_id=job.requested_by,
            project_id=job.project_id,
            request_id=request_id,
            payload={
                "analysis_job_id": job.id,
                "request_fingerprint": job.request_fingerprint,
                "attempt_no": job.attempt_no,
                "code": code,
                "message": message,
                "previous_status": job.previous_project_status,
            },
        )
        db.commit()
    except Exception:
        db.rollback()


def _canonical_configuration(configuration: dict[str, Any] | None):
    try:
        return canonicalize_configuration(configuration)
    except StaticExtractionConfigError as exc:
        raise AnalysisValidationError(exc.code, exc.message) from exc


def _get_or_create_analyzer_version(db: Session, canonical) -> AnalyzerVersion:
    analyzer = db.scalar(
        select(AnalyzerVersion).where(
            AnalyzerVersion.analyzer_name == STATIC_ANALYZER_NAME,
            AnalyzerVersion.analyzer_version == STATIC_ANALYZER_VERSION,
            AnalyzerVersion.configuration_hash == canonical.configuration_hash,
        )
    )
    if analyzer is not None:
        return analyzer
    analyzer = AnalyzerVersion(
        analyzer_name=STATIC_ANALYZER_NAME,
        analyzer_version=STATIC_ANALYZER_VERSION,
        extractor_kind="static",
        configuration_json=canonical.configuration,
        configuration_hash=canonical.configuration_hash,
        pattern_set_hash=canonical.pattern_set_hash,
    )
    db.add(analyzer)
    db.flush()
    return analyzer


def _resolve_artifacts(db: Session, project_id: str, artifact_ids: list[str] | None) -> list[SourceArtifact]:
    if artifact_ids:
        if len(set(artifact_ids)) != len(artifact_ids):
            raise AnalysisValidationError("duplicate_artifact_id", "Duplicate artifact IDs are not allowed.")
        rows = {
            artifact.id: artifact
            for artifact in db.scalars(
                select(SourceArtifact).where(
                    SourceArtifact.project_id == project_id,
                    SourceArtifact.id.in_(artifact_ids),
                )
            )
        }
        missing = [artifact_id for artifact_id in artifact_ids if artifact_id not in rows]
        if missing:
            raise AnalysisValidationError("artifact_not_found", "Requested artifact was not found.")
        artifacts = [rows[artifact_id] for artifact_id in artifact_ids]
    else:
        artifacts = list(
            db.scalars(
                select(SourceArtifact)
                .where(SourceArtifact.project_id == project_id)
                .order_by(SourceArtifact.created_at.asc(), SourceArtifact.original_path.asc())
            )
        )
    if not artifacts:
        raise AnalysisValidationError("no_artifacts", "Project has no source artifacts to analyze.")
    return artifacts


def _artifacts_for_job(db: Session, job: AnalysisJob) -> list[SourceArtifact]:
    job_artifacts = list(
        db.scalars(
            select(AnalysisJobArtifact)
            .where(AnalysisJobArtifact.job_id == job.id)
            .order_by(AnalysisJobArtifact.artifact_id.asc())
        )
    )
    artifacts: list[SourceArtifact] = []
    for job_artifact in job_artifacts:
        artifact = db.get(SourceArtifact, job_artifact.artifact_id)
        if artifact is not None:
            artifacts.append(artifact)
    return artifacts


def _request_fingerprint(
    project_id: str,
    artifacts: list[SourceArtifact],
    analyzer: AnalyzerVersion,
) -> str:
    payload = {
        "project_id": project_id,
        "artifact_sha256_values": sorted(artifact.sha256 for artifact in artifacts),
        "analyzer_name": analyzer.analyzer_name,
        "analyzer_version": analyzer.analyzer_version,
        "pattern_set_hash": analyzer.pattern_set_hash,
        "configuration_hash": analyzer.configuration_hash,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _active_project_job(db: Session, project_id: str) -> AnalysisJob | None:
    return db.scalar(
        select(AnalysisJob)
        .where(AnalysisJob.project_id == project_id, AnalysisJob.status.in_(ACTIVE_JOB_STATUSES))
        .order_by(AnalysisJob.created_at.desc())
    )


def _latest_job_for_fingerprint(
    db: Session,
    project_id: str,
    request_fingerprint: str,
) -> AnalysisJob | None:
    return db.scalar(
        select(AnalysisJob)
        .where(
            AnalysisJob.project_id == project_id,
            AnalysisJob.request_fingerprint == request_fingerprint,
        )
        .order_by(AnalysisJob.attempt_no.desc())
    )


def _latest_job_for_status(
    db: Session,
    project_id: str,
    request_fingerprint: str,
    status: str,
) -> AnalysisJob | None:
    return db.scalar(
        select(AnalysisJob)
        .where(
            AnalysisJob.project_id == project_id,
            AnalysisJob.request_fingerprint == request_fingerprint,
            AnalysisJob.status == status,
        )
        .order_by(AnalysisJob.attempt_no.desc())
    )


def _gap_identity(
    analyzer: AnalyzerVersion,
    artifact: SourceArtifact,
    source: dict[str, Any],
) -> str:
    return generic_identity_hash(
        "analysis_gap",
        {
            "artifact_sha256": artifact.sha256,
            "analyzer_name": analyzer.analyzer_name,
            "analyzer_version": analyzer.analyzer_version,
            "configuration_hash": analyzer.configuration_hash,
            "source": source,
        },
    )


def _question_identity(
    analyzer: AnalyzerVersion,
    artifact: SourceArtifact,
    source: dict[str, Any],
) -> str:
    return generic_identity_hash(
        "unresolved_question",
        {
            "artifact_sha256": artifact.sha256,
            "analyzer_name": analyzer.analyzer_name,
            "analyzer_version": analyzer.analyzer_version,
            "configuration_hash": analyzer.configuration_hash,
            "source": source,
        },
    )


def _failure_code(exc: Exception) -> str:
    if isinstance(exc, ArtifactIntegrityError):
        return exc.code
    if isinstance(exc, IngestionRejectedError):
        return exc.code
    if isinstance(exc, AnalysisError):
        return exc.code
    if isinstance(exc, ProjectStateError):
        return "invalid_project_state"
    return "analysis_processing_failed"


def _safe_failure_message(exc: Exception) -> str:
    if isinstance(exc, (ArtifactIntegrityError, IngestionRejectedError, AnalysisError)):
        return exc.message
    if isinstance(exc, ProjectStateError):
        return str(exc)
    return exc.__class__.__name__
