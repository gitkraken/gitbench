"""Structured-output contract templates, canonicalization, and validation."""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

from gitbench.harness.types import Fixture, StructuredOutputContract

logger = logging.getLogger(__name__)


class StructuredOutputParseError(ValueError):
    """Raised when a model response is not strict, finite JSON."""


class StructuredOutputSchemaError(ValueError):
    """Raised when parsed structured output violates its fixture schema."""


def strict_json_loads(text: str) -> Any:
    """Parse standard JSON and reject all non-finite numeric values."""

    def reject_constant(value: str) -> None:
        raise StructuredOutputParseError(
            f"non-standard JSON constant {value!r} is not allowed"
        )

    try:
        payload = json.loads(text, parse_constant=reject_constant)
    except StructuredOutputParseError:
        raise
    except json.JSONDecodeError as exc:
        raise StructuredOutputParseError(str(exc)) from exc

    _reject_non_finite(payload)
    return payload


def _reject_non_finite(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise StructuredOutputParseError(f"non-finite number at {path} is not allowed")
    if isinstance(value, dict):
        for key, child in value.items():
            _reject_non_finite(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_non_finite(child, f"{path}[{index}]")


def validate_structured_payload(
    payload: Any,
    contract: StructuredOutputContract,
) -> None:
    """Validate a parsed payload against the JSON Schema subset GitBench emits."""
    errors: list[str] = []
    _validate_schema_value(payload, contract.schema, "$", errors)
    if errors:
        raise StructuredOutputSchemaError(errors[0])


def _validate_schema_value(
    value: Any,
    schema: dict[str, Any],
    path: str,
    errors: list[str],
) -> None:
    if errors:
        return

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path} must equal {schema['const']!r}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} must be one of {schema['enum']!r}")
        return

    expected_type = schema.get("type")
    if expected_type is not None and not _matches_json_type(value, expected_type):
        errors.append(f"{path} must be of type {expected_type}")
        return

    if expected_type == "object":
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path} is missing required property {required!r}")
                return
        for key, child in value.items():
            child_schema = properties.get(key)
            if child_schema is not None:
                _validate_schema_value(child, child_schema, f"{path}.{key}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path} contains undeclared property {key!r}")
            elif isinstance(schema.get("additionalProperties"), dict):
                _validate_schema_value(
                    child,
                    schema["additionalProperties"],
                    f"{path}.{key}",
                    errors,
                )
            if errors:
                return
    elif expected_type == "array":
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path} must contain at least {schema['minItems']} items")
            return
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path} must contain at most {schema['maxItems']} items")
            return
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, child in enumerate(value):
                _validate_schema_value(child, item_schema, f"{path}[{index}]", errors)
                if errors:
                    return
    elif expected_type == "string":
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path} must contain at least {schema['minLength']} characters")
        elif "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path} must contain at most {schema['maxLength']} characters")
        elif "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{path} must match pattern {schema['pattern']!r}")
    elif expected_type in ("integer", "number"):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path} must be at least {schema['minimum']}")
        elif "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path} must be at most {schema['maximum']}")


def _matches_json_type(value: Any, expected_type: str | list[str]) -> bool:
    if isinstance(expected_type, list):
        return any(_matches_json_type(value, item) for item in expected_type)
    if expected_type == "null":
        return value is None
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and (not isinstance(value, float) or math.isfinite(value))
        )
    return False


# ---------------------------------------------------------------------------
# Canonicalization — structured payload → scorer-compatible text
# ---------------------------------------------------------------------------

CANONICALIZE_STRING = "string"
CANONICALIZE_LINES = "lines"
CANONICALIZE_COMMAND_LINES = "command_lines"
CANONICALIZE_NUMERIC_STRING = "numeric_string"
CANONICALIZE_FILE_BLOCK = "file_block"
CANONICALIZE_FILE_BLOCKS = "file_blocks"
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

    elif strategy == CANONICALIZE_FILE_BLOCKS:
        if isinstance(value, dict):
            parts = []
            for filename in sorted(value):
                content = str(value[filename]).rstrip("\n")
                parts.append(f"{filename}:\n{content}")
            return "\n\n".join(parts)
        return ""

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
# Named schema registry
# ---------------------------------------------------------------------------

class SchemaResolutionError(ValueError):
    """Raised when no structured-output schema can be resolved for a fixture."""


