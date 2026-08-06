from __future__ import annotations

import hashlib
import html
import io
import stat
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from sqlalchemy.orm import Session

from apps.api.app.audit import record_audit_event
from apps.api.app.config import Settings
from apps.api.app.models import IngestionWarning, Project, SourceArtifact, new_uuid
from apps.api.app.time import utc_now
from packages.domain.project_state import assert_project_transition

ALLOWED_SOURCE_EXTENSIONS = {
    ".cbl",
    ".cob",
    ".cpy",
    ".sql",
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar"}
TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "cp932", "shift_jis", "cp1252", "latin-1")
CONTROL_BYTES = set(range(0, 9)) | {11, 12} | set(range(14, 32))


class IngestionRejectedError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ArtifactIntegrityError(IngestionRejectedError):
    def __init__(self, expected_sha256: str, actual_sha256: str) -> None:
        super().__init__(
            "artifact_integrity_mismatch",
            "Artifact integrity check failed.",
        )
        self.expected_sha256 = expected_sha256
        self.actual_sha256 = actual_sha256


@dataclass(frozen=True)
class ParsedArtifact:
    original_path: str
    content: bytes
    file_extension: str
    size_bytes: int
    sha256: str
    encoding: str
    line_count: int
    warnings: list[ParsedWarning]


@dataclass(frozen=True)
class ParsedWarning:
    original_path: str
    warning_code: str
    message: str


@dataclass(frozen=True)
class ParsedUpload:
    artifacts: list[ParsedArtifact]
    warnings: list[ParsedWarning]


@dataclass(frozen=True)
class IngestionResult:
    project: Project
    artifacts: list[SourceArtifact]
    warnings: list[IngestionWarning]


def parse_source_upload(upload_filename: str | None, content: bytes, settings: Settings) -> ParsedUpload:
    if len(content) > settings.max_upload_bytes:
        raise IngestionRejectedError(
            "upload_too_large",
            "Upload exceeds the configured size limit.",
        )

    if _is_zip_upload(upload_filename, content):
        return _parse_zip_upload(content, settings)
    return _parse_single_file(upload_filename, content, settings)


