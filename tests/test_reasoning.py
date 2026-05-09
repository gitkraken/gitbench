"""Tests for gitbench.harness.reasoning validation module."""

import click
import json

import pytest
from click.testing import CliRunner

from gitbench.cli import cli
from gitbench.harness.reasoning import (
    VALID_REASONING_LEVELS,
    get_supported_levels,
    parse_model_reasoning,
    validate_model_list,
)


class TestParseModelReasoning:
    def test_bare_name(self):
        base, level = parse_model_reasoning("gpt-4o")
        assert base == "gpt-4o"
        assert level is None

    def test_with_reasoning_level(self):
        base, level = parse_model_reasoning("o3-mini#high")
        assert base == "o3-mini"
        assert level == "high"

    def test_multiple_hash_uses_last(self):
        base, level = parse_model_reasoning("model#extra#low")
        assert base == "model#extra"
        assert level == "low"

    def test_mock_model_bypasses_parsing(self):
        base, level = parse_model_reasoning("mock#high")
        assert base == "mock"
        assert level == "high"

    def test_empty_level(self):
        base, level = parse_model_reasoning("model#")
        assert base == "model"
        assert level == ""

    def test_no_hash(self):
        base, level = parse_model_reasoning("llama3.1:8b")
        assert base == "llama3.1:8b"
        assert level is None

    def test_provider_prefix_with_level(self):
        base, level = parse_model_reasoning("openai/gpt-4o#high")
        assert base == "openai/gpt-4o"
        assert level == "high"

    def test_colon_in_model_name(self):
        base, level = parse_model_reasoning("anthropic/claude-3.5:latest#medium")
        assert base == "anthropic/claude-3.5:latest"
        assert level == "medium"


class TestValidReasoningLevels:
    def test_expected_levels(self):
        assert VALID_REASONING_LEVELS == ["minimal", "low", "medium", "high", "xhigh"]

    def test_level_count(self):
        assert len(VALID_REASONING_LEVELS) == 5


class TestGetSupportedLevels:
    def test_known_model(self):
        levels = get_supported_levels("gpt-4o")
        assert levels is not None
        assert "high" in levels
        assert "xhigh" in levels

    def test_known_model_with_provider_prefix(self):
        levels = get_supported_levels("openai/gpt-4o")
        assert levels is not None
        assert "high" in levels
        assert "xhigh" in levels

    def test_unknown_model(self):
        assert get_supported_levels("unknown-model") is None

    def test_o3_mini(self):
        levels = get_supported_levels("o3-mini")
        assert levels == ["minimal", "low", "medium", "high"]
        assert "xhigh" not in levels

    def test_gpt_4o_mini(self):
        levels = get_supported_levels("gpt-4o-mini")
        assert levels == ["minimal", "low", "medium", "high"]
        assert "xhigh" not in levels


