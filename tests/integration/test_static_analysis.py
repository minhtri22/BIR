from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from apps.api.app.analysis import create_analysis_job, process_analysis_job
from apps.api.app.ingestion import artifact_absolute_path
from apps.api.app.models import (
    AnalysisGap,
    AnalysisJob,
    AnalysisJobArtifact,
    AnalyzerVersion,
    BusinessStatement,
    Evidence,
    Project,
    SourceArtifact,
)
from tests.conftest import create_user, login


SOURCE_TEXT = "\n".join(
    [
        "* Approve large orders",
        "IF ORDER-AMOUNT > 1000",
        "MOVE 'APPROVED' TO ORDER-STATUS.",
        "EVALUATE CUSTOMER-TYPE",
        "WHEN 'VIP'",
        "EXEC SQL SELECT * FROM CUSTOMER END-EXEC",
        "IF USER-ROLE = 'MANAGER'",
        "COMPUTE DUE-DATE = CURRENT-DATE + 30.",
        "CALL 'PAYRISK'.",
        "*> TODO verify external dependency",
    ]
)
SOURCE_BYTES = SOURCE_TEXT.encode("utf-8")


def _create_project(client: TestClient, csrf_token: str) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={"name": f"Phase 3 Project {uuid4()}", "source_type": "COBOL"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _upload_source(client: TestClient, project_id: str, csrf_token: str, content: bytes = SOURCE_BYTES) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/artifacts/upload",
        files={"file": ("rules.cbl", content, "text/plain")},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 200, response.text
    return response.json()["artifacts"][0]


def _start_analysis(
    client: TestClient,
    project_id: str,
    csrf_token: str,
    configuration: dict | None = None,
) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/analysis-jobs",
        json={"artifact_ids": [], "configuration": configuration or {}},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code in {200, 201}, response.text
    return response.json()


def _wait_for_job(client: TestClient, project_id: str, job_id: str) -> dict:
    for _ in range(20):
        response = client.get(f"/api/v1/projects/{project_id}/analysis-jobs/{job_id}")
        assert response.status_code == 200, response.text
        job = response.json()
        if job["status"] not in {"queued", "running"}:
            return job
        time.sleep(0.1)
    raise AssertionError("analysis job did not finish")


def test_static_analysis_creates_candidates_evidence_gaps_questions_and_audit(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    artifact = _upload_source(client, project["id"], csrf_token)

    job = _start_analysis(client, project["id"], csrf_token)
    finished = _wait_for_job(client, project["id"], job["id"])

    assert finished["status"] == "succeeded"
    assert finished["analyzer_name"] == "static-cobol-mvp"
    assert finished["analyzer_version"] == "0.1.0"
    assert finished["candidate_count"] >= 8
    assert client.get(f"/api/v1/projects/{project['id']}").json()["status"] == "review_in_progress"

    inventory = client.get(f"/api/v1/projects/{project['id']}/artifacts").json()
    assert inventory[0]["analysis_status"] == "analyzed"
    assert inventory[0]["candidate_count"] == finished["candidate_count"]

    candidates = client.get(f"/api/v1/projects/{project['id']}/statements?status=candidate").json()
    assert len(candidates) == finished["candidate_count"]
    assert {candidate["created_by_kind"] for candidate in candidates} == {"system"}
    assert all(candidate["analysis_job_id"] == job["id"] for candidate in candidates)
    assert all(candidate["evidence_count"] >= 1 for candidate in candidates)
    assert {candidate["pattern_id"] for candidate in candidates} >= {
        "if_else",
        "assignment",
        "sql",
        "procedure_call",
    }

    evidence = client.get(
        f"/api/v1/projects/{project['id']}/statements/{candidates[0]['id']}/evidence"
    ).json()
    assert evidence[0]["artifact_id"] == artifact["id"]
    assert evidence[0]["artifact_sha256"] == artifact["sha256"]
    assert evidence[0]["start_line"] >= 1
    assert evidence[0]["excerpt"]

    gaps = client.get(f"/api/v1/projects/{project['id']}/analysis-gaps").json()
    questions = client.get(f"/api/v1/projects/{project['id']}/unresolved-questions").json()
    assert gaps
    assert questions

    audit_types = [event["event_type"] for event in client.get(f"/api/v1/projects/{project['id']}/audit-events").json()]
    assert "ANALYSIS_STARTED" in audit_types
    assert "ANALYSIS_COMPLETED" in audit_types


def test_succeeded_request_fingerprint_reuses_existing_job_without_duplicate_candidates(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    _upload_source(client, project["id"], csrf_token)

    first_job = _start_analysis(client, project["id"], csrf_token)
    first_finished = _wait_for_job(client, project["id"], first_job["id"])
    first_candidates = client.get(f"/api/v1/projects/{project['id']}/statements").json()

    second_response = client.post(
        f"/api/v1/projects/{project['id']}/analysis-jobs",
        json={"artifact_ids": [], "configuration": {}},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert second_response.status_code == 200, second_response.text
    assert second_response.json()["id"] == first_finished["id"]
    second_candidates = client.get(f"/api/v1/projects/{project['id']}/statements").json()
    assert len(second_candidates) == len(first_candidates)


def test_new_analysis_run_inserts_new_candidates_without_updating_existing_ones(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    _upload_source(client, project["id"], csrf_token)

    first_job = _start_analysis(
        client,
        project["id"],
        csrf_token,
        {"enabled_patterns": ["if_else"], "chunk_max_lines": 20, "chunk_overlap_lines": 0},
    )
    _wait_for_job(client, project["id"], first_job["id"])
    first_candidates = client.get(f"/api/v1/projects/{project['id']}/statements").json()
    first_candidate_id = first_candidates[0]["id"]
    first_updated_at = first_candidates[0]["updated_at"]

    second_job = _start_analysis(
        client,
        project["id"],
        csrf_token,
        {"enabled_patterns": ["if_else", "assignment"], "chunk_max_lines": 20, "chunk_overlap_lines": 0},
    )
    _wait_for_job(client, project["id"], second_job["id"])
    all_candidates = client.get(f"/api/v1/projects/{project['id']}/statements").json()
    original = next(candidate for candidate in all_candidates if candidate["id"] == first_candidate_id)

    assert len(all_candidates) > len(first_candidates)
    assert original["updated_at"] == first_updated_at
    assert {candidate["analysis_job_id"] for candidate in all_candidates} == {first_job["id"], second_job["id"]}


def test_active_project_job_rejects_new_analysis_request(client: TestClient) -> None:
    user = create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    artifact = _upload_source(client, project["id"], csrf_token)
    session_factory = client.app.state.SessionLocal

    with session_factory() as db:
        analyzer = AnalyzerVersion(
            analyzer_name="static-cobol-mvp",
            analyzer_version="0.1.0",
            extractor_kind="static",
            configuration_json={"chunk_max_lines": 120, "chunk_overlap_lines": 20, "enabled_patterns": ["if_else"]},
            configuration_hash="c" * 64,
            pattern_set_hash="p" * 64,
        )
        db.add(analyzer)
        db.flush()
        project_row = db.get(Project, project["id"])
        assert project_row is not None
        project_row.status = "analyzing"
        job = AnalysisJob(
            project_id=project["id"],
            analyzer_version_id=analyzer.id,
            status="queued",
            request_fingerprint="a" * 64,
            requested_by=user.id,
            requested_artifact_count=1,
            attempt_no=1,
            previous_project_status="ready_for_analysis",
        )
        db.add(job)
        db.flush()
        db.add(
            AnalysisJobArtifact(
                job_id=job.id,
                artifact_id=artifact["id"],
                artifact_sha256=artifact["sha256"],
                status="queued",
            )
        )
        db.commit()

    response = client.post(
        f"/api/v1/projects/{project['id']}/analysis-jobs",
        json={"artifact_ids": [], "configuration": {}},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 409
    assert "active analysis job" in response.json()["detail"]


def test_unknown_config_and_client_owned_analyzer_identity_are_rejected(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    _upload_source(client, project["id"], csrf_token)

    unknown_config = client.post(
        f"/api/v1/projects/{project['id']}/analysis-jobs",
        json={"artifact_ids": [], "configuration": {"made_up": True}},
        headers={"X-CSRF-Token": csrf_token},
    )
    analyzer_spoof = client.post(
        f"/api/v1/projects/{project['id']}/analysis-jobs",
        json={"artifact_ids": [], "configuration": {}, "analyzer_name": "client"},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert unknown_config.status_code == 400
    assert analyzer_spoof.status_code == 422


def test_failed_analysis_restores_project_and_retry_creates_next_attempt(client: TestClient) -> None:
    user = create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    artifact = _upload_source(client, project["id"], csrf_token)
    settings = client.app.state.settings
    session_factory = client.app.state.SessionLocal

    with session_factory() as db:
        project_row = db.get(Project, project["id"])
        assert project_row is not None
        decision = create_analysis_job(
            db,
            project_row,
            artifact_ids=None,
            configuration={"enabled_patterns": ["if_else"], "chunk_max_lines": 20, "chunk_overlap_lines": 0},
            actor_user_id=user.id,
            actor_role="analyst",
            request_id="test-failure",
        )
        failed_job_id = decision.job.id

    artifact_path = artifact_absolute_path(settings, artifact["storage_path"])
    artifact_path.write_bytes(b"TAMPERED\n")
    with session_factory() as db:
        process_analysis_job(db, settings, job_id=failed_job_id, request_id="test-failure")

    failed_job = client.get(f"/api/v1/projects/{project['id']}/analysis-jobs/{failed_job_id}").json()
    assert failed_job["status"] == "failed"
    assert failed_job["failure_code"] == "artifact_integrity_mismatch"
    assert client.get(f"/api/v1/projects/{project['id']}").json()["status"] == "ready_for_analysis"

    artifact_path.write_bytes(SOURCE_BYTES)
    retry_response = client.post(
        f"/api/v1/projects/{project['id']}/analysis-jobs/{failed_job_id}/retry",
        json={},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert retry_response.status_code == 201, retry_response.text
    retry_job = _wait_for_job(client, project["id"], retry_response.json()["id"])

    assert retry_job["status"] == "succeeded"
    assert retry_job["attempt_no"] == 2
    assert retry_job["retry_of_job_id"] == failed_job_id


def test_evidence_exactly_one_target_constraint_is_enforced(client: TestClient) -> None:
    create_user(client, "analyst@example.com", "password", "analyst")
    csrf_token = login(client, "analyst@example.com", "password")
    project = _create_project(client, csrf_token)
    _upload_source(client, project["id"], csrf_token)
    job = _start_analysis(client, project["id"], csrf_token)
    _wait_for_job(client, project["id"], job["id"])

    session_factory = client.app.state.SessionLocal
    with session_factory() as db:
        statement = db.scalar(select(BusinessStatement).where(BusinessStatement.project_id == project["id"]))
        gap = db.scalar(select(AnalysisGap).where(AnalysisGap.project_id == project["id"]))
        evidence = db.scalar(select(Evidence).where(Evidence.statement_id == statement.id))
        assert statement is not None
        assert gap is not None
        assert evidence is not None
        invalid = Evidence(
            project_id=project["id"],
            analysis_job_id=job["id"],
            statement_id=statement.id,
            analysis_gap_id=gap.id,
            unresolved_question_id=None,
            artifact_id=evidence.artifact_id,
            artifact_sha256=evidence.artifact_sha256,
            source_chunk_id=evidence.source_chunk_id,
            start_line=evidence.start_line,
            end_line=evidence.end_line,
            excerpt=evidence.excerpt,
            excerpt_sha256=evidence.excerpt_sha256,
            relation_type="supports",
            extraction_method="static",
            pattern_id=evidence.pattern_id,
            analyzer_version_id=evidence.analyzer_version_id,
            created_by=None,
            created_by_kind="system",
        )
        db.add(invalid)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
