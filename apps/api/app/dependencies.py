from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.config import Settings
from apps.api.app.models import SessionRecord, User
from apps.api.app.security import compare_hash, sha256_text
from apps.api.app.time import utc_now


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: SessionRecord


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request):
    session_factory = request.app.state.SessionLocal
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_current_context(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    raw_session_id = request.cookies.get(settings.session_cookie_name)
    if not raw_session_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    token_hash = sha256_text(raw_session_id)
    session = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == token_hash))
    now = utc_now()
    if (
        session is None
        or session.revoked_at is not None
        or session.idle_expires_at <= now
        or session.absolute_expires_at <= now
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    session.last_seen_at = now
    session.idle_expires_at = now + request.app.state.session_idle_delta
    db.commit()
    return AuthContext(user=user, session=session)


def validate_csrf_header(request: Request, context: AuthContext) -> None:
    csrf_token = request.headers.get("x-csrf-token")
    if not csrf_token or not compare_hash(csrf_token, context.session.csrf_token_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")


def require_csrf(
    request: Request,
    context: AuthContext = Depends(get_current_context),
) -> AuthContext:
    validate_csrf_header(request, context)
    return context


def require_roles(*roles: str, require_csrf_token: bool = False):
    def dependency(
        request: Request,
        context: AuthContext = Depends(get_current_context),
    ) -> AuthContext:
        if context.user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Forbidden")
        if require_csrf_token:
            validate_csrf_header(request, context)
        return context

    return dependency

