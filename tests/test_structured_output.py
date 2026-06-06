"""Tests for structured-output contract templates, canonicalization, and validation."""

import json

import pytest

from gitbench.harness.types import Fixture, StructuredOutputContract
from gitbench.structured_output import (
    branch_list_template,
    canonicalize,
    commit_message_template,
    commit_selection_template,
    command_list_template,
    command_template,
    contract_for_benchmark_fixture,
    fixture_expected_as_payload,
    hash_template,
    numeric_template,
    resolved_content_template,
    roundtrip_check,
    stash_ref_template,
    validate_contract,
)
from gitbench.fixture_structured_validator import (
    validate_fixture_contract,
    validate_all_fixtures,
)


# ---------------------------------------------------------------------------
# Contract template smoke tests
# ---------------------------------------------------------------------------


def _make_fixture(expected, scoring_type):
    return Fixture(
        id="test-fixture",
        description="test",
        setup=[],
        prompt="test prompt",
        expected=expected,
        scoring={"type": scoring_type},
    )


class TestContractTemplates:
    def test_commit_message_template(self):
        schema = commit_message_template()
        assert schema["type"] == "object"
        assert "commit" in schema["properties"]
        assert schema["properties"]["commit"]["type"] == "string"
        assert schema["additionalProperties"] is False
        assert "commit" in schema["required"]

    def test_command_template(self):
        schema = command_template()
        assert schema["type"] == "object"
        assert "command" in schema["properties"]

    def test_numeric_template(self):
        schema = numeric_template()
        assert schema["type"] == "object"
        assert schema["properties"]["count"]["type"] == "integer"

    def test_hash_template(self):
        schema = hash_template()
        assert schema["type"] == "object"
        assert "hash" in schema["properties"]

    def test_stash_ref_template(self):
        schema = stash_ref_template()
        assert schema["type"] == "object"
        assert "stash" in schema["properties"]

    def test_resolved_content_template(self):
        schema = resolved_content_template()
        assert schema["type"] == "object"
        assert "resolved_content" in schema["properties"]

    def test_branch_list_template(self):
        schema = branch_list_template()
        assert schema["type"] == "object"
        assert schema["properties"]["branches_to_delete"]["type"] == "array"

    def test_commit_selection_template(self):
        schema = commit_selection_template()
        assert schema["type"] == "object"
        assert schema["properties"]["commits"]["type"] == "array"

    def test_command_list_template(self):
        schema = command_list_template()
        assert schema["type"] == "object"
        assert schema["properties"]["commands"]["type"] == "array"


# ---------------------------------------------------------------------------
# Canonicalization tests
# ---------------------------------------------------------------------------


class TestCanonicalize:
    def test_string_rendering(self):
        contract = StructuredOutputContract(
            schema=commit_message_template(),
            primary_path="commit",
            canonicalize="string",
        )
        result = canonicalize({"commit": "Add hello.txt"}, contract)
        assert result == "Add hello.txt"

    def test_lines_rendering(self):
        contract = StructuredOutputContract(
            schema=branch_list_template(),
            primary_path="branches_to_delete",
            canonicalize="lines",
        )
        result = canonicalize(
            {"branches_to_delete": ["fix-typo", "fix-b"]}, contract
        )
        assert result == "fix-typo\nfix-b"

    def test_numeric_rendering(self):
        contract = StructuredOutputContract(
            schema=numeric_template(),
            primary_path="count",
            canonicalize="numeric_string",
        )
        result = canonicalize({"count": 42}, contract)
        assert result == "42"

    def test_empty_value(self):
        contract = StructuredOutputContract(
            schema=command_template(),
            primary_path="command",
            canonicalize="string",
        )
        result = canonicalize({}, contract)
        assert result == ""


# ---------------------------------------------------------------------------
# Contract validation tests
# ---------------------------------------------------------------------------


class TestValidateContract:
    def test_valid_contract(self):
        contract = StructuredOutputContract(
            schema=commit_message_template(),
            primary_path="commit",
            canonicalize="string",
        )
        errors = validate_contract(contract)
        assert errors == []

    def test_missing_properties(self):
        contract = StructuredOutputContract(
            schema={"type": "object", "additionalProperties": False},
            primary_path="x",
            canonicalize="string",
        )
        errors = validate_contract(contract)
        assert any("properties" in e for e in errors)

    def test_additional_properties_allowed(self):
        contract = StructuredOutputContract(
            schema={
                "type": "object",
                "properties": {"x": {"type": "string"}},
            },
            primary_path="x",
            canonicalize="string",
        )
        errors = validate_contract(contract)
        assert any("additionalProperties" in e for e in errors)

    def test_required_not_in_properties(self):
        contract = StructuredOutputContract(
            schema={
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x", "y"],
                "additionalProperties": False,
            },
            primary_path="x",
            canonicalize="string",
        )
        errors = validate_contract(contract)
        assert any("'y'" in e for e in errors)

    def test_empty_primary_path(self):
        contract = StructuredOutputContract(
            schema=commit_message_template(),
            primary_path="",
            canonicalize="string",
        )
        errors = validate_contract(contract)
        assert any("primary_path" in e for e in errors)


# ---------------------------------------------------------------------------
# Expected answer roundtrip tests
# ---------------------------------------------------------------------------


