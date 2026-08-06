from __future__ import annotations

import pytest

from packages.domain.project_state import (
    ProjectStateError,
    assert_project_transition,
    next_status_for_source_upload,
)


def test_project_creation_status_is_draft_contract() -> None:
    transition = assert_project_transition("draft", "ingesting", "analyst", "accept_source_upload")

    assert transition.current == "draft"
    assert transition.next == "ingesting"
    assert transition.audit_event == "SOURCE_UPLOAD_ACCEPTED"


def test_upload_after_export_ready_revokes_readiness_through_ingesting() -> None:
    assert next_status_for_source_upload("export_ready") == "ingesting"


def test_failed_additional_ingestion_can_restore_previous_stable_state() -> None:
    transition = assert_project_transition(
        "ingesting",
        "export_ready",
        "system",
        "fail_or_cancel_ingestion",
    )

    assert transition.audit_event == "INGESTION_FAILED_OR_CANCELLED"


def test_analysis_failure_can_restore_previous_stable_state() -> None:
    transition = assert_project_transition(
        "analyzing",
        "ready_for_analysis",
        "system",
        "fail_or_cancel_analysis",
    )

    assert transition.audit_event == "ANALYSIS_FAILED_OR_CANCELLED"


def test_admin_can_start_analysis() -> None:
    transition = assert_project_transition(
        "ready_for_analysis",
        "analyzing",
        "admin",
        "start_analysis",
    )

    assert transition.audit_event == "ANALYSIS_STARTED"


def test_archived_project_cannot_transition() -> None:
    with pytest.raises(ProjectStateError, match="Archived projects cannot transition"):
        assert_project_transition("archived", "draft", "admin")


def test_patch_style_arbitrary_status_change_is_not_a_domain_command() -> None:
    with pytest.raises(ProjectStateError, match="not allowed"):
        assert_project_transition("draft", "export_ready", "admin", "patch_project")


def test_archive_requires_admin_actor() -> None:
    with pytest.raises(ProjectStateError, match="Actor analyst cannot transition"):
        assert_project_transition("draft", "archived", "analyst", "archive_project")
