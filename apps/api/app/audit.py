from __future__ import annotations

from sqlalchemy.orm import Session

from apps.api.app.models import AuditEvent


def record_audit_event(
    db: Session,
    event_type: str,
    *,
    actor_user_id: str | None = None,
    project_id: str | None = None,
    request_id: str | None = None,
    payload: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        actor_user_id=actor_user_id,
        project_id=project_id,
        request_id=request_id,
        payload=payload or {},
    )
    db.add(event)
    return event

