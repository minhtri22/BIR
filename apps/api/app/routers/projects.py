from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.audit import record_audit_event
from apps.api.app.dependencies import AuthContext, get_current_context, get_db, require_roles
from apps.api.app.models import AuditEvent, Project
from apps.api.app.schemas import AuditEventOut, ProjectArchiveRequest, ProjectCreate, ProjectOut, ProjectUpdate
from apps.api.app.time import utc_now
from packages.domain.project_state import ProjectStateError, assert_project_transition

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    request: Request,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(require_roles("admin", "analyst", require_csrf_token=True)),
) -> Project:
    project = Project(
        name=payload.name,
        description=payload.description,
        organization_name=payload.organization_name,
        legacy_system_name=payload.legacy_system_name,
        source_type=payload.source_type,
        snapshot_date=payload.snapshot_date,
        status="draft",
        created_by=context.user.id,
    )
    db.add(project)
    db.flush()
    record_audit_event(
        db,
        "PROJECT_CREATED",
        actor_user_id=context.user.id,
        project_id=project.id,
        request_id=getattr(request.state, "request_id", None),
        payload={"name": project.name, "status": project.status},
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    context: AuthContext = Depends(get_current_context),
) -> list[Project]:
    _ = context
    return list(db.scalars(select(Project).order_by(Project.created_at.desc(), Project.name)).all())


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(get_current_context),
) -> Project:
    _ = context
    return _project_or_404(db, project_id)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(require_roles("admin", "analyst", require_csrf_token=True)),
) -> Project:
    project = _project_or_404(db, project_id)
    if project.status == "archived":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Archived projects are read-only")

    changed_fields: dict[str, object] = {}
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if getattr(project, field) != value:
            setattr(project, field, value)
            changed_fields[field] = value

    if changed_fields:
        project.updated_at = utc_now()
        record_audit_event(
            db,
            "PROJECT_UPDATED",
            actor_user_id=context.user.id,
            project_id=project.id,
            request_id=getattr(request.state, "request_id", None),
            payload={"changed_fields": sorted(changed_fields.keys())},
        )
        db.commit()
        db.refresh(project)
    return project


@router.post("/{project_id}/archive", response_model=ProjectOut)
def archive_project(
    project_id: str,
    payload: ProjectArchiveRequest,
    request: Request,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(require_roles("admin", require_csrf_token=True)),
) -> Project:
    project = _project_or_404(db, project_id)
    if project.status == "archived":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Project is already archived")
    try:
        assert_project_transition(project.status, "archived", "admin", "archive_project")
    except ProjectStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    project.status = "archived"
    project.archive_reason = payload.reason
    project.archived_at = utc_now()
    project.updated_at = project.archived_at
    record_audit_event(
        db,
        "PROJECT_ARCHIVED",
        actor_user_id=context.user.id,
        project_id=project.id,
        request_id=getattr(request.state, "request_id", None),
        payload={"reason": payload.reason},
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}/audit-events", response_model=list[AuditEventOut])
def list_project_audit_events(
    project_id: str,
    db: Session = Depends(get_db),
    context: AuthContext = Depends(get_current_context),
) -> list[AuditEvent]:
    _ = context
    _project_or_404(db, project_id)
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.project_id == project_id)
            .order_by(AuditEvent.created_at.asc())
        ).all()
    )

