from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text
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