def _registry_entry(
    key: str,
    key_type: str,
    description: str,
    canonicalize: str,
    title: str = "",
    display_label: str = "",
) -> StructuredOutputContract:
    """Create a SCHEMA_REGISTRY entry as a complete StructuredOutputContract."""
    if key_type == "array":
        prop: dict[str, Any] = {
            "type": "array",
            "items": {"type": "string"},
            "description": description,
        }
    else:
        prop = {
            "type": key_type,
            "description": description,
        }
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {key: prop},
        "required": [key],
        "additionalProperties": False,
    }
    if title:
        schema["title"] = title
    return StructuredOutputContract(
        schema=schema,
        primary_path=key,
        canonicalize=canonicalize,
        display_label=display_label or key.replace("_", " ").title(),
    )


SCHEMA_REGISTRY: dict[str, StructuredOutputContract] = {
    "commit_message": _registry_entry(
        key="commit_message",
        key_type="string",
        description="The commit message of the identified commit",
        canonicalize=CANONICALIZE_STRING,
        title="CommitMessage",
    ),
    "bisect_commit": _registry_entry(
        key="commit",
        key_type="string",
        description="The commit hash or subject of the bad commit",
        canonicalize=CANONICALIZE_STRING,
        title="BisectCommit",
    ),
    "commit_selection": _registry_entry(
        key="commits",
        key_type="array",
        description="The commit hashes or subjects to select for squashing",
        canonicalize=CANONICALIZE_LINES,
        title="CommitSelection",
    ),
    "hash": _registry_entry(
        key="hash",
        key_type="string",
        description="The commit hash",
        canonicalize=CANONICALIZE_STRING,
        title="CommitHash",
    ),
    "command": _registry_entry(
        key="command",
        key_type="string",
        description="The git command to execute",
        canonicalize=CANONICALIZE_STRING,
        title="GitCommand",
    ),
    "command_list": _registry_entry(
        key="commands",
        key_type="array",
        description="The git commands to execute, one per element",
        canonicalize=CANONICALIZE_COMMAND_LINES,
        title="GitCommands",
    ),
    "stash_ref": _registry_entry(
        key="stash",
        key_type="string",
        description="The stash reference (e.g. stash@{0})",
        canonicalize=CANONICALIZE_STASH_REF,
        title="StashRef",
    ),
    "reflog_ref": _registry_entry(
        key="ref",
        key_type="string",
        description="The reflog reference",
        canonicalize=CANONICALIZE_STRING,
        title="ReflogRef",
    ),
    "resolved_content": _registry_entry(
        key="resolved_content",
        key_type="string",
        description="The resolved file content",
        canonicalize=CANONICALIZE_FILE_BLOCK,
        title="ResolvedContent",
    ),
    "resolved_file_blocks": StructuredOutputContract(
        schema={
            "title": "ResolvedFileBlocks",
            "type": "object",
            "properties": {
                "files": {
                    "type": "object",
                    "description": "Resolved file contents keyed by filename",
                    "additionalProperties": {"type": "string"},
                }
            },
            "required": ["files"],
            "additionalProperties": False,
        },
        primary_path="files",
        canonicalize=CANONICALIZE_FILE_BLOCKS,
        display_label="Resolved Files",
    ),
    "branch_list": _registry_entry(
        key="branches_to_delete",
        key_type="array",
        description="Branch names to delete",
        canonicalize=CANONICALIZE_LINES,
        title="BranchList",
    ),
    "string_list": _registry_entry(
        key="items",
        key_type="array",
        description="The list of matching items",
        canonicalize=CANONICALIZE_LINES,
        title="StringList",
    ),
    "count": _registry_entry(
        key="count",
        key_type="integer",
        description="The numeric count",
        canonicalize=CANONICALIZE_NUMERIC_STRING,
        title="NumericAnswer",
    ),
    "email": _registry_entry(
        key="email",
        key_type="string",
        description="The email address",
        canonicalize=CANONICALIZE_STRING,
        title="Email",
    ),
    "filename": _registry_entry(
        key="filename",
        key_type="string",
        description="The file name",
        canonicalize=CANONICALIZE_STRING,
        title="Filename",
    ),
    "file_content": _registry_entry(
        key="content",
        key_type="string",
        description="The file content",
        canonicalize=CANONICALIZE_STRING,
        title="FileContent",
    ),
    "file_list": _registry_entry(
        key="files",
        key_type="array",
        description="The matching file names",
        canonicalize=CANONICALIZE_LINES,
        title="FileList",
    ),
    "file_status": _registry_entry(
        key="status_code",
        key_type="string",
        description="The git status code (A, M, R, D, etc.)",
        canonicalize=CANONICALIZE_STRING,
        title="FileStatus",
    ),
    "commit_message_list": _registry_entry(
        key="commit_message_list",
        key_type="array",
        description="The list of commit messages",
        canonicalize=CANONICALIZE_LINES,
        title="CommitMessageList",
    ),
    "yes_no": _registry_entry(
        key="found",
        key_type="string",
        description="Whether the search found matches (yes or no)",
        canonicalize=CANONICALIZE_STRING,
        title="YesNo",
    ),
    "line_numbers": _registry_entry(
        key="line_numbers",
        key_type="string",
        description="The line numbers where the pattern appears, comma-separated",
        canonicalize=CANONICALIZE_STRING,
        title="LineNumbers",
    ),
    "version_number": _registry_entry(
        key="version_number",
        key_type="string",
        description="The version number found",
        canonicalize=CANONICALIZE_STRING,
        title="VersionNumber",
    ),
}


