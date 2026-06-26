"""Tests for structured-output contract templates, canonicalization, and validation."""

import pytest

from gitbench.fixture_structured_validator import (
    validate_all_fixtures,
    validate_fixture_contract,
)
from gitbench.harness.types import Fixture, StructuredOutputContract
from gitbench.structured_output import (
    SCHEMA_REGISTRY,
    StructuredOutputParseError,
    StructuredOutputSchemaError,
    canonicalize,
    contract_for_benchmark_fixture,
    fixture_expected_as_payload,
    roundtrip_check,
    strict_json_loads,
    validate_contract,
    validate_structured_payload,
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


class TestSchemaRegistry:
    def test_commit_message_schema(self):
        contract = SCHEMA_REGISTRY["commit_message"]
        schema = contract.schema
        assert schema["type"] == "object"
        assert "commit_message" in schema["properties"]
        assert schema["properties"]["commit_message"]["type"] == "string"
        assert schema["additionalProperties"] is False
        assert "commit_message" in schema["required"]

    def test_command_schema(self):
        schema = SCHEMA_REGISTRY["command"].schema
        assert schema["type"] == "object"
        assert "command" in schema["properties"]

    def test_count_schema(self):
        schema = SCHEMA_REGISTRY["count"].schema
        assert schema["type"] == "object"
        assert schema["properties"]["count"]["type"] == "integer"

    def test_hash_schema(self):
        schema = SCHEMA_REGISTRY["hash"].schema
        assert schema["type"] == "object"
        assert "hash" in schema["properties"]

    def test_stash_ref_schema(self):
        schema = SCHEMA_REGISTRY["stash_ref"].schema
        assert schema["type"] == "object"
        assert "stash" in schema["properties"]

    def test_resolved_content_schema(self):
        schema = SCHEMA_REGISTRY["resolved_content"].schema
        assert schema["type"] == "object"
        assert "resolved_content" in schema["properties"]

    def test_resolved_file_blocks_schema(self):
        contract = SCHEMA_REGISTRY["resolved_file_blocks"]
        schema = contract.schema
        assert schema["type"] == "object"
        assert "files" in schema["properties"]
        assert schema["properties"]["files"]["type"] == "object"
        assert schema["properties"]["files"]["additionalProperties"] == {
            "type": "string"
        }
        assert contract.primary_path == "files"

    def test_branch_list_schema(self):
        schema = SCHEMA_REGISTRY["branch_list"].schema
        assert schema["type"] == "object"
        assert schema["properties"]["branches_to_delete"]["type"] == "array"

    def test_commit_selection_schema(self):
        schema = SCHEMA_REGISTRY["commit_selection"].schema
        assert schema["type"] == "object"
        assert schema["properties"]["commits"]["type"] == "array"

    def test_command_list_schema(self):
        schema = SCHEMA_REGISTRY["command_list"].schema
        assert schema["type"] == "object"
        assert schema["properties"]["commands"]["type"] == "array"


class TestStrictStructuredJson:
    @pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
    def test_rejects_non_standard_constants(self, constant):
        with pytest.raises(StructuredOutputParseError, match="non-standard"):
            strict_json_loads(f'{{"commit": {constant}}}')

    def test_rejects_numeric_overflow(self):
        with pytest.raises(StructuredOutputParseError, match="non-finite"):
            strict_json_loads('{"values": [1e400]}')

    def test_accepts_finite_standard_json(self):
        assert strict_json_loads('{"commit": "fix parser", "count": 2}') == {
            "commit": "fix parser",
            "count": 2,
        }

    def test_validates_payload_against_contract(self):
        contract = SCHEMA_REGISTRY["commit_message"]

        validate_structured_payload({"commit_message": "fix parser"}, contract)

        with pytest.raises(StructuredOutputSchemaError, match="required property"):
            validate_structured_payload({}, contract)
        with pytest.raises(StructuredOutputSchemaError, match="type string"):
            validate_structured_payload({"commit_message": 42}, contract)
        with pytest.raises(StructuredOutputSchemaError, match="undeclared property"):
            validate_structured_payload(
                {"commit_message": "fix parser", "extra": True},
                contract,
            )


# ---------------------------------------------------------------------------
# Canonicalization tests
# ---------------------------------------------------------------------------


class TestCanonicalize:
    def test_string_rendering(self):
        contract = SCHEMA_REGISTRY["commit_message"]
        result = canonicalize({"commit_message": "Add hello.txt"}, contract)
        assert result == "Add hello.txt"

    def test_lines_rendering(self):
        contract = SCHEMA_REGISTRY["branch_list"]
        result = canonicalize(
            {"branches_to_delete": ["fix-typo", "fix-b"]}, contract
        )
        assert result == "fix-typo\nfix-b"

    def test_numeric_rendering(self):
        contract = SCHEMA_REGISTRY["count"]
        result = canonicalize({"count": 42}, contract)
        assert result == "42"

    def test_empty_value(self):
        contract = SCHEMA_REGISTRY["command"]
        result = canonicalize({}, contract)
        assert result == ""

    def test_file_blocks_rendering_preserves_filenames_and_contents(self):
        contract = SCHEMA_REGISTRY["resolved_file_blocks"]
        result = canonicalize(
            {
                "files": {
                    "utils.py": "DEBUG = True\nPORT = 9000\n",
                    "main.py": 'def main():\n    print("Running enterprise")\n',
                }
            },
            contract,
        )

        assert "main.py:\n" in result
        assert "utils.py:\n" in result
        assert 'print("Running enterprise")' in result
        assert "DEBUG = True" in result


# ---------------------------------------------------------------------------
# Contract validation tests
# ---------------------------------------------------------------------------


class TestValidateContract:
    def test_valid_contract(self):
        contract = SCHEMA_REGISTRY["commit_message"]
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
            schema=SCHEMA_REGISTRY["commit_message"].schema,
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
        assert payload == {"commit_message": "Add hello.txt with greeting message"}
        assert roundtrip_check(fixture, contract)

    def test_branch_list_roundtrip(self):
        fixture = _make_fixture("fix-typo\nfix-b", "exact_match")
        contract = contract_for_benchmark_fixture(fixture, "branch_cleanup")
        payload = fixture_expected_as_payload(fixture, contract)
        assert payload == {"branches_to_delete": ["fix-typo", "fix-b"]}
        assert roundtrip_check(fixture, contract)

    def test_numeric_roundtrip(self):
        fixture = _make_fixture("42", "numeric_exact")
        # Use a benchmark without a default so scoring-type fallback applies
        contract = contract_for_benchmark_fixture(fixture, "test_benchmark")
        payload = fixture_expected_as_payload(fixture, contract)
        assert payload == {"count": 42}
        assert roundtrip_check(fixture, contract)

    def test_hash_roundtrip(self):
        fixture = _make_fixture("abc1234", "commit_hash_by_subject")
        # Use a benchmark without a default so scoring-type fallback applies
        contract = contract_for_benchmark_fixture(fixture, "test_benchmark")
        payload = fixture_expected_as_payload(fixture, contract)
        assert payload == {"hash": "abc1234"}
        assert roundtrip_check(fixture, contract)

    def test_resolved_content_roundtrip(self):
        fixture = _make_fixture("Hello, Planet!!!", "similarity")
        contract = contract_for_benchmark_fixture(fixture, "merge_conflicts")
        payload = fixture_expected_as_payload(fixture, contract)
        assert payload == {"resolved_content": "Hello, Planet!!!"}
        assert roundtrip_check(fixture, contract)

    def test_resolved_content_schema_remains_single_file_default(self):
        fixture = _make_fixture("Hello, Planet!!!", "exact_match")
        contract = contract_for_benchmark_fixture(fixture, "merge_conflicts")

        assert contract is SCHEMA_REGISTRY["resolved_content"]

    def test_resolved_file_blocks_roundtrip_from_expected_files(self):
        fixture = Fixture(
            id="resolved-files",
            description="multi-file",
            setup=[],
            prompt="Resolve files",
            expected="main.py:\nprint('ok')\n\nutils.py:\nDEBUG = True\n",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {
                    "main.py": "print('ok')\n",
                    "utils.py": "DEBUG = True\n",
                },
            },
            output_schema="resolved_file_blocks",
        )
        contract = contract_for_benchmark_fixture(fixture, "merge_conflicts")
        payload = fixture_expected_as_payload(fixture, contract)

        assert payload == {
            "files": {
                "main.py": "print('ok')\n",
                "utils.py": "DEBUG = True\n",
            }
        }
        assert roundtrip_check(fixture, contract)

    def test_resolved_file_blocks_canonical_text_scores(self):
        from gitbench.harness.scorer import Scorer

        fixture = Fixture(
            id="resolved-files",
            description="multi-file",
            setup=[],
            prompt="Resolve files",
            expected="",
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {
                    "main.py": "print('ok')\n",
                    "utils.py": "DEBUG = True\n",
                },
            },
            output_schema="resolved_file_blocks",
        )
        contract = contract_for_benchmark_fixture(fixture, "merge_conflicts")
        payload = {
            "files": {
                "utils.py": "DEBUG = True\n",
                "main.py": "print('ok')\n",
            }
        }

        validate_structured_payload(payload, contract)
        result = Scorer().score(fixture, canonicalize(payload, contract))

        assert result.passed is True

    def test_command_list_roundtrip(self):
        fixture = _make_fixture("git checkout main\ngit pull", "command_equivalence")
        # Use a benchmark without a default so scoring-type fallback applies
        contract = contract_for_benchmark_fixture(fixture, "test_benchmark")
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
