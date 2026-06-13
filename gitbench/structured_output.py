"""Structured-output contract templates, canonicalization, and validation."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from gitbench.harness.types import Fixture, StructuredOutputContract

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Contract templates — one per benchmark/scoring family
# ---------------------------------------------------------------------------


def _json_schema_object(
    properties: dict[str, Any],
    required: list[str],
    title: str = "",
    description: str = "",
) -> dict[str, Any]:
    """Build a strict JSON Schema object shape.

    Every object-level schema enforces ``additionalProperties: false`` so
    that providers cannot return undeclared keys.
    """
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }
    if title:
        schema["title"] = title
    if description:
        schema["description"] = description
    return schema


# -- Simple scalar templates ------------------------------------------------


def commit_message_template() -> dict[str, Any]:
    """Schema for a single commit-message field."""
    return _json_schema_object(
        properties={
            "commit": {"type": "string", "description": "The commit message"},
        },
        required=["commit"],
        title="CommitMessage",
    )


def command_template() -> dict[str, Any]:
    """Schema for a single git command."""
    return _json_schema_object(
        properties={
            "command": {
                "type": "string",
                "description": "The git command to execute",
            },
        },
        required=["command"],
        title="GitCommand",
    )


def numeric_template() -> dict[str, Any]:
    """Schema for a numeric / count answer."""
    return _json_schema_object(
        properties={
            "count": {
                "type": "integer",
                "description": "The numeric answer",
            },
        },
        required=["count"],
        title="NumericAnswer",
    )


def hash_template() -> dict[str, Any]:
    """Schema for a git commit hash."""
    return _json_schema_object(
        properties={
            "hash": {
                "type": "string",
                "description": "The commit hash",
            },
        },
        required=["hash"],
        title="CommitHash",
    )


def stash_ref_template() -> dict[str, Any]:
    """Schema for a stash reference."""
    return _json_schema_object(
        properties={
            "stash": {
                "type": "string",
                "description": "The stash reference (e.g. stash@{0})",
            },
        },
        required=["stash"],
        title="StashRef",
    )


def reflog_ref_template() -> dict[str, Any]:
    """Schema for a reflog reference."""
    return _json_schema_object(
        properties={
            "ref": {
                "type": "string",
                "description": "The reflog reference",
            },
        },
        required=["ref"],
        title="ReflogRef",
    )


def bisect_commit_template() -> dict[str, Any]:
    """Schema for a bisect bad-commit answer."""
    return _json_schema_object(
        properties={
            "commit": {
                "type": "string",
                "description": "The commit hash or subject of the bad commit",
            },
        },
        required=["commit"],
        title="BisectCommit",
    )


def resolved_content_template() -> dict[str, Any]:
    """Schema for resolved file content (merge-conflicts)."""
    return _json_schema_object(
        properties={
            "resolved_content": {
                "type": "string",
                "description": "The resolved file content",
            },
        },
        required=["resolved_content"],
        title="ResolvedContent",
    )


def json_object_template(properties: dict[str, Any] | None = None) -> dict[str, Any]:
    """Schema for a generic JSON object (json_semantic_equal).

    When no properties are supplied a single ``"value"`` field is used.
    """
    if properties is None:
        properties = {
            "value": {"type": "string", "description": "The JSON value answer"},
        }
    return _json_schema_object(
        properties=properties,
        required=list(properties.keys()),
        title="JsonObject",
    )


# -- Collection templates ---------------------------------------------------


def command_list_template() -> dict[str, Any]:
    """Schema for multiple git commands (one per line in expected text)."""
    return _json_schema_object(
        properties={
            "commands": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The git commands to execute, one per element",
            },
        },
        required=["commands"],
        title="GitCommands",
    )


def branch_list_template() -> dict[str, Any]:
    """Schema for a list of branch names."""
    return _json_schema_object(
        properties={
            "branches_to_delete": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Branch names to delete",
            },
        },
        required=["branches_to_delete"],
        title="BranchList",
    )


def commit_selection_template() -> dict[str, Any]:
    """Schema for a list of commit hashes (commit squashing)."""
    return _json_schema_object(
        properties={
            "commits": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The commit hashes to select",
            },
        },
        required=["commits"],
        title="CommitSelection",
    )


def string_list_template(field_name: str = "items") -> dict[str, Any]:
    """Schema for an order-insensitive list of strings."""
    return _json_schema_object(
        properties={
            field_name: {
                "type": "array",
                "items": {"type": "string"},
                "description": f"The {field_name} list",
            },
        },
        required=[field_name],
        title="StringList",
    )


# ---------------------------------------------------------------------------
# Canonicalization — structured payload → scorer-compatible text
# ---------------------------------------------------------------------------

CANONICALIZE_STRING = "string"
CANONICALIZE_LINES = "lines"
CANONICALIZE_COMMAND_LINES = "command_lines"
CANONICALIZE_NUMERIC_STRING = "numeric_string"
CANONICALIZE_FILE_BLOCK = "file_block"
CANONICALIZE_STASH_REF = "stash_ref"
CANONICALIZE_REFLINE = "refline"


def canonicalize(payload: dict[str, Any], contract: StructuredOutputContract) -> str:
    """Render a structured payload back to scorer-compatible text.

    Args:
        payload: The parsed JSON payload from the model.
        contract: The structured-output contract for this fixture.

    Returns:
        Canonical text suitable for the existing scorer.
    """
    strategy = contract.canonicalize
    primary_path = contract.primary_path

    # Resolve the value at primary_path (supports dotted paths)
    value = _resolve_path(payload, primary_path)

    if strategy == CANONICALIZE_STRING:
        return str(value) if value is not None else ""

    elif strategy == CANONICALIZE_LINES:
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return str(value) if value is not None else ""

    elif strategy == CANONICALIZE_COMMAND_LINES:
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return str(value) if value is not None else ""

    elif strategy == CANONICALIZE_NUMERIC_STRING:
        return str(value) if value is not None else ""

    elif strategy == CANONICALIZE_FILE_BLOCK:
        return str(value) if value is not None else ""

    elif strategy == CANONICALIZE_STASH_REF:
        return str(value) if value is not None else ""

    elif strategy == CANONICALIZE_REFLINE:
        return str(value) if value is not None else ""

    else:
        logger.warning(
            "Unknown canonicalization strategy %r — falling back to string",
            strategy,
        )
        return str(value) if value is not None else ""


def _resolve_path(payload: dict[str, Any], path: str) -> Any:
    """Resolve a dotted path against a dict, e.g. ``commit.hash``."""
    parts = path.split(".")
    current: Any = payload
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


# ---------------------------------------------------------------------------
# Scoring-type → template mapping
# ---------------------------------------------------------------------------

SCORING_TYPE_TEMPLATES: dict[str, tuple[callable, str, str]] = {
    # (template_fn, primary_path, canonicalize_strategy)
    "similarity": (commit_message_template, "commit", "string"),
    "llm_judge": (commit_message_template, "commit", "string"),
    "exact_match": (command_template, "command", "string"),
    "numeric_exact": (numeric_template, "count", "numeric_string"),
    "commit_hash_by_subject": (hash_template, "hash", "string"),
    "unordered_line_set": (string_list_template, "items", "lines"),
    "json_semantic_equal": (json_object_template, "value", "string"),
    "command_equivalence": (command_list_template, "commands", "command_lines"),
    "stash_recovery": (stash_ref_template, "stash", "stash_ref"),
    "reflog_recovery": (reflog_ref_template, "ref", "string"),
    "commit_selection": (commit_selection_template, "commits", "lines"),
    "bisect_regression": (bisect_commit_template, "commit", "string"),
}

# Benchmarks/situations where the default mapping should be overridden.
# Keyed by benchmark name.
BENCHMARK_TEMPLATE_OVERRIDES: dict[str, tuple[callable, str, str]] = {
    "cherry_pick": (resolved_content_template, "resolved_content", "file_block"),
    "merge_conflicts": (resolved_content_template, "resolved_content", "file_block"),
    "rebase": (resolved_content_template, "resolved_content", "file_block"),
    "branch_cleanup": (branch_list_template, "branches_to_delete", "lines"),
    "commit_messages": (commit_message_template, "commit", "string"),
}

# Scoring types that use state_assertions — these don't have a single scalar
# answer field but still benefit from structured output for the command text.
STATE_ASSERTION_BENCHMARKS = {
    "blame_forensics",
    "cherry_pick",
    "git_clean",
    "git_grep",
    "git_log_format",
    "git_show",
    "rebase",
    "submodule_usage",
    "tag_management",
    "worktree_usage",
}


def resolve_contract_for_fixture(fixture: Fixture) -> StructuredOutputContract | None:
    """Resolve or derive a structured-output contract for a fixture.

    Prefers the fixture's explicit ``structured_output`` field.  Falls back
    to deriving a contract from the fixture's scoring type and the benchmark
    family templates.

    Returns ``None`` when no suitable template can be resolved.
    """
    if fixture.structured_output is not None:
        return fixture.structured_output

    scoring_type = fixture.scoring.get("type", "similarity")

    # Determine the benchmark name from the fixture id convention
    # Fixture ids are globally unique but benchmark context may be needed.
    # We check the overrides first, then the generic mapping.
    template_fn, primary_path, canonicalize = SCORING_TYPE_TEMPLATES.get(
        scoring_type, (None, "", "")
    )
    if template_fn is None:
        logger.debug(
            "No structured-output template for scoring type %r (fixture %s)",
            scoring_type,
            fixture.id,
        )
        return None

    return StructuredOutputContract(
        schema=template_fn(),
        primary_path=primary_path,
        canonicalize=canonicalize,
        display_label=primary_path.replace("_", " ").title(),
    )


def contract_for_benchmark_fixture(
    fixture: Fixture,
    benchmark_name: str,
) -> StructuredOutputContract | None:
    """Resolve contract using both generic templates and benchmark overrides.

    Precedence:
    1. Fixture's explicit ``structured_output`` field (always wins).
    2. Benchmark-level override (branch_cleanup, cherry_pick, merge_conflicts, rebase, commit_messages).
    3. Scoring-type-specific template (for special cases within state-assertion benchmarks).
    4. State-assertion benchmark fallback (command_list).
    """
    # Explicit fixture contract always wins
    if fixture.structured_output is not None:
        return fixture.structured_output

    # Benchmark-level override for benchmarks where all fixtures share a shape
    if benchmark_name in BENCHMARK_TEMPLATE_OVERRIDES:
        template_fn, primary_path, canonicalize = BENCHMARK_TEMPLATE_OVERRIDES[benchmark_name]
        return StructuredOutputContract(
            schema=template_fn(),
            primary_path=primary_path,
            canonicalize=canonicalize,
            display_label=primary_path.replace("_", " ").title(),
        )

    scoring_type = fixture.scoring.get("type", "similarity")

    # Scoring-type-specific template (for special cases within state-assertion benchmarks)
    template_fn, primary_path, canonicalize = SCORING_TYPE_TEMPLATES.get(
        scoring_type, (None, "", "")
    )
    if template_fn is not None:
        return StructuredOutputContract(
            schema=template_fn(),
            primary_path=primary_path,
            canonicalize=canonicalize,
            display_label=primary_path.replace("_", " ").title(),
        )

    # For state-assertion benchmarks, use a command-list schema
    if benchmark_name in STATE_ASSERTION_BENCHMARKS:
        return StructuredOutputContract(
            schema=command_list_template(),
            primary_path="commands",
            canonicalize="command_lines",
            display_label="Commands",
        )

    return None


def validate_contract(contract: StructuredOutputContract) -> list[str]:
    """Basic static validation of a structured-output contract.

    Returns a list of error messages (empty when valid).
    """
    errors: list[str] = []
    schema = contract.schema

    if not isinstance(schema, dict):
        errors.append("schema must be a dict")
        return errors

    if schema.get("type") != "object":
        errors.append("schema type must be 'object'")

    if "properties" not in schema:
        errors.append("schema must have 'properties'")
    elif not isinstance(schema["properties"], dict):
        errors.append("schema.properties must be a dict")

    # Check additionalProperties is explicitly false for strict objects
    props = schema.get("properties", {})
    if isinstance(props, dict) and schema.get("additionalProperties") is not False:
        errors.append("schema must set additionalProperties: false for strict objects")

    # Check required fields are present in properties
    required = schema.get("required", [])
    if isinstance(required, list) and isinstance(props, dict):
        for field in required:
            if field not in props:
                errors.append(
                    f"required field '{field}' is not declared in properties"
                )

    if not contract.primary_path:
        errors.append("primary_path is empty")

    return errors


# ---------------------------------------------------------------------------
# Fixture-level validation helpers
# ---------------------------------------------------------------------------


def fixture_expected_as_payload(
    fixture: Fixture,
    contract: StructuredOutputContract,
) -> dict[str, Any] | None:
    """Attempt to represent the fixture's expected answer as a structured payload.

    Returns the payload dict or ``None`` when representation fails.
    """
    primary_path = contract.primary_path
    canonicalize_strategy = contract.canonicalize
    expected = fixture.expected
    schema = contract.schema

    # Determine the target field type from the schema
    props = schema.get("properties", {})
    primary_prop = props.get(primary_path, {})
    prop_type = primary_prop.get("type", "string")

    if prop_type == "array":
        items = [
            line.strip()
            for line in expected.splitlines()
            if line.strip()
        ]
        return {primary_path: items}

    elif prop_type == "integer":
        numbers = re.findall(r"[-+]?\d+", expected)
        if numbers:
            return {primary_path: int(numbers[0])}
        return None

    else:  # string or default
        return {primary_path: expected}


def roundtrip_check(fixture: Fixture, contract: StructuredOutputContract) -> bool:
    """Check that a fixture's expected answer roundtrips through structured payload."""
    payload = fixture_expected_as_payload(fixture, contract)
    if payload is None:
        return False

    # Try canonicalizing and compare against expected (normalized)
    canonical = canonicalize(payload, contract)
    return _texts_match_for_roundtrip(fixture.expected, canonical)


def _texts_match_for_roundtrip(expected: str, canonical: str) -> bool:
    """Check if the canonicalized text matches the expected text for validation."""
    # For exact match, compare directly
    if isinstance(canonical, str):
        return expected.strip() == canonical.strip()

    # For line based, compare sets for unordered
    expected_lines = {line.strip() for line in expected.splitlines() if line.strip()}
    actual_lines = {line.strip() for line in canonical.splitlines() if line.strip()}
    return expected_lines == actual_lines