class TestValidateModelList:
    def test_empty_list_ok(self):
        validate_model_list([])

    def test_mock_only_ok(self):
        validate_model_list(["mock"])

    def test_mock_with_levels_ok(self):
        validate_model_list(["mock#high", "mock#medium"])

    def test_valid_level_passes(self):
        validate_model_list(["gpt-4o#high"])
        validate_model_list(["o3-mini#medium"])
        validate_model_list(["gpt-4o#xhigh"])

    def test_model_without_level_passes(self):
        validate_model_list(["gpt-4o"])
        validate_model_list(["openai/gpt-4o"])

    def test_unknown_model_with_level_passes(self):
        validate_model_list(["some-new-model#high"])

    def test_unknown_model_without_level_passes(self):
        validate_model_list(["some-model-with-slash/version"])

    def test_multiple_valid_models(self):
        validate_model_list(["gpt-4o#high", "o3-mini#medium", "gpt-4o-mini#low"])

    def test_mixed_valid_and_mock(self):
        validate_model_list(["gpt-4o#high", "mock#high", "mock"])

    def test_invalid_level_raises(self):
        with pytest.raises(click.ClickException, match="Invalid reasoning level"):
            validate_model_list(["gpt-4o#invalid_level"])

    def test_valid_level_but_not_supported_by_model(self):
        with pytest.raises(click.ClickException, match="does not support"):
            validate_model_list(["o3-mini#xhigh"])

    def test_gpt_4o_mini_xhigh_not_supported(self):
        with pytest.raises(click.ClickException, match="does not support"):
            validate_model_list(["gpt-4o-mini#xhigh"])

    def test_valid_level_on_different_model(self):
        validate_model_list(["gpt-4o#xhigh"])
        validate_model_list(["gpt-4.1#xhigh"])
        validate_model_list(["gpt-5#xhigh"])

    def test_error_message_contains_model_and_level(self):
        with pytest.raises(click.ClickException) as exc:
            validate_model_list(["o3-mini#xhigh"])
        message = str(exc.value)
        assert "o3-mini" in message
        assert "xhigh" in message

    def test_error_message_lists_supported_levels(self):
        with pytest.raises(click.ClickException) as exc_info:
            validate_model_list(["gpt-4o-mini#xhigh"])
        message = str(exc_info.value)
        for level in VALID_REASONING_LEVELS:
            if level != "xhigh":
                assert level in message

    def test_invalid_level_error_message_shows_valid_list(self):
        with pytest.raises(click.ClickException) as exc_info:
            validate_model_list(["gpt-4o#extreme"])
        message = str(exc_info.value)
        assert "Invalid reasoning level" in message
        for level in VALID_REASONING_LEVELS:
            assert level in message

    def test_first_invalid_stops_validation(self):
        with pytest.raises(click.ClickException):
            validate_model_list(["gpt-4o#invalid", "o3-mini#xhigh"])

    def test_each_model_in_list_gets_unpacked_from_runs(self):
        models = [
            "openai/gpt-4o#high",
            "anthropic/claude-opus-4.7",
            "deepseek/deepseek-v4-pro#low",
            "google/gemini-3-flash-preview",
        ]
        validate_model_list(models)


class TestCliIntegration:
    def test_run_with_valid_reasoning_passes(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("gitbench.json", "w") as f:
                json.dump({"models": {"test": {"models": ["mock"], "provider": "openai"}}}, f)

            from unittest.mock import patch
            with patch("gitbench.cli.check_git_availability", return_value=True):
                result = runner.invoke(
                    cli,
                    ["run", "--benchmark", "commit_messages", "--model", "openai/gpt-4o-mini#high"],
                )
            assert result.exit_code == 0

    def test_run_with_invalid_reasoning_fails_fast(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("gitbench.json", "w") as f:
                json.dump({"models": {"test": {"models": ["mock"], "provider": "openai"}}}, f)

            from unittest.mock import patch
            with patch("gitbench.cli.check_git_availability", return_value=True):
                result = runner.invoke(
                    cli,
                    ["run", "--benchmark", "commit_messages", "--model", "gpt-4o-mini#xhigh"],
                )
            assert result.exit_code != 0
            assert "does not support" in result.output.lower() or "xhigh" in result.output.lower()

    def test_run_with_unsupported_level_fails_fast(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("gitbench.json", "w") as f:
                json.dump({"models": {"test": {"models": ["mock"], "provider": "openai"}}}, f)

            from unittest.mock import patch
            with patch("gitbench.cli.check_git_availability", return_value=True):
                result = runner.invoke(
                    cli,
                    ["run", "--benchmark", "commit_messages", "--model", "gpt-4o#ultra"],
                )
            assert result.exit_code != 0
            assert "Invalid reasoning level" in result.output or "ultra" in result.output.lower()

    def test_run_all_models_with_invalid_model_fails_fast(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            config = {
                "models": {
                    "bad": {
                        "models": ["gpt-4o-mini#xhigh"],
                        "provider": "openai",
                    }
                }
            }
            with open("gitbench.json", "w") as f:
                json.dump(config, f)

            from unittest.mock import patch
            with patch("gitbench.cli.check_git_availability", return_value=True):
                result = runner.invoke(
                    cli,
                    ["run", "--benchmark", "commit_messages", "--all-models"],
                )
            assert result.exit_code != 0
            assert "does not support" in result.output.lower() or "xhigh" in result.output.lower()
