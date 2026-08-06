from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.app.dependencies import AuthContext, require_roles

router = APIRouter(prefix="/projects/{project_id}/statements", tags=["review"])


@router.post("/{statement_id}/review")
def review_not_yet_implemented(
    project_id: str,
    statement_id: str,
    context: AuthContext = Depends(require_roles("reviewer", require_csrf_token=True)),
) -> dict[str, str]:
    _ = (project_id, statement_id, context)
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        detail="Review workflow starts in Phase 4; RBAC gate is active in Phase 1.",
    )