def ingest_source_upload(
    db: Session,
    project: Project,
    *,
    upload_filename: str | None,
    content: bytes,
    actor_user_id: str,
    actor_role: str,
    request_id: str | None,
    settings: Settings,
) -> IngestionResult:
    previous_status = project.status
    assert_project_transition(previous_status, "ingesting", actor_role, "accept_source_upload")
    project.status = "ingesting"
    project.updated_at = utc_now()
    record_audit_event(
        db,
        "SOURCE_UPLOAD_ACCEPTED",
        actor_user_id=actor_user_id,
        project_id=project.id,
        request_id=request_id,
        payload={
            "filename": upload_filename,
            "previous_status": previous_status,
            "size_bytes": len(content),
        },
    )
    db.flush()

    try:
        parsed = parse_source_upload(upload_filename, content, settings)
    except IngestionRejectedError as exc:
        _restore_previous_status(project, previous_status)
        record_audit_event(
            db,
            "INGESTION_FAILED_OR_CANCELLED",
            actor_user_id=actor_user_id,
            project_id=project.id,
            request_id=request_id,
            payload={
                "code": exc.code,
                "message": exc.message,
                "previous_status": previous_status,
            },
        )
        db.commit()
        raise

    warning_rows = [
        IngestionWarning(
            project_id=project.id,
            artifact_id=None,
            original_path=warning.original_path,
            warning_code=warning.warning_code,
            message=warning.message,
            created_by=actor_user_id,
        )
        for warning in parsed.warnings
    ]
    for warning in warning_rows:
        db.add(warning)

    if not parsed.artifacts:
        _restore_previous_status(project, previous_status)
        record_audit_event(
            db,
            "INGESTION_FAILED_OR_CANCELLED",
            actor_user_id=actor_user_id,
            project_id=project.id,
            request_id=request_id,
            payload={
                "code": "no_supported_artifacts",
                "previous_status": previous_status,
                "warning_count": len(warning_rows),
            },
        )
        db.flush()
        db.commit()
        return IngestionResult(project=project, artifacts=[], warnings=warning_rows)

    artifact_rows: list[SourceArtifact] = []
    written_paths: list[str] = []
    try:
        for parsed_artifact in parsed.artifacts:
            artifact_id = new_uuid()
            storage_path = f"{project.id}/{artifact_id}.source"
            written_paths.append(storage_path)
            write_immutable_artifact(settings, storage_path, parsed_artifact.content)
            artifact = SourceArtifact(
                id=artifact_id,
                project_id=project.id,
                original_path=parsed_artifact.original_path,
                storage_path=storage_path,
                file_extension=parsed_artifact.file_extension,
                size_bytes=parsed_artifact.size_bytes,
                sha256=parsed_artifact.sha256,
                encoding=parsed_artifact.encoding,
                line_count=parsed_artifact.line_count,
                analysis_status="not_analyzed",
                candidate_count=0,
                created_by=actor_user_id,
            )
            db.add(artifact)
            artifact_rows.append(artifact)
            for warning in parsed_artifact.warnings:
                warning_row = IngestionWarning(
                    project_id=project.id,
                    artifact_id=artifact.id,
                    original_path=warning.original_path,
                    warning_code=warning.warning_code,
                    message=warning.message,
                    created_by=actor_user_id,
                )
                db.add(warning_row)
                warning_rows.append(warning_row)

        assert_project_transition("ingesting", "ready_for_analysis", "system", "complete_ingestion")
        project.status = "ready_for_analysis"
        project.updated_at = utc_now()
        record_audit_event(
            db,
            "INGESTION_COMPLETED",
            actor_user_id=actor_user_id,
            project_id=project.id,
            request_id=request_id,
            payload={
                "artifact_count": len(artifact_rows),
                "warning_count": len(warning_rows),
                "sha256": [artifact.sha256 for artifact in artifact_rows],
            },
        )
        db.flush()
        db.commit()
    except Exception as exc:
        db.rollback()
        _remove_uncommitted_artifacts(settings, written_paths)
        _record_persistence_failure(
            db,
            project_id=project.id,
            previous_status=previous_status,
            actor_user_id=actor_user_id,
            request_id=request_id,
            code="ingestion_persistence_failed",
            message=exc.__class__.__name__,
        )
        raise

    return IngestionResult(project=project, artifacts=artifact_rows, warnings=warning_rows)


def record_rejected_upload(
    db: Session,
    project: Project,
    *,
    upload_filename: str | None,
    actor_user_id: str,
    actor_role: str,
    request_id: str | None,
    error: IngestionRejectedError,
    observed_size_bytes: int | None = None,
) -> None:
    previous_status = project.status
    assert_project_transition(previous_status, "ingesting", actor_role, "accept_source_upload")
    project.status = "ingesting"
    project.updated_at = utc_now()
    record_audit_event(
        db,
        "SOURCE_UPLOAD_ACCEPTED",
        actor_user_id=actor_user_id,
        project_id=project.id,
        request_id=request_id,
        payload={
            "filename": upload_filename,
            "previous_status": previous_status,
            "size_bytes": observed_size_bytes,
        },
    )
    _restore_previous_status(project, previous_status)
    record_audit_event(
        db,
        "INGESTION_FAILED_OR_CANCELLED",
        actor_user_id=actor_user_id,
        project_id=project.id,
        request_id=request_id,
        payload={
            "code": error.code,
            "message": error.message,
            "previous_status": previous_status,
        },
    )
    db.commit()


def artifact_absolute_path(settings: Settings, storage_path: str) -> Path:
    root = Path(settings.artifact_storage_root).resolve()
    target = (root / storage_path).resolve()
    if not target.is_relative_to(root):
        raise IngestionRejectedError(
            "storage_path_escape",
            "Artifact storage path is outside the configured storage root.",
        )
    return target


