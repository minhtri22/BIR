from __future__ import annotations

import hashlib
import io
import stat
import zipfile
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.app.config import Settings
from apps.api.app.main import create_app
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
