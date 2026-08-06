from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

STATIC_ANALYZER_NAME = "static-cobol-mvp"
STATIC_ANALYZER_VERSION = "0.1.0"

SUPPORTED_PATTERN_IDS: tuple[str, ...] = (
    "if_else",
    "evaluate_when",
    "assignment",
    "sql",
    "procedure_call",
    "status_literal",
    "numeric_threshold",
    "date_logic",
    "role_user_check",
    "comment_adjacent_logic",
)

PATTERN_DEFINITIONS: tuple[dict[str, str], ...] = (
    {"id": "if_else", "version": "1", "description": "COBOL IF/ELSE conditional detection"},
    {"id": "evaluate_when", "version": "1", "description": "COBOL EVALUATE/WHEN branch detection"},
    {"id": "assignment", "version": "1", "description": "MOVE, COMPUTE, and SET assignment detection"},
    {"id": "sql", "version": "1", "description": "SQL SELECT/INSERT/UPDATE/DELETE detection"},
    {"id": "procedure_call", "version": "1", "description": "CALL, PERFORM, and CICS LINK detection"},
    {"id": "status_literal", "version": "1", "description": "Status/code/flag literal detection"},
    {"id": "numeric_threshold", "version": "1", "description": "Numeric threshold comparison detection"},
    {"id": "date_logic", "version": "1", "description": "Date/current-date/effective/expiry logic detection"},
    {"id": "role_user_check", "version": "1", "description": "Role/user/auth check detection"},
    {"id": "comment_adjacent_logic", "version": "1", "description": "Comment near executable logic detection"},
)

DEFAULT_CONFIGURATION: dict[str, Any] = {
    "chunk_max_lines": 120,
    "chunk_overlap_lines": 20,
    "enabled_patterns": list(SUPPORTED_PATTERN_IDS),
}

CONFIG_BOUNDS = {
    "chunk_max_lines": (1, 500),
    "chunk_overlap_lines": (0, 200),
}


class StaticExtractionConfigError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CanonicalConfiguration:
    configuration: dict[str, Any]
    configuration_hash: str
    pattern_set_hash: str


@dataclass(frozen=True)
class SourceChunkDraft:
    chunk_index: int
    start_line: int
    end_line: int
    line_count: int
    content: str
    content_hash: str
    chunk_type: str = "line_window"


@dataclass(frozen=True)
class EvidenceDraft:
    start_line: int
    end_line: int
    excerpt: str
    relation_type: str = "supports"


@dataclass(frozen=True)
class CandidateDraft:
    pattern_id: str
    type: str
    title: str
    statement_text: str
    structured_expression: dict[str, Any]
    scope: dict[str, Any]
    confidence: float
    evidence: EvidenceDraft


@dataclass(frozen=True)
class GapDraft:
    pattern_id: str
    gap_type: str
    title: str
    description: str
    severity: str
    identity_source: dict[str, Any]
    evidence: EvidenceDraft


@dataclass(frozen=True)
class QuestionDraft:
    pattern_id: str
    question_type: str
    question_text: str
    priority: str
    identity_source: dict[str, Any]
    evidence: EvidenceDraft


@dataclass(frozen=True)
class ExtractionDraft:
    candidates: list[CandidateDraft]
    gaps: list[GapDraft]
    questions: list[QuestionDraft]


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def pattern_set_hash() -> str:
    return _sha256_text(canonical_json(PATTERN_DEFINITIONS))


