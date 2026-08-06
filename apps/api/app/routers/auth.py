from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from apps.api.app.audit import record_audit_event
from apps.api.app.config import Settings
from apps.api.app.dependencies import AuthContext, get_current_context, get_db, get_settings, require_csrf
from apps.api.app.models import CsrfNonce, LoginRateLimit, SessionRecord, User
from apps.api.app.schemas import AuthSessionResponse, CsrfResponse, LoginRequest
from apps.api.app.security import (
    account_identifier_hash,
    compare_hash,
    generate_token,
    sha256_text,
    verify_password,
)
from apps.api.app.time import utc_now

router = APIRouter(prefix="/auth", tags=["auth"])

GENERIC_LOGIN_ERROR = "Invalid email or password"


def _set_cookie(response: Response, settings: Settings, name: str, value: str, max_age: int) -> None:
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def _client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host


def _rate_limit_key(request: Request, email: str) -> str:
    return sha256_text(f"{_client_ip(request)}:{account_identifier_hash(email)}")


def _check_rate_limit(db: Session, settings: Settings, key_hash: str) -> None:
    now = utc_now()
    record = db.get(LoginRateLimit, key_hash)
    window_delta = timedelta(seconds=settings.login_rate_limit_window_seconds)
    if record is None:
        return
    if record.window_started_at + window_delta <= now:
        db.delete(record)
        db.flush()
        return
    if record.attempts >= settings.login_rate_limit_attempts:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")


def _record_failed_login(db: Session, settings: Settings, request: Request, email: str) -> None:
    now = utc_now()
    key_hash = _rate_limit_key(request, email)
    record = db.get(LoginRateLimit, key_hash)
    window_delta = timedelta(seconds=settings.login_rate_limit_window_seconds)
    if record is None or record.window_started_at + window_delta <= now:
        record = LoginRateLimit(key_hash=key_hash, attempts=1, window_started_at=now)
        db.merge(record)
    else:
        record.attempts += 1
    record_audit_event(
        db,
        "LOGIN_FAILED",
        request_id=getattr(request.state, "request_id", None),
        payload={"account_identifier_hash": account_identifier_hash(email)},
    )


def _reset_rate_limit(db: Session, request: Request, email: str) -> None:
    db.execute(delete(LoginRateLimit).where(LoginRateLimit.key_hash == _rate_limit_key(request, email)))


def _validate_pre_login_csrf(
    db: Session,
    settings: Settings,
    request: Request,
    csrf_token: str | None,
) -> CsrfNonce:
    nonce_id = request.cookies.get(settings.pre_csrf_cookie_name)
    if not nonce_id or not csrf_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")

    nonce = db.get(CsrfNonce, nonce_id)
    if (
        nonce is None
        or nonce.used_at is not None
        or nonce.expires_at <= utc_now()
        or not compare_hash(csrf_token, nonce.token_hash)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
    return nonce


@router.get("/csrf", response_model=CsrfResponse)
def create_login_csrf(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CsrfResponse:
    raw_token = generate_token()
    nonce = CsrfNonce(
        token_hash=sha256_text(raw_token),
        expires_at=utc_now() + timedelta(seconds=settings.csrf_nonce_seconds),
    )
    db.add(nonce)
    db.commit()
    _set_cookie(response, settings, settings.pre_csrf_cookie_name, nonce.id, settings.csrf_nonce_seconds)
    return CsrfResponse(csrf_token=raw_token)


@router.post("/login", response_model=AuthSessionResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthSessionResponse:
    email = payload.email.strip().lower()
    csrf_token = request.headers.get("x-csrf-token")
    nonce = _validate_pre_login_csrf(db, settings, request, csrf_token)
    key_hash = _rate_limit_key(request, email)
    _check_rate_limit(db, settings, key_hash)

    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        nonce.used_at = utc_now()
        _record_failed_login(db, settings, request, email)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)

    now = utc_now()
    raw_session_id = generate_token()
    raw_session_csrf = generate_token()
    session = SessionRecord(
        token_hash=sha256_text(raw_session_id),
        csrf_token_hash=sha256_text(raw_session_csrf),
        user_id=user.id,
        created_at=now,
        last_seen_at=now,
        idle_expires_at=now + timedelta(seconds=settings.session_idle_seconds),
        absolute_expires_at=now + timedelta(seconds=settings.session_absolute_seconds),
    )
    nonce.used_at = now
    db.add(session)
    _reset_rate_limit(db, request, email)
    record_audit_event(
        db,
        "LOGIN_SUCCEEDED",
        actor_user_id=user.id,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()

    _set_cookie(response, settings, settings.session_cookie_name, raw_session_id, settings.session_absolute_seconds)
    return AuthSessionResponse(user=user, csrf_token=raw_session_csrf)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    session = db.get(SessionRecord, context.session.id)
    if session is not None:
        session.revoked_at = utc_now()
    record_audit_event(
        db,
        "LOGOUT",
        actor_user_id=context.user.id,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=AuthSessionResponse)
def me(
    context: AuthContext = Depends(get_current_context),
    db: Session = Depends(get_db),
) -> AuthSessionResponse:
    csrf_token = generate_token()
    session = db.get(SessionRecord, context.session.id)
    if session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    session.csrf_token_hash = sha256_text(csrf_token)
    db.commit()
    return AuthSessionResponse(user=context.user, csrf_token=csrf_token)

