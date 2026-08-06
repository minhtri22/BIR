from __future__ import annotations

from typing import Generator
from uuid import uuid4
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.app.config import Settings
from apps.api.app.main import create_app
from apps.api.app.models import User
from apps.api.app.security import hash_password


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    runtime_dir = Path("runtime-tests")
    runtime_dir.mkdir(exist_ok=True)
    artifact_dir = runtime_dir / f"artifacts-{uuid4()}"
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{runtime_dir / f'{uuid4()}.db'}",
        cookie_secure=False,
        auto_create_db=True,
        login_rate_limit_attempts=3,
        login_rate_limit_window_seconds=300,
        artifact_storage_root=str(artifact_dir),
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


def create_user(client: TestClient, email: str, password: str, role: str) -> User:
    session_factory = client.app.state.SessionLocal
    with session_factory() as db:
        user = User(email=email.lower(), password_hash=hash_password(password), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def login(client: TestClient, email: str, password: str) -> str:
    csrf = client.get("/api/v1/auth/csrf")
    assert csrf.status_code == 200
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers={"X-CSRF-Token": csrf.json()["csrf_token"]},
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]
