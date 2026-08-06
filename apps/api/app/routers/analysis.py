from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.app.analysis import (
    AnalysisConflictError,
    AnalysisNotFoundError,
    AnalysisValidationError,
    create_analysis_job,
    process_analysis_job_by_id,
    retry_analysis_job,
)
from apps.api.app.config import Settings
from apps.api.app.dependencies import AuthContext, get_current_context, get_db, get_settings, require_roles
from apps.api.app.models import (
    AnalysisGap,
    AnalysisJob,
    AnalyzerVersion,
    BusinessStatement,
    Evidence,
    Project,
    UnresolvedQuestion,
)
from apps.api.app.schemas import (
    AnalysisGapOut,
    AnalysisJobCreate,
    AnalysisJobOut,
    BusinessStatementOut,
    EvidenceOut,
    UnresolvedQuestionOut,
)

router = APIRouter(prefix="/projects/{project_id}", tags=["analysis"])


def _project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _job_or_404(db: Session, project_id: str, job_id: str) -> AnalysisJob:
    job = db.get(AnalysisJob, job_id)
    if job is None or job.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Analysis job not found")
    return job


def _statement_or_404(db: Session, project_id: str, statement_id: str) -> BusinessStatement:
    statement = db.get(BusinessStatement, statement_id)
    if statement is None or statement.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Statement not found")
    return statement


@router.post("/analysis-jobs", response_model=AnalysisJobOut)
def create_project_analysis_job(
    project_id: str,
    payload: AnalysisJobCreate,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    context: AuthContext = Depends(require_roles("admin", "analyst", require_csrf_token=True)),
) -> dict:
    project = _project_or_404(db, project_id)
    try:
        decision = create_analysis_job(
            db,
            project,
            artifact_ids=payload.artifact_ids or None,
            configuration=payload.configuration,
            actor_user_id=context.user.id,
            actor_role=context.user.role,
            request_id=getattr(request.state, "request_id", None),
        )
    except AnalysisValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except AnalysisConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=exc.message) from exc

    response.status_code = decision.status_code
    if decision.created:
        background_tasks.add_task(
            process_analysis_job_by_id,
            request.app.state.SessionLocal,
            settings,
            decision.job.id,
            getattr(request.state, "request_id", None),
        )
    return _job_response(db, decision.job)


@router.post("/analysis-jobs/{job_id}/retry", response_model=AnalysisJobOut)
def retry_project_analysis_job(
    project_id: str,
    job_id: str,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    context: AuthContext = Depends(require_roles("admin", "analyst", require_csrf_token=True)),
) -> dict:
    project = _project_or_404(db, project_id)
    try:
        decision = retry_analysis_job(
            db,
            project,
            job_id=job_id,
            actor_user_id=context.user.id,
            actor_role=context.user.role,
            request_id=getattr(request.state, "request_id", None),
        )
    except AnalysisNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except AnalysisValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except AnalysisConflictError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=exc.message) from exc

    response.status_code = decision.status_code
    if decision.created:
        background_tasks.add_task(
            process_analysis_job_by_id,
            request.app.state.SessionLocal,
            settings,
            decision.job.id,
            getattr(request.state, "request_id", None),
        )
    return _job_response(db, decision.job)


@router.get("/analysis-jobs", response_model=list[AnalysisJobOut])
def list_project_analysis_jobs(
    project_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(get_current_context),
) -> list[dict]:
    _ = context
    _project_or_404(db, project_id)
    bounded_limit = max(1, min(limit, 100))
    query = select(AnalysisJob).where(AnalysisJob.project_id == project_id)
    if status_filter:
        query = query.where(AnalysisJob.status == status_filter)
    jobs = list(
        db.scalars(query.order_by(AnalysisJob.created_at.desc()).limit(bounded_limit).offset(max(offset, 0))).all()
    )
    return [_job_response(db, job) for job in jobs]


@router.get("/analysis-jobs/{job_id}", response_model=AnalysisJobOut)
def get_project_analysis_job(
    project_id: str,
    job_id: str,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(get_current_context),
) -> dict:
    _ = context
    _project_or_404(db, project_id)
    return _job_response(db, _job_or_404(db, project_id, job_id))


@router.get("/statements", response_model=list[BusinessStatementOut])
def list_candidate_statements(
    project_id: str,
    status_filter: str = Query(default="candidate", alias="status"),
    type_filter: str | None = Query(default=None, alias="type"),
    artifact_id: str | None = None,
    confidence_min: float | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(get_current_context),
) -> list[dict]:
    _ = context
    _project_or_404(db, project_id)
    bounded_limit = max(1, min(limit, 100))
    query = select(BusinessStatement).where(
        BusinessStatement.project_id == project_id,
        BusinessStatement.status == status_filter,
    )
    if type_filter:
        query = query.where(BusinessStatement.type == type_filter)
    if artifact_id:
        query = query.where(BusinessStatement.primary_artifact_id == artifact_id)
    if confidence_min is not None:
        query = query.where(BusinessStatement.confidence >= confidence_min)
    statements = list(
        db.scalars(
            query.order_by(BusinessStatement.created_at.desc(), BusinessStatement.id.asc())
            .limit(bounded_limit)
            .offset(max(offset, 0))
        ).all()
    )
    return [_statement_response(db, statement) for statement in statements]


