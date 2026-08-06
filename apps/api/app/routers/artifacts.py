from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.audit import record_audit_event
from apps.api.app.config import Settings
from apps.api.app.dependencies import AuthContext, get_current_context, get_db, get_settings, require_roles
from apps.api.app.ingestion import (
    ArtifactIntegrityError,
    IngestionRejectedError,
    escaped_source_lines,
    ingest_source_upload,
    read_artifact_text,
    record_rejected_upload,
)
from apps.api.app.models import Project, SourceArtifact
from apps.api.app.schemas import SourceArtifactOut, SourceContentResponse, SourceUploadResponse
from packages.domain.project_state import ProjectStateError

router = APIRouter(prefix="/projects/{project_id}/artifacts", tags=["artifacts"])


async def read_upload_bounded(
    file: UploadFile,
    max_bytes: int,
    chunk_size: int = 1024 * 1024,
) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(chunk_size):
        total += len(chunk)
        if total > max_bytes:
            raise IngestionRejectedError(
                "upload_too_large",
                "Upload exceeds the configured size limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _artifact_or_404(db: Session, project_id: str, artifact_id: str) -> SourceArtifact:
    artifact = db.get(SourceArtifact, artifact_id)
    if artifact is None or artifact.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return artifact


@router.post("/upload", response_model=SourceUploadResponse)
async def upload_project_source(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    context: AuthContext = Depends(require_roles("admin", "analyst", require_csrf_token=True)),
) -> SourceUploadResponse:
    project = _project_or_404(db, project_id)
    if project.status == "archived":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Archived projects are read-only")

    try:
        content = await read_upload_bounded(file, settings.max_upload_bytes)
    except IngestionRejectedError as exc:
        try:
            record_rejected_upload(
                db,
                project,
                upload_filename=file.filename,
                actor_user_id=context.user.id,
                actor_role=context.user.role,
                request_id=getattr(request.state, "request_id", None),
                error=exc,
            )
        except ProjectStateError as state_exc:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=str(state_exc)) from state_exc
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    try:
        result = ingest_source_upload(
            db,
            project,
            upload_filename=file.filename,
            content=content,
            actor_user_id=context.user.id,
            actor_role=context.user.role,
            request_id=getattr(request.state, "request_id", None),
            settings=settings,
        )
    except ProjectStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except IngestionRejectedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    return SourceUploadResponse(
        project=result.project,
        artifacts=result.artifacts,
        warnings=result.warnings,
    )


@router.get("", response_model=list[SourceArtifactOut])
def list_project_artifacts(
    project_id: str,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(get_current_context),
) -> list[SourceArtifact]:
    _ = context
    _project_or_404(db, project_id)
    return list(
        db.scalars(
            select(SourceArtifact)
            .where(SourceArtifact.project_id == project_id)
            .order_by(SourceArtifact.created_at.asc(), SourceArtifact.original_path.asc())
        ).all()
    )


@router.get("/{artifact_id}", response_model=SourceArtifactOut)
def get_project_artifact(
    project_id: str,
    artifact_id: str,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(get_current_context),
) -> SourceArtifact:
    _ = context
    _project_or_404(db, project_id)
    return _artifact_or_404(db, project_id, artifact_id)


@router.get("/{artifact_id}/content", response_model=SourceContentResponse)
def get_project_artifact_content(
    project_id: str,
    artifact_id: str,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    context: AuthContext = Depends(get_current_context),
) -> SourceContentResponse:
    _ = context
    _project_or_404(db, project_id)
    artifact = _artifact_or_404(db, project_id, artifact_id)
    try:
        text = read_artifact_text(artifact, settings)
    except ArtifactIntegrityError as exc:
        record_audit_event(
            db,
            "ARTIFACT_INTEGRITY_MISMATCH",
            actor_user_id=context.user.id,
            project_id=project_id,
            request_id=getattr(request.state, "request_id", None),
            payload={
                "artifact_id": artifact.id,
                "expected_sha256": exc.expected_sha256,
                "actual_sha256": exc.actual_sha256,
            },
        )
        db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except OSError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Artifact content not found") from exc
    except IngestionRejectedError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=exc.message) from exc
    return SourceContentResponse(artifact=artifact, lines=escaped_source_lines(text))