# ---------------------------------------------------------------------------
# Benchmark defaults and scoring-type fallbacks
# ---------------------------------------------------------------------------

BENCHMARK_DEFAULT_SCHEMAS: dict[str, str] = {
    "blame_forensics": "commit_message",
    "commit_messages": "commit_message",
    "git_clean": "command",
    "tag_management": "command",
    "worktree_usage": "command",
    "submodule_usage": "command",
    "cherry_pick": "resolved_content",
    "merge_conflicts": "resolved_content",
    "rebase": "resolved_content",
    "branch_cleanup": "branch_list",
    "stash_recovery": "stash_ref",
    "reflog": "reflog_ref",
    "git_bisect": "bisect_commit",
    "commit_squash": "commit_selection",
}

SCORING_TYPE_FALLBACKS: dict[str, str] = {
    "numeric_exact": "count",
    "commit_hash_by_subject": "hash",
    "unordered_line_set": "string_list",
    "command_equivalence": "command_list",
    "stash_recovery": "stash_ref",
    "reflog_recovery": "reflog_ref",
    "bisect_regression": "bisect_commit",
    "commit_selection": "commit_selection",
    "llm_judge": "commit_message",
    "similarity": "commit_message",
    "state_assertions": "command_list",
    "resolved_file_blocks": "resolved_file_blocks",
}


def contract_for_benchmark_fixture(
    fixture: Fixture,
    benchmark_name: str,
) -> StructuredOutputContract:
    """Resolve a structured-output contract using the named schema registry.

    Precedence:
    0. Fixture's explicit ``structured_output`` field (backward compat, always wins).
    1. Fixture's ``output_schema`` field → SCHEMA_REGISTRY lookup.
    2. BENCHMARK_DEFAULT_SCHEMAS[benchmark_name] → SCHEMA_REGISTRY lookup.
    3. SCORING_TYPE_FALLBACKS[scoring_type] → SCHEMA_REGISTRY lookup.
    4. Error: no resolution found.
    """
    # 0. Explicit structured_output contract (backward compatibility)
    if fixture.structured_output is not None:
        return fixture.structured_output

    # 1. Fixture-level output_schema override
    if fixture.output_schema is not None:
        schema_name = fixture.output_schema
        if schema_name not in SCHEMA_REGISTRY:
            raise SchemaResolutionError(
                f"Fixture {fixture.id} ({benchmark_name}): "
                f"output_schema references unknown schema '{schema_name}'. "
                f"Available schemas: {sorted(SCHEMA_REGISTRY.keys())}"
            )
        return SCHEMA_REGISTRY[schema_name]

    # 2. Benchmark-level default
    if benchmark_name in BENCHMARK_DEFAULT_SCHEMAS:
        schema_name = BENCHMARK_DEFAULT_SCHEMAS[benchmark_name]
        return SCHEMA_REGISTRY[schema_name]

    # 3. Scoring-type fallback
    scoring_type = fixture.scoring.get("type", "similarity")
    if scoring_type in SCORING_TYPE_FALLBACKS:
        schema_name = SCORING_TYPE_FALLBACKS[scoring_type]
        return SCHEMA_REGISTRY[schema_name]

    # 4. Error
    raise SchemaResolutionError(
        f"No schema resolution for fixture {fixture.id} "
        f"(benchmark {benchmark_name}, scoring type {scoring_type}). "
        f"Add 'output_schema' to the fixture YAML, "
        f"or add a benchmark default or scoring-type fallback."
    )


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

    if canonicalize_strategy == CANONICALIZE_FILE_BLOCKS:
        expected_files = fixture.scoring.get("expected_files")
        if (
            isinstance(expected_files, dict)
            and expected_files
            and all(
                isinstance(filename, str)
                and filename.strip()
                and isinstance(content, str)
                for filename, content in expected_files.items()
            )
        ):
            return {primary_path: dict(expected_files)}
        return None

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