def canonicalize_configuration(raw_configuration: dict[str, Any] | None) -> CanonicalConfiguration:
    raw = dict(raw_configuration or {})
    unknown_keys = sorted(set(raw) - set(DEFAULT_CONFIGURATION))
    if unknown_keys:
        raise StaticExtractionConfigError(
            "unknown_configuration_key",
            f"Unsupported analysis configuration key: {unknown_keys[0]}",
        )

    chunk_max_lines = _validated_int(
        raw.get("chunk_max_lines", DEFAULT_CONFIGURATION["chunk_max_lines"]),
        "chunk_max_lines",
    )
    chunk_overlap_lines = _validated_int(
        raw.get("chunk_overlap_lines", DEFAULT_CONFIGURATION["chunk_overlap_lines"]),
        "chunk_overlap_lines",
    )
    if chunk_overlap_lines >= chunk_max_lines:
        raise StaticExtractionConfigError(
            "invalid_chunk_overlap",
            "chunk_overlap_lines must be lower than chunk_max_lines.",
        )

    enabled_patterns = raw.get("enabled_patterns", DEFAULT_CONFIGURATION["enabled_patterns"])
    if not isinstance(enabled_patterns, list) or not enabled_patterns:
        raise StaticExtractionConfigError(
            "invalid_enabled_patterns",
            "enabled_patterns must be a non-empty list.",
        )
    if any(not isinstance(pattern, str) for pattern in enabled_patterns):
        raise StaticExtractionConfigError(
            "invalid_enabled_patterns",
            "enabled_patterns may contain only string pattern IDs.",
        )

    unsupported = sorted(set(enabled_patterns) - set(SUPPORTED_PATTERN_IDS))
    if unsupported:
        raise StaticExtractionConfigError(
            "unsupported_pattern",
            f"Unsupported analysis pattern: {unsupported[0]}",
        )

    enabled_set = set(enabled_patterns)
    canonical = {
        "chunk_max_lines": chunk_max_lines,
        "chunk_overlap_lines": chunk_overlap_lines,
        "enabled_patterns": [pattern for pattern in SUPPORTED_PATTERN_IDS if pattern in enabled_set],
    }
    return CanonicalConfiguration(
        configuration=canonical,
        configuration_hash=_sha256_text(canonical_json(canonical)),
        pattern_set_hash=pattern_set_hash(),
    )


