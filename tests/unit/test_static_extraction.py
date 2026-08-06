from __future__ import annotations

import pytest

from packages.extraction.static import (
    STATIC_ANALYZER_NAME,
    STATIC_ANALYZER_VERSION,
    StaticExtractionConfigError,
    candidate_identity_hash,
    canonicalize_configuration,
    extract_from_chunks,
    make_source_chunks,
)


def test_chunking_is_deterministic_and_preserves_line_ranges() -> None:
    config = canonicalize_configuration({"chunk_max_lines": 3, "chunk_overlap_lines": 1}).configuration
    text = "\n".join(["L1", "L2", "L3", "L4", "L5"])

    first = make_source_chunks(text, config)
    second = make_source_chunks(text, config)

    assert first == second
    assert [(chunk.start_line, chunk.end_line) for chunk in first] == [(1, 3), (3, 5)]
    assert first[0].content == "L1\nL2\nL3"
    assert first[1].content == "L3\nL4\nL5"


def test_static_patterns_create_candidates_gaps_and_questions_with_evidence() -> None:
    config = canonicalize_configuration({"chunk_max_lines": 20, "chunk_overlap_lines": 0}).configuration
    text = "\n".join(
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

    chunks = make_source_chunks(text, config)
    extraction = extract_from_chunks(chunks, config)[0]
    pattern_ids = {candidate.pattern_id for candidate in extraction.candidates}

    assert {
        "if_else",
        "assignment",
        "evaluate_when",
        "sql",
        "procedure_call",
        "status_literal",
        "numeric_threshold",
        "date_logic",
        "role_user_check",
        "comment_adjacent_logic",
    }.issubset(pattern_ids)
    assert extraction.gaps
    assert extraction.questions
    assert all(candidate.evidence.start_line >= 1 for candidate in extraction.candidates)


def test_unknown_config_and_unsupported_patterns_are_rejected() -> None:
    with pytest.raises(StaticExtractionConfigError, match="Unsupported analysis configuration key"):
        canonicalize_configuration({"analyzer_name": "client-owned"})

    with pytest.raises(StaticExtractionConfigError, match="Unsupported analysis pattern"):
        canonicalize_configuration({"enabled_patterns": ["if_else", "made_up"]})


def test_candidate_identity_does_not_depend_on_statement_text() -> None:
    common = {
        "artifact_sha256": "a" * 64,
        "analyzer_name": STATIC_ANALYZER_NAME,
        "analyzer_version": STATIC_ANALYZER_VERSION,
        "configuration_hash": "b" * 64,
        "pattern_id": "if_else",
        "statement_type": "business_rule",
        "scope": {"line": 10},
        "structured_expression": {"kind": "if", "condition": "AMOUNT > 1000"},
        "evidence_ranges": [
            {
                "artifact_sha256": "a" * 64,
                "start_line": 10,
                "end_line": 10,
                "relation_type": "supports",
            }
        ],
    }

    first = candidate_identity_hash(**common)
    second = candidate_identity_hash(**common)

    assert first == second
