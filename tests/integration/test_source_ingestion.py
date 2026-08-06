from __future__ import annotations

import asyncio
import hashlib
import io
import stat
import zipfile
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

import apps.api.app.ingestion as ingestion_module
from apps.api.app.config import Settings
from apps.api.app.ingestion import IngestionRejectedError
from apps.api.app.main import create_app
from apps.api.app.routers.artifacts import read_upload_bounded
from tests.conftest import create_user, login


def _create_project(client: TestClient, csrf_token: str) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={"name": f"Phase 2 Project {uuid4()}", "source_type": "COBOL"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _upload(
    client: TestClient,
    project_id: str,
    csrf_token: str,
    filename: str,
    content: bytes,
) -> TestClient:
    return client.post(
        f"/api/v1/projects/{project_id}/artifacts/upload",
        files={"file": (filename, content, "application/octet-stream")},
        headers={"X-CSRF-Token": csrf_token},
    )


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_tc01_text_upload_persists_immutable_inventory_and_escaped_viewer(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    source = b"IDENTIFICATION DIVISION.\n<script>alert('x')</script>\n"

    response = _upload(client, project["id"], csrf_token, "unsafe-name.cbl", source)

    assert response.status_code == 200, response.text
    payload = response.json()
    artifact = payload["artifacts"][0]
    assert payload["project"]["status"] == "ready_for_analysis"
    assert artifact["original_path"] == "unsafe-name.cbl"
    assert "unsafe-name.cbl" not in artifact["storage_path"]
    assert artifact["sha256"] == hashlib.sha256(source).hexdigest()
    assert artifact["encoding"] in {"utf-8-sig", "utf-8"}
    assert artifact["line_count"] == 2
    assert artifact["analysis_status"] == "not_analyzed"
    assert artifact["candidate_count"] == 0

    storage_root = Path(client.app.state.settings.artifact_storage_root).resolve()
    stored_file = (storage_root / artifact["storage_path"]).resolve()
    assert stored_file.is_relative_to(storage_root)
    assert stored_file.read_bytes() == source

    inventory = client.get(f"/api/v1/projects/{project['id']}/artifacts")
    assert inventory.status_code == 200
    assert inventory.json()[0]["id"] == artifact["id"]

    viewer = client.get(f"/api/v1/projects/{project['id']}/artifacts/{artifact['id']}/content")
    assert viewer.status_code == 200
    assert viewer.json()["lines"][1]["escaped_html"] == "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;"

    audit = client.get(f"/api/v1/projects/{project['id']}/audit-events").json()
    assert [event["event_type"] for event in audit] == [
        "PROJECT_CREATED",
        "SOURCE_UPLOAD_ACCEPTED",
        "INGESTION_COMPLETED",
    ]


def test_tc01_zip_path_traversal_is_blocked_without_artifacts(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    malicious_zip = _zip_bytes({"../../evil.cbl": b"IDENTIFICATION DIVISION.\n"})

    response = _upload(client, project["id"], csrf_token, "sources.zip", malicious_zip)

    assert response.status_code == 400
    assert "unsafe" in response.json()["detail"] or "relative" in response.json()["detail"]
    project_after = client.get(f"/api/v1/projects/{project['id']}").json()
    assert project_after["status"] == "draft"
    assert client.get(f"/api/v1/projects/{project['id']}/artifacts").json() == []
    assert not (Path(client.app.state.settings.artifact_storage_root) / "evil.cbl").exists()
    audit_types = [event["event_type"] for event in client.get(f"/api/v1/projects/{project['id']}/audit-events").json()]
    assert audit_types == [
        "PROJECT_CREATED",
        "SOURCE_UPLOAD_ACCEPTED",
        "INGESTION_FAILED_OR_CANCELLED",
    ]


def test_oversized_upload_is_rejected_with_restore_and_failure_audit() -> None:
    runtime_dir = Path("runtime-tests")
    runtime_dir.mkdir(exist_ok=True)
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{runtime_dir / f'oversized-{uuid4()}.db'}",
        cookie_secure=False,
        auto_create_db=True,
        artifact_storage_root=str(runtime_dir / f"artifacts-{uuid4()}"),
        max_upload_bytes=8,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        create_user(client, "analyst@example.com", "password", "analyst")
        csrf_token = login(client, "analyst@example.com", "password")
        project = _create_project(client, csrf_token)

        response = _upload(client, project["id"], csrf_token, "too-large.cbl", b"123456789")

        assert response.status_code == 400
        assert response.json()["detail"] == "Upload exceeds the configured size limit."
        assert client.get(f"/api/v1/projects/{project['id']}/artifacts").json() == []
        assert client.get(f"/api/v1/projects/{project['id']}").json()["status"] == "draft"
        audit = client.get(f"/api/v1/projects/{project['id']}/audit-events").json()
        assert [event["event_type"] for event in audit] == [
            "PROJECT_CREATED",
            "SOURCE_UPLOAD_ACCEPTED",
            "INGESTION_FAILED_OR_CANCELLED",
        ]
        assert audit[-1]["payload"]["code"] == "upload_too_large"


def test_bounded_upload_reader_stops_after_limit_without_consuming_remaining_chunks() -> None:
    class ChunkedUpload:
        def __init__(self) -> None:
            self.chunks = [b"1234", b"5678", b"should-not-be-read"]
            self.read_calls = 0

        async def read(self, size: int) -> bytes:
            assert size == 4
            self.read_calls += 1
            return self.chunks.pop(0) if self.chunks else b""

    upload = ChunkedUpload()

    try:
        asyncio.run(read_upload_bounded(upload, max_bytes=5, chunk_size=4))  # type: ignore[arg-type]
        raise AssertionError("oversized upload should be rejected")
    except IngestionRejectedError as exc:
        assert exc.code == "upload_too_large"
        assert upload.read_calls == 2
        assert upload.chunks == [b"should-not-be-read"]


def test_tc11_zip_symlink_nested_archive_and_decompression_limits_are_blocked(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")

    symlink_buffer = io.BytesIO()
    with zipfile.ZipFile(symlink_buffer, "w") as archive:
        info = zipfile.ZipInfo("linked.cbl")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "target.cbl")

    cases = [
        ("symlink.zip", symlink_buffer.getvalue(), "symlink"),
        ("nested.zip", _zip_bytes({"inner.zip": _zip_bytes({"safe.cbl": b"ok\n"})}), "Nested"),
        ("ratio.zip", _zip_bytes({"huge.cbl": b"A" * 20000}), "compression ratio"),
    ]

    for filename, content, detail_fragment in cases:
        project = _create_project(client, csrf_token)
        response = _upload(client, project["id"], csrf_token, filename, content)
        assert response.status_code == 400, response.text
        assert detail_fragment.lower() in response.json()["detail"].lower()
        assert client.get(f"/api/v1/projects/{project['id']}/artifacts").json() == []
        assert client.get(f"/api/v1/projects/{project['id']}").json()["status"] == "draft"


def test_tc11_entry_count_path_length_and_uncompressed_limits_are_enforced() -> None:
    runtime_dir = Path("runtime-tests")
    runtime_dir.mkdir(exist_ok=True)
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{runtime_dir / f'limits-{uuid4()}.db'}",
        cookie_secure=False,
        auto_create_db=True,
        artifact_storage_root=str(runtime_dir / f"artifacts-{uuid4()}"),
        max_zip_entries=2,
        max_zip_path_length=12,
        max_zip_uncompressed_bytes=20,
        max_zip_compression_ratio=1000,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        create_user(client, "analyst@example.com", "password", "analyst")
        csrf_token = login(client, "analyst@example.com", "password")
        cases = [
            ("entries.zip", _zip_bytes({"a.cbl": b"1", "b.cbl": b"2", "c.cbl": b"3"}), "entry count"),
            ("path.zip", _zip_bytes({"very-long-name.cbl": b"1"}), "path"),
            ("total.zip", _zip_bytes({"a.cbl": b"A" * 15, "b.cbl": b"B" * 15}), "uncompressed"),
        ]
        for filename, content, detail_fragment in cases:
            project = _create_project(client, csrf_token)
            response = _upload(client, project["id"], csrf_token, filename, content)
            assert response.status_code == 400
            assert detail_fragment in response.json()["detail"]
            assert client.get(f"/api/v1/projects/{project['id']}").json()["status"] == "draft"


def test_unsupported_and_binary_entries_return_warnings_without_execution(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    marker = Path(client.app.state.settings.artifact_storage_root).resolve().parent / "should-not-exist.txt"
    source = f"Write-Output hacked > {marker}\n".encode()
    mixed_zip = _zip_bytes(
        {
            "runme.txt": source,
            "binary.cbl": b"\x00\x01\x02",
            "program.exe": b"MZ\x00\x01",
        }
    )

    response = _upload(client, project["id"], csrf_token, "mixed.zip", mixed_zip)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["project"]["status"] == "ready_for_analysis"
    assert len(payload["artifacts"]) == 1
    assert {warning["warning_code"] for warning in payload["warnings"]} == {
        "binary_file_skipped",
        "unsupported_file_type",
    }
    assert not marker.exists()
    viewer = client.get(
        f"/api/v1/projects/{project['id']}/artifacts/{payload['artifacts'][0]['id']}/content"
    )
    assert "Write-Output hacked" in viewer.json()["lines"][0]["escaped_html"]


def test_filesystem_failure_cleans_partial_artifact_restores_status_and_audits(monkeypatch) -> None:
    runtime_dir = Path("runtime-tests")
    runtime_dir.mkdir(exist_ok=True)
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{runtime_dir / f'fs-failure-{uuid4()}.db'}",
        cookie_secure=False,
        auto_create_db=True,
        artifact_storage_root=str(runtime_dir / f"artifacts-{uuid4()}"),
    )
    app = create_app(settings)
    created_paths: list[Path] = []

    def failing_write(settings: Settings, storage_path: str, content: bytes) -> None:
        target = ingestion_module.artifact_absolute_path(settings, storage_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        created_paths.append(target)
        raise OSError("simulated disk failure")

    monkeypatch.setattr(ingestion_module, "write_immutable_artifact", failing_write)

    with TestClient(app, raise_server_exceptions=False) as client:
        create_user(client, "analyst@example.com", "password", "analyst")
        csrf_token = login(client, "analyst@example.com", "password")
        project = _create_project(client, csrf_token)

        response = _upload(client, project["id"], csrf_token, "partial.cbl", b"IDENTIFICATION DIVISION.\n")

        assert response.status_code == 500
        assert client.get(f"/api/v1/projects/{project['id']}").json()["status"] == "draft"
        assert client.get(f"/api/v1/projects/{project['id']}/artifacts").json() == []
        assert created_paths and all(not path.exists() for path in created_paths)
        audit = client.get(f"/api/v1/projects/{project['id']}/audit-events").json()
        assert audit[-1]["event_type"] == "INGESTION_FAILED_OR_CANCELLED"
        assert audit[-1]["payload"]["code"] == "ingestion_persistence_failed"


def test_tampered_artifact_is_rejected_and_audited(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    response = _upload(client, project["id"], csrf_token, "stable.cbl", b"IDENTIFICATION DIVISION.\n")
    assert response.status_code == 200, response.text
    artifact = response.json()["artifacts"][0]
    storage_root = Path(client.app.state.settings.artifact_storage_root).resolve()
    (storage_root / artifact["storage_path"]).write_bytes(b"TAMPERED\n")

    viewer = client.get(f"/api/v1/projects/{project['id']}/artifacts/{artifact['id']}/content")

    assert viewer.status_code == 409
    assert viewer.json()["detail"] == "Artifact integrity check failed."
    audit = client.get(f"/api/v1/projects/{project['id']}/audit-events").json()
    assert audit[-1]["event_type"] == "ARTIFACT_INTEGRITY_MISMATCH"
    assert audit[-1]["payload"]["artifact_id"] == artifact["id"]


def test_cp932_source_upload_records_legacy_japanese_encoding(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    source_text = "部署コード=東京\n"
    response = _upload(client, project["id"], csrf_token, "japanese.txt", source_text.encode("cp932"))

    assert response.status_code == 200, response.text
    artifact = response.json()["artifacts"][0]
    assert artifact["encoding"] == "cp932"
    viewer = client.get(f"/api/v1/projects/{project['id']}/artifacts/{artifact['id']}/content")
    assert viewer.json()["lines"][0]["escaped_html"] == "部署コード=東京"


def test_latin1_fallback_creates_low_confidence_encoding_warning(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    response = _upload(client, project["id"], csrf_token, "fallback.txt", b"FIELD-\x81\n")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["artifacts"][0]["encoding"] == "latin-1"
    assert [warning["warning_code"] for warning in payload["warnings"]] == ["encoding_low_confidence"]
    assert payload["warnings"][0]["artifact_id"] == payload["artifacts"][0]["id"]