def _validated_int(value: Any, key: str) -> int:
    lower, upper = CONFIG_BOUNDS[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise StaticExtractionConfigError("invalid_configuration_value", f"{key} must be an integer.")
    if value < lower or value > upper:
        raise StaticExtractionConfigError(
            "configuration_value_out_of_bounds",
            f"{key} must be between {lower} and {upper}.",
        )
    return value


def make_source_chunks(text: str, configuration: dict[str, Any]) -> list[SourceChunkDraft]:
    lines = text.splitlines()
    if not lines:
        return []

    max_lines = int(configuration["chunk_max_lines"])
    overlap = int(configuration["chunk_overlap_lines"])
    step = max_lines - overlap
    chunks: list[SourceChunkDraft] = []
    start = 0
    while start < len(lines):
        end = min(start + max_lines, len(lines))
        chunk_lines = lines[start:end]
        content = "\n".join(chunk_lines)
        chunks.append(
            SourceChunkDraft(
                chunk_index=len(chunks),
                start_line=start + 1,
                end_line=end,
                line_count=len(chunk_lines),
                content=content,
                content_hash=_sha256_text(content),
            )
        )
        if end >= len(lines):
            break
        start += step
    return chunks


def extract_from_chunks(
    chunks: list[SourceChunkDraft],
    configuration: dict[str, Any],
) -> dict[int, ExtractionDraft]:
    enabled_patterns = set(configuration["enabled_patterns"])
    result: dict[int, ExtractionDraft] = {}
    for chunk in chunks:
        candidates: list[CandidateDraft] = []
        gaps: list[GapDraft] = []
        questions: list[QuestionDraft] = []
        indexed_lines = _indexed_lines(chunk)

        for relative_index, line in indexed_lines:
            absolute_line = chunk.start_line + relative_index
            normalized = line.strip()
            upper = normalized.upper()
            evidence = _single_line_evidence(absolute_line, line)

            if "if_else" in enabled_patterns:
                candidate = _if_else_candidate(upper, normalized, absolute_line, evidence)
                if candidate:
                    candidates.append(candidate)
            if "evaluate_when" in enabled_patterns:
                candidate = _evaluate_when_candidate(upper, normalized, absolute_line, evidence)
                if candidate:
                    candidates.append(candidate)
            if "assignment" in enabled_patterns:
                candidate = _assignment_candidate(upper, normalized, absolute_line, evidence)
                if candidate:
                    candidates.append(candidate)
            if "sql" in enabled_patterns:
                candidate = _sql_candidate(upper, normalized, absolute_line, evidence)
                if candidate:
                    candidates.append(candidate)
            if "procedure_call" in enabled_patterns:
                candidate = _procedure_call_candidate(upper, normalized, absolute_line, evidence)
                if candidate:
                    candidates.append(candidate)
                    gaps.append(_external_call_gap(candidate, evidence))
            if "status_literal" in enabled_patterns:
                candidate = _status_literal_candidate(upper, normalized, absolute_line, evidence)
                if candidate:
                    candidates.append(candidate)
            if "numeric_threshold" in enabled_patterns:
                candidate = _numeric_threshold_candidate(upper, normalized, absolute_line, evidence)
                if candidate:
                    candidates.append(candidate)
            if "date_logic" in enabled_patterns:
                candidate = _date_logic_candidate(upper, normalized, absolute_line, evidence)
                if candidate:
                    candidates.append(candidate)
            if "role_user_check" in enabled_patterns:
                candidate = _role_user_check_candidate(upper, normalized, absolute_line, evidence)
                if candidate:
                    candidates.append(candidate)

            question = _question_from_uncertainty(upper, normalized, absolute_line, evidence)
            if question:
                questions.append(question)

        if "comment_adjacent_logic" in enabled_patterns:
            candidates.extend(_comment_adjacent_candidates(indexed_lines, chunk.start_line))

        result[chunk.chunk_index] = ExtractionDraft(
            candidates=_dedupe_candidates(candidates),
            gaps=_dedupe_gaps(gaps),
            questions=_dedupe_questions(questions),
        )
    return result


def candidate_identity_hash(
    *,
    artifact_sha256: str,
    analyzer_name: str,
    analyzer_version: str,
    configuration_hash: str,
    pattern_id: str,
    statement_type: str,
    scope: dict[str, Any],
    structured_expression: dict[str, Any],
    evidence_ranges: list[dict[str, Any]],
) -> str:
    identity = {
        "artifact_sha256": artifact_sha256,
        "analyzer_name": analyzer_name,
        "analyzer_version": analyzer_version,
        "configuration_hash": configuration_hash,
        "pattern_id": pattern_id,
        "statement_type": statement_type,
        "scope": scope,
        "structured_expression": structured_expression,
        "evidence_ranges": sorted(evidence_ranges, key=lambda row: canonical_json(row)),
    }
    return _sha256_text(canonical_json(identity))


def generic_identity_hash(kind: str, identity_source: dict[str, Any]) -> str:
    return _sha256_text(canonical_json({"kind": kind, "source": identity_source}))


def _indexed_lines(chunk: SourceChunkDraft) -> list[tuple[int, str]]:
    return list(enumerate(chunk.content.splitlines()))


def _single_line_evidence(line_number: int, line: str) -> EvidenceDraft:
    return EvidenceDraft(start_line=line_number, end_line=line_number, excerpt=line)


def _if_else_candidate(
    upper: str,
    normalized: str,
    line_number: int,
    evidence: EvidenceDraft,
) -> CandidateDraft | None:
    if not re.match(r"^IF\s+.+", upper):
        return None
    condition = re.sub(r"^IF\s+", "", normalized, flags=re.IGNORECASE).strip().rstrip(".")
    return CandidateDraft(
        pattern_id="if_else",
        type="business_rule",
        title=f"Conditional rule at line {line_number}",
        statement_text=f"Source defines conditional logic for `{condition}`.",
        structured_expression={"kind": "if", "condition": condition},
        scope={"line": line_number},
        confidence=0.78,
        evidence=evidence,
    )


def _evaluate_when_candidate(
    upper: str,
    normalized: str,
    line_number: int,
    evidence: EvidenceDraft,
) -> CandidateDraft | None:
    if not (upper.startswith("EVALUATE ") or upper.startswith("WHEN ")):
        return None
    branch = "evaluate" if upper.startswith("EVALUATE ") else "when"
    expression = re.sub(r"^(EVALUATE|WHEN)\s+", "", normalized, flags=re.IGNORECASE).strip().rstrip(".")
    return CandidateDraft(
        pattern_id="evaluate_when",
        type="decision_table",
        title=f"EVALUATE/WHEN branch at line {line_number}",
        statement_text=f"Source defines a {branch} branch for `{expression}`.",
        structured_expression={"kind": branch, "expression": expression},
        scope={"line": line_number},
        confidence=0.8,
        evidence=evidence,
    )


def _assignment_candidate(
    upper: str,
    normalized: str,
    line_number: int,
    evidence: EvidenceDraft,
) -> CandidateDraft | None:
    move_match = re.search(r"\bMOVE\s+(.+?)\s+TO\s+(.+?)(?:\.|$)", normalized, re.IGNORECASE)
    compute_match = re.search(r"\bCOMPUTE\s+(.+?)\s*=\s*(.+?)(?:\.|$)", normalized, re.IGNORECASE)
    set_match = re.search(r"\bSET\s+(.+?)\s+TO\s+(.+?)(?:\.|$)", normalized, re.IGNORECASE)
    if move_match:
        source, target = move_match.group(1).strip(), move_match.group(2).strip()
        verb = "MOVE"
    elif compute_match:
        target, source = compute_match.group(1).strip(), compute_match.group(2).strip()
        verb = "COMPUTE"
    elif set_match:
        target, source = set_match.group(1).strip(), set_match.group(2).strip()
        verb = "SET"
    else:
        return None
    return CandidateDraft(
        pattern_id="assignment",
        type="data_mapping",
        title=f"{verb} assignment at line {line_number}",
        statement_text=f"Source assigns `{source}` to `{target}`.",
        structured_expression={"kind": verb.lower(), "source": source, "target": target},
        scope={"line": line_number, "target": target},
        confidence=0.74,
        evidence=evidence,
    )


def _sql_candidate(
    upper: str,
    normalized: str,
    line_number: int,
    evidence: EvidenceDraft,
) -> CandidateDraft | None:
    match = re.search(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", upper)
    if not match:
        return None
    operation = match.group(1).lower()
    return CandidateDraft(
        pattern_id="sql",
        type="data_access",
        title=f"SQL {operation.upper()} at line {line_number}",
        statement_text=f"Source references SQL `{operation.upper()}` data access.",
        structured_expression={"kind": "sql", "operation": operation, "text": normalized},
        scope={"line": line_number, "operation": operation},
        confidence=0.72,
        evidence=evidence,
    )


def _procedure_call_candidate(
    upper: str,
    normalized: str,
    line_number: int,
    evidence: EvidenceDraft,
) -> CandidateDraft | None:
    call_match = re.search(r"\bCALL\s+['\"]?([A-Z0-9_-]+)['\"]?", upper)
    cics_match = re.search(r"\bPROGRAM\s*\(\s*['\"]?([A-Z0-9_-]+)['\"]?\s*\)", upper)
    perform_match = re.search(r"\bPERFORM\s+([A-Z0-9_-]+)", upper)
    if call_match:
        target = call_match.group(1)
        call_kind = "call"
    elif cics_match:
        target = cics_match.group(1)
        call_kind = "cics_link"
    elif perform_match:
        target = perform_match.group(1)
        call_kind = "perform"
    else:
        return None
    return CandidateDraft(
        pattern_id="procedure_call",
        type="process_step",
        title=f"Procedure call to {target}",
        statement_text=f"Source invokes `{target}` through {call_kind}.",
        structured_expression={"kind": call_kind, "target": target},
        scope={"line": line_number, "target": target},
        confidence=0.7,
        evidence=evidence,
    )


def _status_literal_candidate(
    upper: str,
    normalized: str,
    line_number: int,
    evidence: EvidenceDraft,
) -> CandidateDraft | None:
    if not re.search(r"\b(STATUS|STATE|CODE|FLAG)\b", upper):
        return None
    literal_match = re.search(r"['\"]([A-Z0-9_-]{2,})['\"]", upper)
    literal = literal_match.group(1) if literal_match else normalized
    return CandidateDraft(
        pattern_id="status_literal",
        type="status_rule",
        title=f"Status literal at line {line_number}",
        statement_text=f"Source references status/code literal `{literal}`.",
        structured_expression={"kind": "status_literal", "literal": literal, "text": normalized},
        scope={"line": line_number},
        confidence=0.68,
        evidence=evidence,
    )


def _numeric_threshold_candidate(
    upper: str,
    normalized: str,
    line_number: int,
    evidence: EvidenceDraft,
) -> CandidateDraft | None:
    symbol_match = re.search(r"(>=|<=|>|<|=)\s*(-?\d+(?:\.\d+)?)", normalized)
    word_match = re.search(r"\b(GREATER THAN|LESS THAN|EQUAL TO)\s+(-?\d+(?:\.\d+)?)", upper)
    if symbol_match:
        operator, value = symbol_match.group(1), symbol_match.group(2)
    elif word_match:
        operator, value = word_match.group(1).lower(), word_match.group(2)
    else:
        return None
    return CandidateDraft(
        pattern_id="numeric_threshold",
        type="threshold_rule",
        title=f"Numeric threshold at line {line_number}",
        statement_text=f"Source compares a value with `{operator} {value}`.",
        structured_expression={"kind": "numeric_threshold", "operator": operator, "value": value},
        scope={"line": line_number},
        confidence=0.67,
        evidence=evidence,
    )


def _date_logic_candidate(
    upper: str,
    normalized: str,
    line_number: int,
    evidence: EvidenceDraft,
) -> CandidateDraft | None:
    if not re.search(r"\b(DATE|CURRENT-DATE|YYYY|YYMM|EXPIR|EFFECTIVE)\b", upper):
        return None
    return CandidateDraft(
        pattern_id="date_logic",
        type="date_rule",
        title=f"Date logic at line {line_number}",
        statement_text="Source references date-sensitive logic.",
        structured_expression={"kind": "date_logic", "text": normalized},
        scope={"line": line_number},
        confidence=0.64,
        evidence=evidence,
    )


def _role_user_check_candidate(
    upper: str,
    normalized: str,
    line_number: int,
    evidence: EvidenceDraft,
) -> CandidateDraft | None:
    if not re.search(r"\b(USER|ROLE|AUTH|PERMISSION|SECURITY)\b", upper):
        return None
    return CandidateDraft(
        pattern_id="role_user_check",
        type="access_rule",
        title=f"Role/user check at line {line_number}",
        statement_text="Source references user, role, authorization, or permission logic.",
        structured_expression={"kind": "role_user_check", "text": normalized},
        scope={"line": line_number},
        confidence=0.65,
        evidence=evidence,
    )


def _comment_adjacent_candidates(
    indexed_lines: list[tuple[int, str]],
    chunk_start_line: int,
) -> list[CandidateDraft]:
    candidates: list[CandidateDraft] = []
    for offset, line in indexed_lines:
        stripped = line.strip()
        if not _is_comment(stripped):
            continue
        next_line = indexed_lines[offset + 1][1] if offset + 1 < len(indexed_lines) else ""
        previous_line = indexed_lines[offset - 1][1] if offset > 0 else ""
        adjacent = next_line.strip() or previous_line.strip()
        if not adjacent or not _looks_like_logic(adjacent):
            continue
        line_number = chunk_start_line + offset
        adjacent_line = line_number + 1 if next_line.strip() else line_number - 1
        start_line, end_line = sorted((line_number, adjacent_line))
        excerpt = "\n".join(row for _, row in indexed_lines[start_line - chunk_start_line : end_line - chunk_start_line + 1])
        evidence = EvidenceDraft(start_line=start_line, end_line=end_line, excerpt=excerpt)
        candidates.append(
            CandidateDraft(
                pattern_id="comment_adjacent_logic",
                type="business_rule",
                title=f"Comment-adjacent logic near line {line_number}",
                statement_text="Source has business comment context adjacent to executable-looking logic.",
                structured_expression={"kind": "comment_adjacent_logic", "comment": stripped, "logic": adjacent},
                scope={"line": line_number, "adjacent_line": adjacent_line},
                confidence=0.58,
                evidence=evidence,
            )
        )
    return candidates


def _external_call_gap(candidate: CandidateDraft, evidence: EvidenceDraft) -> GapDraft:
    target = candidate.structured_expression.get("target", "external target")
    return GapDraft(
        pattern_id="procedure_call",
        gap_type="missing_dependency",
        title=f"External dependency requires review: {target}",
        description=f"Static extraction found a call to `{target}`, but Phase 3 does not resolve external program behavior.",
        severity="medium",
        identity_source={
            "pattern_id": "procedure_call",
            "target": target,
            "range": [evidence.start_line, evidence.end_line],
        },
        evidence=evidence,
    )


def _question_from_uncertainty(
    upper: str,
    normalized: str,
    line_number: int,
    evidence: EvidenceDraft,
) -> QuestionDraft | None:
    if not re.search(r"\b(TODO|TBD|UNKNOWN|MANUAL|VERIFY)\b", upper):
        return None
    return QuestionDraft(
        pattern_id="comment_adjacent_logic",
        question_type="missing_business_context",
        question_text=f"Review unresolved source note at line {line_number}: {normalized}",
        priority="medium",
        identity_source={"line": line_number, "text": normalized},
        evidence=evidence,
    )


def _dedupe_candidates(candidates: list[CandidateDraft]) -> list[CandidateDraft]:
    seen: set[str] = set()
    result: list[CandidateDraft] = []
    for candidate in candidates:
        key = canonical_json(
            {
                "pattern_id": candidate.pattern_id,
                "type": candidate.type,
                "scope": candidate.scope,
                "structured": candidate.structured_expression,
                "range": [candidate.evidence.start_line, candidate.evidence.end_line],
            }
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def _dedupe_gaps(gaps: list[GapDraft]) -> list[GapDraft]:
    seen: set[str] = set()
    result: list[GapDraft] = []
    for gap in gaps:
        key = canonical_json(gap.identity_source)
        if key in seen:
            continue
        seen.add(key)
        result.append(gap)
    return result


def _dedupe_questions(questions: list[QuestionDraft]) -> list[QuestionDraft]:
    seen: set[str] = set()
    result: list[QuestionDraft] = []
    for question in questions:
        key = canonical_json(question.identity_source)
        if key in seen:
            continue
        seen.add(key)
        result.append(question)
    return result


def _is_comment(stripped: str) -> bool:
    return stripped.startswith("*") or stripped.startswith("*>") or stripped.startswith("--")


def _looks_like_logic(line: str) -> bool:
    upper = line.upper()
    return bool(
        re.search(
            r"\b(IF|EVALUATE|WHEN|MOVE|COMPUTE|SET|CALL|PERFORM|SELECT|INSERT|UPDATE|DELETE)\b",
            upper,
        )
    )