@router.get("/statements/{statement_id}", response_model=BusinessStatementOut)
def get_candidate_statement(
    project_id: str,
    statement_id: str,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(get_current_context),
) -> dict:
    _ = context
    _project_or_404(db, project_id)
    return _statement_response(db, _statement_or_404(db, project_id, statement_id))


@router.get("/statements/{statement_id}/evidence", response_model=list[EvidenceOut])
def list_statement_evidence(
    project_id: str,
    statement_id: str,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(get_current_context),
) -> list[Evidence]:
    _ = context
    _project_or_404(db, project_id)
    _statement_or_404(db, project_id, statement_id)
    return list(
        db.scalars(
            select(Evidence)
            .where(Evidence.project_id == project_id, Evidence.statement_id == statement_id)
            .order_by(Evidence.start_line.asc(), Evidence.created_at.asc())
        ).all()
    )


@router.get("/analysis-gaps", response_model=list[AnalysisGapOut])
def list_analysis_gaps(
    project_id: str,
    status_filter: str = Query(default="open", alias="status"),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(get_current_context),
) -> list[AnalysisGap]:
    _ = context
    _project_or_404(db, project_id)
    bounded_limit = max(1, min(limit, 100))
    return list(
        db.scalars(
            select(AnalysisGap)
            .where(AnalysisGap.project_id == project_id, AnalysisGap.status == status_filter)
            .order_by(AnalysisGap.created_at.desc())
            .limit(bounded_limit)
            .offset(max(offset, 0))
        ).all()
    )


@router.get("/unresolved-questions", response_model=list[UnresolvedQuestionOut])
def list_unresolved_questions(
    project_id: str,
    status_filter: str = Query(default="open", alias="status"),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(get_current_context),
) -> list[UnresolvedQuestion]:
    _ = context
    _project_or_404(db, project_id)
    bounded_limit = max(1, min(limit, 100))
    return list(
        db.scalars(
            select(UnresolvedQuestion)
            .where(UnresolvedQuestion.project_id == project_id, UnresolvedQuestion.status == status_filter)
            .order_by(UnresolvedQuestion.created_at.desc())
            .limit(bounded_limit)
            .offset(max(offset, 0))
        ).all()
    )


def _job_response(db: Session, job: AnalysisJob) -> dict:
    analyzer = db.get(AnalyzerVersion, job.analyzer_version_id)
    if analyzer is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Analyzer version missing")
    return {
        "id": job.id,
        "project_id": job.project_id,
        "analyzer_version_id": job.analyzer_version_id,
        "analyzer_name": analyzer.analyzer_name,
        "analyzer_version": analyzer.analyzer_version,
        "extractor_kind": analyzer.extractor_kind,
        "pattern_set_hash": analyzer.pattern_set_hash,
        "configuration_hash": analyzer.configuration_hash,
        "configuration": analyzer.configuration_json,
        "status": job.status,
        "request_fingerprint": job.request_fingerprint,
        "requested_by": job.requested_by,
        "requested_artifact_count": job.requested_artifact_count,
        "attempt_no": job.attempt_no,
        "retry_of_job_id": job.retry_of_job_id,
        "previous_project_status": job.previous_project_status,
        "failure_code": job.failure_code,
        "failure_message": job.failure_message,
        "candidate_count": job.candidate_count,
        "gap_count": job.gap_count,
        "question_count": job.question_count,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "updated_at": job.updated_at,
    }


def _statement_response(db: Session, statement: BusinessStatement) -> dict:
    evidence_count = int(
        db.scalar(
            select(func.count()).select_from(Evidence).where(Evidence.statement_id == statement.id)
        )
        or 0
    )
    return {
        "id": statement.id,
        "project_id": statement.project_id,
        "analysis_job_id": statement.analysis_job_id,
        "type": statement.type,
        "pattern_id": statement.pattern_id,
        "title": statement.title,
        "statement_text": statement.statement_text,
        "structured_expression_json": statement.structured_expression_json,
        "scope_json": statement.scope_json,
        "confidence": statement.confidence,
        "status": statement.status,
        "extraction_method": statement.extraction_method,
        "analyzer_version_id": statement.analyzer_version_id,
        "primary_artifact_id": statement.primary_artifact_id,
        "primary_chunk_id": statement.primary_chunk_id,
        "candidate_identity_hash": statement.candidate_identity_hash,
        "unresolved_count": statement.unresolved_count,
        "revision_no": statement.revision_no,
        "supersedes_id": statement.supersedes_id,
        "created_by": statement.created_by,
        "created_by_kind": statement.created_by_kind,
        "created_at": statement.created_at,
        "updated_at": statement.updated_at,
        "evidence_count": evidence_count,
    }
