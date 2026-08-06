from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.app.config import Settings
from apps.api.app.main import create_app
from apps.api.app.models import SessionRecord, User
from apps.api.app.security import hash_password
from apps.api.app.time import utc_now
from tests.conftest import create_user, login


def runtime_database_url(prefix: str) -> str:
    runtime_dir = Path("runtime-tests")
    runtime_dir.mkdir(exist_ok=True)
    return f"sqlite:///{runtime_dir / f'{prefix}-{uuid4()}.db'}"


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "worker": None}


def test_login_uses_generic_failure_message(client: TestClient) -> None:
    create_user(client, "admin@example.com", "correct-password", "admin")

    first_csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "wrong"},
        headers={"X-CSRF-Token": first_csrf},
    )

    second_csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong"},
        headers={"X-CSRF-Token": second_csrf},
    )

    assert unknown.status_code == 401
    assert wrong_password.status_code == 401
    assert unknown.json() == wrong_password.json() == {"detail": "Invalid email or password"}


def test_login_requires_pre_auth_csrf(client: TestClient) -> None:
    create_user(client, "admin@example.com", "password", "admin")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "password"},
    )

    assert response.status_code == 403


def test_session_cookie_flags_are_secure_in_production() -> None:
    settings = Settings(
        app_env="production",
        database_url=runtime_database_url("prod"),
        cookie_secure=True,
        auto_create_db=True,
    )
    app = create_app(settings)
    with TestClient(app, base_url="https://testserver") as client:
        create_user(client, "admin@example.com", "password", "admin")
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "password"},
            headers={"X-CSRF-Token": csrf},
        )

    set_cookie = response.headers["set-cookie"]
    assert "bf_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Secure" in set_cookie


def test_project_create_requires_session_csrf(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    login(client, "analyst@example.com", "password")

    response = client.post("/api/v1/projects", json={"name": "No CSRF"})

    assert response.status_code == 403


def test_project_crud_archive_and_audit(client: TestClient) -> None:
    create_user(client, "admin@example.com", "password", "admin")
    csrf_token = login(client, "admin@example.com", "password")

    created = client.post(
        "/api/v1/projects",
        json={
            "name": "Legacy Purchase Approval",
            "legacy_system_name": "ORDER_MAINFRAME",
            "source_type": "COBOL",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert created.status_code == 201, created.text
    project = created.json()
    assert project["status"] == "draft"

    listed = client.get("/api/v1/projects")
    assert listed.status_code == 200
    assert any(row["id"] == project["id"] for row in listed.json())

    updated = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"description": "Phase 1 foundation project"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Phase 1 foundation project"

    forbidden_status_patch = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "export_ready"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert forbidden_status_patch.status_code == 422

    archived = client.post(
        f"/api/v1/projects/{project['id']}/archive",
        json={"reason": "Phase 1 archive gate"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    edit_archived = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"description": "Should not change"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert edit_archived.status_code == 409

    audit = client.get(f"/api/v1/projects/{project['id']}/audit-events")
    assert audit.status_code == 200
    assert [event["event_type"] for event in audit.json()] == [
        "PROJECT_CREATED",
        "PROJECT_UPDATED",
        "PROJECT_ARCHIVED",
    ]


def test_viewer_cannot_create_project_or_call_review_endpoint(client: TestClient) -> None:
    create_user(client, "viewer@example.com", "password", "viewer")
    csrf_token = login(client, "viewer@example.com", "password")

    create_response = client.post(
        "/api/v1/projects",
        json={"name": "Forbidden"},
        headers={"X-CSRF-Token": csrf_token},
    )
    review_response = client.post(
        "/api/v1/projects/P-1/statements/S-1/review",
        json={"decision": "confirm"},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert create_response.status_code == 403
    assert review_response.status_code == 403


def test_logout_invalidates_server_side_session(client: TestClient) -> None:
    create_user(client, "admin@example.com", "password", "admin")
    csrf_token = login(client, "admin@example.com", "password")

    logout_response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout_response.status_code == 200

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 401


def test_expired_idle_session_is_rejected(client: TestClient) -> None:
    create_user(client, "admin@example.com", "password", "admin")
    login(client, "admin@example.com", "password")

    session_factory = client.app.state.SessionLocal
    with session_factory() as db:
        session = db.query(SessionRecord).one()
        session.idle_expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_development_seed_requires_environment_password() -> None:
    settings = Settings(
        app_env="development",
        database_url=runtime_database_url("seed"),
        auto_create_db=True,
        dev_seed_password=None,
    )
    app = create_app(settings)

    try:
        with TestClient(app):
            raise AssertionError("startup should fail before yielding a client")
    except RuntimeError as exc:
        assert "DEV_SEED_PASSWORD is required" in str(exc)


def test_development_seed_user_can_log_in() -> None:
    settings = Settings(
        app_env="development",
        database_url=runtime_database_url("seed-login"),
        auto_create_db=True,
        dev_seed_email="seed@example.com",
        dev_seed_password="from-env",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "seed@example.com", "password": "from-env"},
            headers={"X-CSRF-Token": csrf},
        )

    assert response.status_code == 200


def test_login_rate_limit_by_account_and_ip(client: TestClient) -> None:
    create_user(client, "admin@example.com", "password", "admin")

    for _ in range(3):
        csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "wrong"},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 401

    csrf = client.get("/api/v1/auth/csrf").json()["csrf_token"]
    limited = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "password"},
        headers={"X-CSRF-Token": csrf},
    )

    assert limited.status_code == 429