class TestExpectedAsPayload:
    def test_commit_message_roundtrip(self):
        fixture = _make_fixture("Add hello.txt with greeting message", "similarity")
        contract = contract_for_benchmark_fixture(fixture, "commit_messages")
        payload = fixture_expected_as_payload(fixture, contract)
        assert payload == {"commit": "Add hello.txt with greeting message"}
        assert roundtrip_check(fixture, contract)

    def test_branch_list_roundtrip(self):
        fixture = _make_fixture("fix-typo\nfix-b", "exact_match")
        contract = contract_for_benchmark_fixture(fixture, "branch_cleanup")
        payload = fixture_expected_as_payload(fixture, contract)
        assert payload == {"branches_to_delete": ["fix-typo", "fix-b"]}
        assert roundtrip_check(fixture, contract)

    def test_numeric_roundtrip(self):
        fixture = _make_fixture("42", "numeric_exact")
        # Use a benchmark that isn't a state-assertion benchmark
        contract = contract_for_benchmark_fixture(fixture, "reflog")
        payload = fixture_expected_as_payload(fixture, contract)
        assert payload == {"count": 42}
        assert roundtrip_check(fixture, contract)

    def test_hash_roundtrip(self):
        fixture = _make_fixture("abc1234", "commit_hash_by_subject")
        contract = contract_for_benchmark_fixture(fixture, "reflog")
        payload = fixture_expected_as_payload(fixture, contract)
        assert payload == {"hash": "abc1234"}
        assert roundtrip_check(fixture, contract)

    def test_resolved_content_roundtrip(self):
        fixture = _make_fixture("Hello, Planet!!!", "similarity")
        contract = contract_for_benchmark_fixture(fixture, "merge_conflicts")
        payload = fixture_expected_as_payload(fixture, contract)
        assert payload == {"resolved_content": "Hello, Planet!!!"}
        assert roundtrip_check(fixture, contract)

    def test_command_list_roundtrip(self):
        fixture = _make_fixture("git checkout main\ngit pull", "command_equivalence")
        contract = contract_for_benchmark_fixture(fixture, "tag_management")
        payload = fixture_expected_as_payload(fixture, contract)
        assert payload == {"commands": ["git checkout main", "git pull"]}
        assert roundtrip_check(fixture, contract)

    def test_stash_ref_roundtrip(self):
        fixture = _make_fixture("stash@{0}", "stash_recovery")
        contract = contract_for_benchmark_fixture(fixture, "stash_recovery")
        payload = fixture_expected_as_payload(fixture, contract)
        assert payload == {"stash": "stash@{0}"}
        assert roundtrip_check(fixture, contract)


# ---------------------------------------------------------------------------
# Explicit contract field tests
# ---------------------------------------------------------------------------


class TestExplicitContractField:
    def test_fixture_with_explicit_contract_prefers_it(self):
        explicit_contract = StructuredOutputContract(
            schema={"type": "object", "properties": {"custom": {"type": "string"}}, "required": ["custom"], "additionalProperties": False},
            primary_path="custom",
            canonicalize="string",
            display_label="Custom Field",
        )
        fixture = Fixture(
            id="explicit-fixture",
            description="test",
            setup=[],
            prompt="test",
            expected="custom-value",
            scoring={"type": "exact_match"},
            structured_output=explicit_contract,
        )
        # Use a non-override, non-state-assertion benchmark name
        resolved = contract_for_benchmark_fixture(fixture, "reflog")
        assert resolved.primary_path == "custom"
        assert resolved.display_label == "Custom Field"
        assert "custom" in resolved.schema["properties"]


# ---------------------------------------------------------------------------
# Fixture contract validator integration tests
# ---------------------------------------------------------------------------


class TestValidateFixtureContract:
    def test_valid_commit_message_fixture(self):
        fixture = _make_fixture("Add hello.txt", "similarity")
        issues = validate_fixture_contract(fixture, "commit_messages")
        assert issues == []

    def test_valid_branch_cleanup_fixture(self):
        fixture = _make_fixture("fix-typo\nfix-b", "exact_match")
        issues = validate_fixture_contract(fixture, "branch_cleanup")
        assert issues == []

    def test_valid_merge_conflicts_fixture(self):
        fixture = _make_fixture("resolved content here", "similarity")
        issues = validate_fixture_contract(fixture, "merge_conflicts")
        assert issues == []

    def test_unknown_scoring_type(self):
        fixture = _make_fixture("test", "unknown_scoring_type")
        issues = validate_fixture_contract(fixture, "some_benchmark")
        assert any(i.code == "missing-contract" for i in issues)


class TestValidateAllFixtures:
    def test_all_contracts_valid(self):
        fixtures = {
            "commit_messages": [
                _make_fixture("Add file", "similarity"),
                _make_fixture("Fix bug", "similarity"),
            ],
            "branch_cleanup": [
                _make_fixture("branch-a\nbranch-b", "exact_match"),
            ],
        }
        report = validate_all_fixtures(fixtures)
        assert report.valid
        assert report.total_fixtures == 3
        assert report.fixtures_with_contract == 3
        assert report.fixtures_without_contract == 0

    def test_missing_contract_fixture_reported(self):
        fixtures = {
            "unknown_benchmark": [
                _make_fixture("test", "unknown_type"),
            ],
        }
        report = validate_all_fixtures(fixtures)
        assert not report.valid
        assert report.fixtures_without_contract == 1
