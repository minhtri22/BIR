from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

ProjectStatus = Literal[
    "draft",
    "ingesting",
    "ready_for_analysis",
    "analyzing",
    "review_in_progress",
    "export_ready",
    "archived",
]

Actor = Literal["admin", "analyst", "reviewer", "viewer", "system"]


class ProjectStateError(ValueError):
    """Raised when a project transition violates the locked lifecycle."""


@dataclass(frozen=True)
class ProjectTransition:
    current: ProjectStatus
    next: ProjectStatus
    actors: tuple[Actor, ...]
    command: str
    audit_event: str
    precondition: str
    recovery_rule: str | None = None
    export_impact: str | None = None


PROJECT_STATUSES: tuple[ProjectStatus, ...] = (
    "draft",
    "ingesting",
    "ready_for_analysis",
    "analyzing",
    "review_in_progress",
    "export_ready",
    "archived",
)

PROJECT_TRANSITIONS: tuple[ProjectTransition, ...] = (
    ProjectTransition(
        "draft",
        "ingesting",
        ("admin", "analyst"),
        "accept_source_upload",
        "SOURCE_UPLOAD_ACCEPTED",
        "A valid source upload request is accepted.",
    ),
    ProjectTransition(
        "ready_for_analysis",
        "ingesting",
        ("admin", "analyst"),
        "accept_source_upload",
        "SOURCE_UPLOAD_ACCEPTED",
        "Additional source upload is accepted.",
    ),
    ProjectTransition(
        "review_in_progress",
        "ingesting",
        ("admin", "analyst"),
        "accept_source_upload",
        "SOURCE_UPLOAD_ACCEPTED",
        "Additional source upload is accepted.",
        export_impact="Current review coverage is stale.",
    ),
    ProjectTransition(
        "export_ready",
        "ingesting",
        ("admin", "analyst"),
        "accept_source_upload",
        "SOURCE_UPLOAD_ACCEPTED",
        "Additional source upload is accepted.",
        export_impact="Current readiness is revoked; prior exports remain immutable snapshots.",
    ),
    ProjectTransition(
        "ingesting",
        "draft",
        ("system", "admin"),
        "fail_or_cancel_ingestion",
        "INGESTION_FAILED_OR_CANCELLED",
        "First ingestion fails or is cancelled.",
        recovery_rule="Return to recorded previous stable state; default to draft.",
    ),
    ProjectTransition(
        "ingesting",
        "ready_for_analysis",
        ("system", "admin"),
        "fail_or_cancel_ingestion",
        "INGESTION_FAILED_OR_CANCELLED",
        "Additional ingestion fails or is cancelled.",
        recovery_rule="Return to recorded previous stable state.",
    ),
    ProjectTransition(
        "ingesting",
        "review_in_progress",
        ("system", "admin"),
        "fail_or_cancel_ingestion",
        "INGESTION_FAILED_OR_CANCELLED",
        "Additional ingestion fails or is cancelled.",
        recovery_rule="Return to recorded previous stable state.",
    ),
    ProjectTransition(
        "ingesting",
        "export_ready",
        ("system", "admin"),
        "fail_or_cancel_ingestion",
        "INGESTION_FAILED_OR_CANCELLED",
        "Additional ingestion fails or is cancelled.",
        recovery_rule="Return to recorded previous stable state.",
    ),
    ProjectTransition(
        "ingesting",
        "ready_for_analysis",
        ("system",),
        "complete_ingestion",
        "INGESTION_COMPLETED",
        "Ingestion completes and source inventory is persisted.",
    ),
    ProjectTransition(
        "ready_for_analysis",
        "analyzing",
        ("analyst", "system"),
        "start_analysis",
        "ANALYSIS_STARTED",
        "Analysis job is created for at least one ingested artifact.",
    ),
    ProjectTransition(
        "review_in_progress",
        "analyzing",
        ("analyst", "system"),
        "start_analysis",
        "ANALYSIS_STARTED",
        "Re-analysis is requested for new source, analyzer version, or explicit reason.",
    ),
    ProjectTransition(
        "export_ready",
        "analyzing",
        ("analyst", "system"),
        "start_analysis",
        "ANALYSIS_STARTED",
        "Re-analysis is requested without new upload.",
        export_impact="Current readiness is revoked.",
    ),
    ProjectTransition(
        "analyzing",
        "review_in_progress",
        ("system",),
        "complete_analysis",
        "ANALYSIS_COMPLETED",
        "Analysis job completes and candidates, gaps, or empty result are persisted.",
    ),
    ProjectTransition(
        "review_in_progress",
        "export_ready",
        ("reviewer", "admin"),
        "pass_export_readiness",
        "EXPORT_READINESS_PASSED",
        "Export readiness validation passes.",
    ),
    ProjectTransition(
        "draft",
        "archived",
        ("admin",),
        "archive_project",
        "PROJECT_ARCHIVED",
        "A non-empty archive reason is supplied.",
    ),
    ProjectTransition(
        "ingesting",
        "archived",
        ("admin",),
        "archive_project",
        "PROJECT_ARCHIVED",
        "A non-empty archive reason is supplied.",
    ),
    ProjectTransition(
        "ready_for_analysis",
        "archived",
        ("admin",),
        "archive_project",
        "PROJECT_ARCHIVED",
        "A non-empty archive reason is supplied.",
    ),
    ProjectTransition(
        "analyzing",
        "archived",
        ("admin",),
        "archive_project",
        "PROJECT_ARCHIVED",
        "A non-empty archive reason is supplied.",
    ),
    ProjectTransition(
        "review_in_progress",
        "archived",
        ("admin",),
        "archive_project",
        "PROJECT_ARCHIVED",
        "A non-empty archive reason is supplied.",
    ),
    ProjectTransition(
        "export_ready",
        "archived",
        ("admin",),
        "archive_project",
        "PROJECT_ARCHIVED",
        "A non-empty archive reason is supplied.",
    ),
)


def _matching_transitions(
    current: ProjectStatus,
    next_status: ProjectStatus,
    command: str | None = None,
) -> Iterable[ProjectTransition]:
    for transition in PROJECT_TRANSITIONS:
        if transition.current != current or transition.next != next_status:
            continue
        if command is not None and transition.command != command:
            continue
        yield transition


def assert_project_transition(
    current: ProjectStatus,
    next_status: ProjectStatus,
    actor: Actor,
    command: str | None = None,
) -> ProjectTransition:
    if current not in PROJECT_STATUSES:
        raise ProjectStateError(f"Unknown current project status: {current}")
    if next_status not in PROJECT_STATUSES:
        raise ProjectStateError(f"Unknown next project status: {next_status}")
    if current == "archived":
        raise ProjectStateError("Archived projects cannot transition in the MVP.")

    for transition in _matching_transitions(current, next_status, command):
        if actor in transition.actors:
            return transition
        raise ProjectStateError(
            f"Actor {actor} cannot transition project from {current} to {next_status}."
        )

    command_text = f" via {command}" if command else ""
    raise ProjectStateError(
        f"Project transition from {current} to {next_status}{command_text} is not allowed."
    )


def next_status_for_source_upload(current: ProjectStatus) -> ProjectStatus:
    assert_project_transition(
        current=current,
        next_status="ingesting",
        actor="analyst",
        command="accept_source_upload",
    )
    return "ingesting"