def write_immutable_artifact(settings: Settings, storage_path: str, content: bytes) -> None:
    target = artifact_absolute_path(settings, storage_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as file_handle:
        file_handle.write(content)


def read_artifact_text(artifact: SourceArtifact, settings: Settings) -> str:
    content = artifact_absolute_path(settings, artifact.storage_path).read_bytes()
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != artifact.sha256:
        raise ArtifactIntegrityError(artifact.sha256, actual_sha256)
    return content.decode(artifact.encoding)


def escaped_source_lines(text: str) -> list[dict[str, object]]:
    return [
        {"number": index, "escaped_html": html.escape(line, quote=True)}
        for index, line in enumerate(text.splitlines(), start=1)
    ]


def _restore_previous_status(project: Project, previous_status: str) -> None:
    assert_project_transition("ingesting", previous_status, "system", "fail_or_cancel_ingestion")
    project.status = previous_status
    project.updated_at = utc_now()


def _remove_uncommitted_artifacts(settings: Settings, storage_paths: list[str]) -> None:
    for storage_path in storage_paths:
        try:
            artifact_absolute_path(settings, storage_path).unlink(missing_ok=True)
        except OSError:
            continue


def _record_persistence_failure(
    db: Session,
    *,
    project_id: str,
    previous_status: str,
    actor_user_id: str,
    request_id: str | None,
    code: str,
    message: str,
) -> None:
    try:
        project = db.get(Project, project_id)
        if project is not None and project.status != "archived":
            project.status = previous_status
            project.updated_at = utc_now()
        record_audit_event(
            db,
            "INGESTION_FAILED_OR_CANCELLED",
            actor_user_id=actor_user_id,
            project_id=project_id,
            request_id=request_id,
            payload={
                "code": code,
                "message": message,
                "previous_status": previous_status,
            },
        )
        db.commit()
    except Exception:
        db.rollback()


def _parse_single_file(
    upload_filename: str | None,
    content: bytes,
    settings: Settings,
) -> ParsedUpload:
    original_path = _safe_single_filename(upload_filename, settings)
    artifact, warning = _build_text_artifact(original_path, content)
    return ParsedUpload(
        artifacts=[artifact] if artifact is not None else [],
        warnings=[warning] if warning is not None else [],
    )


def _parse_zip_upload(content: bytes, settings: Settings) -> ParsedUpload:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > settings.max_zip_entries:
                raise IngestionRejectedError(
                    "zip_entry_limit_exceeded",
                    "ZIP entry count exceeds the configured limit.",
                )

            _validate_zip_entries(infos, settings)
            parsed_artifacts: list[ParsedArtifact] = []
            warnings: list[ParsedWarning] = []
            for info in infos:
                if info.is_dir():
                    continue
                normalized_path = _normalized_zip_path(info.filename, settings)
                try:
                    entry_content = archive.read(info)
                except RuntimeError as exc:
                    raise IngestionRejectedError(
                        "zip_entry_read_failed",
                        "ZIP entry could not be read safely.",
                    ) from exc
                artifact, warning = _build_text_artifact(normalized_path, entry_content)
                if artifact is not None:
                    parsed_artifacts.append(artifact)
                if warning is not None:
                    warnings.append(warning)
            return ParsedUpload(artifacts=parsed_artifacts, warnings=warnings)
    except zipfile.BadZipFile as exc:
        raise IngestionRejectedError("invalid_zip", "Upload is not a valid ZIP file.") from exc


def _validate_zip_entries(infos: list[zipfile.ZipInfo], settings: Settings) -> None:
    seen_paths: set[str] = set()
    total_uncompressed = 0
    for info in infos:
        normalized_path = _normalized_zip_path(info.filename, settings)
        if normalized_path in seen_paths:
            raise IngestionRejectedError(
                "zip_duplicate_path",
                "ZIP contains duplicate normalized paths.",
            )
        seen_paths.add(normalized_path)

        if info.flag_bits & 0x1:
            raise IngestionRejectedError("zip_encrypted_entry", "Encrypted ZIP entries are not allowed.")

        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            raise IngestionRejectedError("zip_symlink_blocked", "ZIP symlink entries are not allowed.")

        if PurePosixPath(normalized_path).suffix.lower() in ARCHIVE_EXTENSIONS:
            raise IngestionRejectedError("nested_archive_blocked", "Nested archives are not allowed.")

        total_uncompressed += info.file_size
        if total_uncompressed > settings.max_zip_uncompressed_bytes:
            raise IngestionRejectedError(
                "zip_uncompressed_limit_exceeded",
                "ZIP uncompressed size exceeds the configured limit.",
            )

        if info.is_dir() or info.file_size == 0:
            continue
        if info.compress_size == 0:
            raise IngestionRejectedError(
                "zip_compression_ratio_exceeded",
                "ZIP compression ratio exceeds the configured limit.",
            )
        ratio = info.file_size / info.compress_size
        if ratio > settings.max_zip_compression_ratio:
            raise IngestionRejectedError(
                "zip_compression_ratio_exceeded",
                "ZIP compression ratio exceeds the configured limit.",
            )


def _normalized_zip_path(raw_name: str, settings: Settings) -> str:
    normalized = unicodedata.normalize("NFC", raw_name.replace("\\", "/")).strip()
    if len(normalized) > settings.max_zip_path_length:
        raise IngestionRejectedError(
            "zip_path_too_long",
            "ZIP entry path exceeds the configured length limit.",
        )

    path = PurePosixPath(normalized)
    parts = path.parts
    if path.is_absolute() or not parts:
        raise IngestionRejectedError("zip_path_traversal_blocked", "ZIP entry path is not relative.")
    if any(part in {"", ".", ".."} or ":" in part for part in parts):
        raise IngestionRejectedError("zip_path_traversal_blocked", "ZIP entry path is unsafe.")
    return str(path)


def _safe_single_filename(upload_filename: str | None, settings: Settings) -> str:
    filename = upload_filename or "upload"
    normalized = unicodedata.normalize("NFC", filename.replace("\\", "/")).strip()
    basename = PurePosixPath(normalized).name or "upload"
    if len(basename) > settings.max_zip_path_length:
        raise IngestionRejectedError(
            "filename_too_long",
            "Filename exceeds the configured path length limit.",
        )
    return basename


def _build_text_artifact(
    original_path: str,
    content: bytes,
) -> tuple[ParsedArtifact | None, ParsedWarning | None]:
    extension = PurePosixPath(original_path).suffix.lower()
    if extension not in ALLOWED_SOURCE_EXTENSIONS:
        return None, ParsedWarning(
            original_path=original_path,
            warning_code="unsupported_file_type",
            message=f"Unsupported source file type: {extension or '(none)'}.",
        )
    if _looks_binary(content):
        return None, ParsedWarning(
            original_path=original_path,
            warning_code="binary_file_skipped",
            message="Binary-looking content was skipped and not stored as source.",
        )

    encoding, text = _decode_text(content)
    warnings: list[ParsedWarning] = []
    if encoding == "latin-1":
        warnings.append(
            ParsedWarning(
                original_path=original_path,
                warning_code="encoding_low_confidence",
                message="Source decoded with Latin-1 fallback; encoding should be reviewed.",
            )
        )
    return ParsedArtifact(
        original_path=original_path,
        content=content,
        file_extension=extension,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        encoding=encoding,
        line_count=_line_count(text),
        warnings=warnings,
    ), None


def _decode_text(content: bytes) -> tuple[str, str]:
    for encoding in TEXT_ENCODINGS:
        try:
            return encoding, content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise IngestionRejectedError("unsupported_encoding", "Source text encoding is unsupported.")


def _line_count(text: str) -> int:
    if text == "":
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _looks_binary(content: bytes) -> bool:
    sample = content[:8192]
    if not sample:
        return False
    if b"\x00" in sample:
        return True
    control_count = sum(1 for byte in sample if byte in CONTROL_BYTES)
    return control_count / len(sample) > 0.05


def _is_zip_upload(upload_filename: str | None, content: bytes) -> bool:
    suffix = PurePosixPath((upload_filename or "").lower()).suffix
    if suffix == ".zip":
        return True
    return zipfile.is_zipfile(io.BytesIO(content))
