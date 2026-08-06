from __future__ import annotations

from datetime import date, datetime
from typing import Literal

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

