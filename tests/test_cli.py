"""Tests for GitBench CLI."""

import json
import logging
import sys
import time
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from gitbench.cli import (
    DEFAULT_DOCTOR_TIMEOUT,
    DEFAULT_JSON_OUTPUT_PATH,
    DEFAULT_RETRY_COUNT,
    _doctor_progress_label,
    _effective_doctor_timeout,
    _effective_retry_count,
    _effective_timeout,
    _progress_model_names,
    _progress_model_names_for_runs,
    check_git_availability,
    cli,
    get_model_client,
    resolve_run_output_path,
)
from gitbench.ui.display import RichProgressDisplay
from gitbench.version import BENCHMARK_SUITE_VERSION


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestCheckGitAvailability:
    """Tests for check_git_availability function."""

    def test_returns_true_when_git_available(self):
        """Test that function returns True when git is found."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            result = check_git_availability()
            assert result is True

    def test_returns_false_when_git_not_available(self):
        """Test that function returns False when git is not found."""
        with patch("shutil.which", return_value=None):
            result = check_git_availability()
            assert result is False


class TestGetModelClient:
    """Tests for get_model_client function."""

    def test_returns_mock_client(self):
        """Test that 'mock' returns a MockModelClient."""
        client = get_model_client("mock")
        from gitbench.harness.model import MockModelClient
        assert isinstance(client, MockModelClient)

    def test_returns_openai_adapter(self):
        """Test that 'openai' model name returns an OpenAIAdapter."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            client = get_model_client("openai")
            from gitbench.harness.model import OpenAIAdapter
            assert isinstance(client, OpenAIAdapter)

    def test_returns_openai_adapter_for_any_model_name(self):
        """Test that any non-'mock' model name returns an OpenAIAdapter."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            # Standard model name
            client = get_model_client("gpt-4o")
            from gitbench.harness.model import OpenAIAdapter
            assert isinstance(client, OpenAIAdapter)
            assert client.model == "gpt-4o"

            # OpenRouter-style model name
            client2 = get_model_client("anthropic/claude-sonnet-4")
            assert isinstance(client2, OpenAIAdapter)
            assert client2.model == "anthropic/claude-sonnet-4"

    def test_passes_base_url_to_adapter(self):
        """Test that base_url is forwarded to OpenAIAdapter."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            client = get_model_client("anthropic/claude-sonnet-4", base_url="https://openrouter.ai/api/v1")
            from gitbench.harness.model import OpenAIAdapter
            assert isinstance(client, OpenAIAdapter)
            assert client._base_url == "https://openrouter.ai/api/v1"

    def test_provider_ollama_returns_ollama_adapter(self):
        """Test that provider='ollama' returns an OllamaAdapter."""
        from gitbench.harness.model import OllamaAdapter
        client = get_model_client("gemma4:26b", provider="ollama")
        assert isinstance(client, OllamaAdapter)
        assert client.model == "gemma4:26b"
        assert client.base_url == "http://localhost:11434"

    def test_provider_ollama_with_base_url(self):
        """Test that provider='ollama' uses the given base_url."""
        from gitbench.harness.model import OllamaAdapter
        client = get_model_client("llama3.1:8b", base_url="http://192.168.1.50:11434", provider="ollama")
        assert isinstance(client, OllamaAdapter)
        assert client.base_url == "http://192.168.1.50:11434"

    def test_provider_ollama_strips_v1_suffix(self):
        """Test that /v1 suffix is stripped from Ollama base_url."""
        from gitbench.harness.model import OllamaAdapter
        client = get_model_client("gemma4:26b", base_url="http://localhost:11434/v1", provider="ollama")
        assert isinstance(client, OllamaAdapter)
        assert client.base_url == "http://localhost:11434"

    def test_provider_openai_returns_openai_adapter(self):
        """Test that provider='openai' returns an OpenAIAdapter."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            from gitbench.harness.model import OpenAIAdapter
            client = get_model_client("gpt-4o", provider="openai")
            assert isinstance(client, OpenAIAdapter)
            assert client.timeout == 30

    def test_provider_openai_overrides_localhost_base_url(self):
        """Test that explicit provider='openai' wins even with localhost base_url."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            from gitbench.harness.model import OpenAIAdapter
            client = get_model_client("my-model", base_url="http://localhost:8080/v1", provider="openai")
            assert isinstance(client, OpenAIAdapter)

    def test_infer_ollama_from_localhost_base_url(self):
        """Test that localhost base_url infers Ollama when provider is unset."""
        from gitbench.harness.model import OllamaAdapter
        client = get_model_client("any-model", base_url="http://localhost:11434")
        assert isinstance(client, OllamaAdapter)
        assert client.timeout == 120

    def test_custom_timeout_and_retry_are_forwarded(self):
        """Explicit timeout/retry values override provider defaults."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            client = get_model_client(
                "gpt-4o",
                provider="openai",
                timeout=45,
                retry_count=2,
            )

        assert client.timeout == 45
        assert client.retry_count == 2


class TestModelRetryPolicy:
    """Tests for CLI/profile timeout and retry resolution."""

    def test_provider_defaults_are_preserved_without_cli_or_profile_values(self):
        assert _effective_timeout({}, None) is None
        assert _effective_retry_count({}, None) == DEFAULT_RETRY_COUNT

    def test_profile_timeout_and_retry_are_used_when_cli_values_absent(self):
        profile = {"timeout": 45, "retry_count": 2}

        assert _effective_timeout(profile, None) == 45
        assert _effective_retry_count(profile, None) == 2

    def test_cli_timeout_and_retry_override_profile_values(self):
        profile = {"timeout": 45, "retry_count": 2}

        assert _effective_timeout(profile, 10) == 10
        assert _effective_retry_count(profile, 1) == 1

    def test_doctor_timeout_defaults_longer_but_respects_profile_and_cli(self):
        assert _effective_doctor_timeout({}, None) == DEFAULT_DOCTOR_TIMEOUT
        assert _effective_doctor_timeout({"timeout": 45}, None) == 45
        assert _effective_doctor_timeout({"timeout": 45}, 180) == 180


class TestListCommand:
    """Tests for the list command."""

    def test_list_shows_benchmarks(self, runner):
        """Test that list shows available benchmarks."""
        with patch("gitbench.cli.check_git_availability", return_value=True):
            result = runner.invoke(cli, ["list"])
            assert result.exit_code == 0
            assert "commit_messages" in result.output

    def test_list_warns_when_git_missing(self, runner):
        """Test that list warns when git is not available."""
        with patch("gitbench.cli.check_git_availability", return_value=False):
            result = runner.invoke(cli, ["list"])
            assert "Warning" in result.output or "not found" in result.output


class TestRunCommand:
    """Tests for the run command."""

    def test_run_requires_benchmark_option(self, runner):
        """Test that run command requires --benchmark option."""
        result = runner.invoke(cli, ["run"])
        assert result.exit_code != 0
        assert "--benchmark" in result.output or "Missing" in result.output

    def test_run_with_mock_model(self, runner):
        """Test running with mock model produces JSON output."""
        with patch("gitbench.cli.check_git_availability", return_value=True):
            result = runner.invoke(
                cli,
                ["run", "--benchmark", "commit_messages", "--model", "mock"],
            )
            assert result.exit_code == 0

            # Output should be valid JSON - try to find JSON in output
            # The CLI outputs JSON to stdout, possibly with additional echo statements
            output = result.output.strip()

            # Try to find JSON object in output (may be surrounded by other text)
            json_start = output.find("{")
            if json_start != -1:
                # Find the matching closing brace
                json_candidate = output[json_start:]
                brace_count = 0
                json_end = len(json_candidate)
                for i, char in enumerate(json_candidate):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                json_str = json_candidate[:json_end]
                data = json.loads(json_str)
                assert "benchmark" in data
                assert data["benchmark"] == "commit_messages"
            else:
                pytest.fail(f"No JSON found in output: {output}")

    def test_run_with_json_output_file(self, runner, tmp_path):
        """Test that run can write to an explicit JSON output file."""
        output_path = tmp_path / "results.json"

        with patch("gitbench.cli.check_git_availability", return_value=True):
            result = runner.invoke(
                cli,
                ["run", "--benchmark", "commit_messages", "--model", "mock", "--json-output", str(output_path)],
            )
            assert result.exit_code == 0

            # Check file was created and contains valid JSON
            content = output_path.read_text()
            data = json.loads(content)
            assert "benchmark" in data

    def test_run_writes_default_json_output(self, runner, tmp_path):
        """Test that run writes JSON artifact by default."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            cwd = Path.cwd()
            with patch("gitbench.cli.check_git_availability", return_value=True):
                result = runner.invoke(
                    cli,
                    ["run", "--benchmark", "commit_messages", "--model", "mock"],
            )

            assert result.exit_code == 0
            run_dirs = list((cwd / "gitbench-results").iterdir())
            assert len(run_dirs) == 1
            assert run_dirs[0].name.endswith("Z")
            json_path = run_dirs[0] / f"results-v{BENCHMARK_SUITE_VERSION}.json"
            assert json_path.exists()
            assert json.loads(json_path.read_text())["benchmark"] == "commit_messages"

    def test_run_json_output_cli_overrides_defaults(self, runner, tmp_path):
        """Test that explicit JSON output path overrides defaults."""
        json_path = tmp_path / "custom" / "results.json"

        with patch("gitbench.cli.check_git_availability", return_value=True):
            result = runner.invoke(
                cli,
                [
                    "run",
                    "--benchmark",
                    "commit_messages",
                    "--model",
                    "mock",
                    "--json-output",
                    str(json_path),
                ],
            )

        assert result.exit_code == 0
        assert json.loads(json_path.read_text())["benchmark"] == "commit_messages"

    def test_run_rejects_ambiguous_output_option(self, runner, tmp_path):
        """Test that run requires separate JSON/HTML output options."""
        output_path = tmp_path / "legacy.json"

        result = runner.invoke(
            cli,
            [
                "run",
                "--benchmark",
                "commit_messages",
                "--model",
                "mock",
                "--output",
                str(output_path),
            ],
        )

        assert result.exit_code != 0
        assert "No such option: --output" in result.output

    def test_run_uses_configured_json_output_path(self, runner, tmp_path):
        """Test that gitbench.json can override default JSON output path."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            cwd = Path.cwd()
            config = {
                "outputs": {
                    "json": "configured/results.json",
                }
            }
            with open("gitbench.json", "w") as f:
                json.dump(config, f)

            with patch("gitbench.cli.check_git_availability", return_value=True):
                result = runner.invoke(
                    cli,
                    ["run", "--benchmark", "commit_messages", "--model", "mock"],
                )

            assert result.exit_code == 0
            assert json.loads((cwd / "configured/results.json").read_text())["benchmark"] == "commit_messages"

    def test_run_with_nested_json_output_file(self, runner, tmp_path):
        """Test that --json-output creates parent directories for JSON output."""
        output_path = tmp_path / "nested" / "reports" / "results.json"

        with patch("gitbench.cli.check_git_availability", return_value=True):
            result = runner.invoke(
                cli,
                ["run", "--benchmark", "commit_messages", "--model", "mock", "--json-output", str(output_path)],
            )

        assert result.exit_code == 0
        data = json.loads(output_path.read_text())
        assert data["benchmark"] == "commit_messages"

    def test_run_with_nested_export_path(self, runner, tmp_path):
        """Test that --export-path creates parent directories."""
        export_path = tmp_path / "nested" / "exports" / "results.csv"

        with patch("gitbench.cli.check_git_availability", return_value=True):
            result = runner.invoke(
                cli,
                [
                    "run",
                    "--benchmark",
                    "commit_messages",
                    "--model",
                    "mock",
                    "--export",
                    "csv",
                    "--export-path",
                    str(export_path),
                ],
            )

        assert result.exit_code == 0
        assert export_path.exists()
        assert export_path.read_text().startswith("benchmark,fixture_id,model")

    def test_run_export_does_not_change_output_json_shape(self, runner, tmp_path):
        """Test that --export does not mutate the main JSON output payload."""
        export_path = tmp_path / "exports" / "results.csv"
        output_path = tmp_path / "results.json"

        with patch("gitbench.cli.check_git_availability", return_value=True):
            result = runner.invoke(
                cli,
                [
                    "run",
                    "--benchmark",
                    "commit_messages",
                    "--model",
                    "mock",
                    "--export",
                    "csv",
                    "--export-path",
                    str(export_path),
                    "--json-output",
                    str(output_path),
                ],
            )

        assert result.exit_code == 0
        assert export_path.exists()
        data = json.loads(output_path.read_text())
        assert data["benchmark"] == "commit_messages"

    def test_run_with_verbose_flag(self, runner):
        """Test that verbose flag shows per-fixture results."""
        with patch("gitbench.cli.check_git_availability", return_value=True):
            result = runner.invoke(
                cli,
                ["run", "--benchmark", "commit_messages", "--model", "mock", "--verbose"],
            )
            assert result.exit_code == 0
            # Verbose output should mention per-fixture or similar
            assert "Per-fixture" in result.output or "fixture" in result.output.lower()

    def test_run_routes_benchmark_logs_to_file(self, runner, tmp_path):
        """Runtime logs should not write through the terminal progress stream."""

        def fake_run_all(self, benchmark_names, *, model_name="", fixture_workers=1, progress=None, progress_model_name=None):
            logging.getLogger("gitbench.tests.noisy").warning("noisy benchmark warning")
            results = [
                {
                    "benchmark": bench_name,
                    "total": 1,
                    "passed": 1,
                    "pass_at_k": 1.0,
                    "scores": [],
                    "errors": 0,
                }
                for bench_name in benchmark_names
            ]
            return {
                "model": model_name,
                "summary": {
                    "total_benchmarks": len(results),
                    "total_fixtures": len(results),
                    "total_passed": len(results),
                    "overall_pass_at_k": 1.0,
                },
                "results": results,
            }

        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("gitbench.cli.check_git_availability", return_value=True), \
                 patch("gitbench.cli._benchmark_registry", {"commit_messages": object()}), \
                 patch("gitbench.harness.runner.BenchmarkRunner.run_all", side_effect=fake_run_all, autospec=True):
                result = runner.invoke(
                    cli,
                    ["run", "--benchmark", "commit_messages", "--model", "mock"],
                )

            assert result.exit_code == 0
            assert "noisy benchmark warning" not in result.output

            logs = list(Path("gitbench-logs").glob("run-*.log"))
            assert len(logs) == 1
            assert "noisy benchmark warning" in logs[0].read_text()

    def test_run_closes_progress_display_on_keyboard_interrupt(self, runner):
        """Terminal display cleanup runs for Ctrl+C-style exits."""
        progress_display = Mock()

        with patch("gitbench.cli.check_git_availability", return_value=True), \
             patch("gitbench.cli._benchmark_registry", {"commit_messages": object()}), \
             patch("gitbench.cli.RichProgressDisplay", return_value=progress_display), \
             patch("gitbench.harness.runner.BenchmarkRunner.run_all", side_effect=KeyboardInterrupt):
            result = runner.invoke(
                cli,
                ["run", "--benchmark", "commit_messages", "--model", "mock"],
            )

        assert result.exit_code != 0
        progress_display.close.assert_called_once()

    def test_run_exits_with_error_when_git_missing(self, runner):
        """Test that run exits with error when git is not available."""
        with patch("gitbench.cli.check_git_availability", return_value=False):
            result = runner.invoke(
                cli,
                ["run", "--benchmark", "commit_messages", "--model", "mock"],
            )
            assert result.exit_code == 1
            assert "Git" in result.output or "git" in result.output

    def test_run_with_output_dir(self, runner, tmp_path):
        """Test that --output-dir writes a per-run JSON file."""
        output_dir = tmp_path / "results"

        with patch("gitbench.cli.check_git_availability", return_value=True):
            result = runner.invoke(
                cli,
                ["run", "--benchmark", "commit_messages", "--model", "mock", "--output-dir", str(output_dir)],
            )
            assert result.exit_code == 0

            # Directory should be created with one JSON file
            assert output_dir.exists()
            files = list(output_dir.glob("*.json"))
            assert len(files) == 1

            # File should contain envelope with metadata
            data = json.loads(files[0].read_text())
            assert data["version"] == 1
            assert data["schema_version"] == 1
            assert data["benchmark_suite_version"] == BENCHMARK_SUITE_VERSION
            assert "timestamp" in data
            assert data["model"] == "mock"
            assert "summary" in data
            assert "results" in data
            assert len(data["results"]) == 1
            assert data["results"][0]["benchmark"] == "commit_messages"

    def test_run_with_jsonl(self, runner, tmp_path):
        """Test that --jsonl appends a JSON line to a file."""
        jsonl_path = tmp_path / "results.jsonl"

        with patch("gitbench.cli.check_git_availability", return_value=True):
            # First run
            result = runner.invoke(
                cli,
                ["run", "--benchmark", "commit_messages", "--model", "mock", "--jsonl", str(jsonl_path)],
            )
            assert result.exit_code == 0

            # Second run (should append, not overwrite)
            result = runner.invoke(
                cli,
                ["run", "--benchmark", "commit_messages", "--model", "mock", "--jsonl", str(jsonl_path)],
            )
            assert result.exit_code == 0

            # File should have two lines
            lines = jsonl_path.read_text().strip().split("\n")
            assert len(lines) == 2

            # Each line should be valid JSON with envelope
            for line in lines:
                data = json.loads(line)
                assert data["version"] == 1
                assert data["benchmark_suite_version"] == BENCHMARK_SUITE_VERSION
                assert "timestamp" in data
                assert data["model"] == "mock"
                assert "results" in data

    def test_run_with_output_dir_and_jsonl(self, runner, tmp_path):
        """Test that --output-dir and --jsonl can be used together."""
        output_dir = tmp_path / "results"
        jsonl_path = tmp_path / "results.jsonl"

        with patch("gitbench.cli.check_git_availability", return_value=True):
            result = runner.invoke(
                cli,
                [
                    "run", "--benchmark", "commit_messages", "--model", "mock",
                    "--output-dir", str(output_dir),
                    "--jsonl", str(jsonl_path),
                ],
            )
            assert result.exit_code == 0

            # Both outputs should be created
            assert len(list(output_dir.glob("*.json"))) == 1
            assert jsonl_path.exists()
            assert len(jsonl_path.read_text().strip().split("\n")) == 1

    def test_run_profile_models_with_model_workers(self, runner, tmp_path):
        """Test that multiple profile models can run with model workers."""
        output_dir = tmp_path / "parallel-results"
        jsonl_path = tmp_path / "parallel-results.jsonl"

        with runner.isolated_filesystem(temp_dir=tmp_path):
            config = {
                "models": {
                    "parallel": {
                        "models": ["mock", "mock"],
                    }
                }
            }
            with open("gitbench.json", "w") as f:
                json.dump(config, f)

            with patch("gitbench.cli.check_git_availability", return_value=True):
                result = runner.invoke(
                    cli,
                    [
                        "run",
                        "--benchmark",
                        "commit_messages",
                        "--profile",
                        "parallel",
                        "--model-workers",
                        "2",
                        "--output-dir",
                        str(output_dir),
                        "--jsonl",
                        str(jsonl_path),
                    ],
                )

        assert result.exit_code == 0
        json_start = result.output.find("[")
        assert json_start != -1
        data = json.loads(result.output[json_start:])
        assert len(data) == 2
        assert all(item["model"] == "mock" for item in data)
        assert len(list(output_dir.glob("*.json"))) == 2
        assert len(jsonl_path.read_text().strip().split("\n")) == 2

    def test_run_uses_profile_timeout_and_retry_when_cli_values_absent(self, runner, tmp_path):
        """Profile timeout/retry settings are passed to model clients."""
        from gitbench.harness.model import MockModelClient

        calls = []

        def fake_get_model_client(model, *, timeout=None, retry_count=3, base_url=None, api_key=None, provider=None):
            calls.append(
                {
                    "model": model,
                    "timeout": timeout,
                    "retry_count": retry_count,
                    "base_url": base_url,
                    "provider": provider,
                }
            )
            return MockModelClient()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            config = {
                "models": {
                    "remote": {
                        "models": ["remote-model"],
                        "provider": "openai",
                        "base_url": "https://example.invalid/v1",
                        "timeout": 45,
                        "retry_count": 2,
                    }
                }
            }
            with open("gitbench.json", "w") as f:
                json.dump(config, f)

            with patch("gitbench.cli.check_git_availability", return_value=True), \
                 patch("gitbench.cli.get_model_client", side_effect=fake_get_model_client):
                result = runner.invoke(
                    cli,
                    [
                        "run",
                        "--benchmark",
                        "commit_messages",
                        "--profile",
                        "remote",
                    ],
                )

        assert result.exit_code == 0
        assert calls[0]["timeout"] == 45
        assert calls[0]["retry_count"] == 2

    def test_run_cli_timeout_and_retry_override_profile_values(self, runner, tmp_path):
        """Explicit CLI timeout/retry settings win over profile settings."""
        from gitbench.harness.model import MockModelClient

        calls = []

        def fake_get_model_client(model, *, timeout=None, retry_count=3, base_url=None, api_key=None, provider=None):
            calls.append({"timeout": timeout, "retry_count": retry_count})
            return MockModelClient()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            config = {
                "models": {
                    "remote": {
                        "models": ["remote-model"],
                        "provider": "openai",
                        "timeout": 45,
                        "retry_count": 2,
                    }
                }
            }
            with open("gitbench.json", "w") as f:
                json.dump(config, f)

            with patch("gitbench.cli.check_git_availability", return_value=True), \
                 patch("gitbench.cli.get_model_client", side_effect=fake_get_model_client):
                result = runner.invoke(
                    cli,
                    [
                        "run",
                        "--benchmark",
                        "commit_messages",
                        "--profile",
                        "remote",
                        "--timeout",
                        "10",
                        "--retry-count",
                        "1",
                    ],
                )

        assert result.exit_code == 0
        assert calls[0]["timeout"] == 10
        assert calls[0]["retry_count"] == 1

    def test_run_all_models_with_workers_runs_across_profiles_concurrently(self, runner, tmp_path):
        """Test that -a parallelizes all-model runs across provider profiles."""
        starts = []
        ends = []
        providers = {}

        def fake_run_all(self, benchmark_names, *, model_name="", fixture_workers=1, progress=None, progress_model_name=None):
            starts.append((model_name, time.monotonic()))
            providers[model_name] = "mock"  # provider is resolved earlier, mock skips real clients
            time.sleep(0.2)
            ends.append((model_name, time.monotonic()))
            results = [
                {
                    "benchmark": bench_name,
                    "total": 1,
                    "passed": 1,
                    "pass_at_k": 1.0,
                    "scores": [],
                    "errors": 0,
                }
                for bench_name in benchmark_names
            ]
            return {
                "model": model_name,
                "summary": {
                    "total_benchmarks": len(results),
                    "total_fixtures": len(results),
                    "total_passed": len(results),
                    "overall_pass_at_k": 1.0,
                },
                "results": results,
            }

        with runner.isolated_filesystem(temp_dir=tmp_path):
            config = {
                "models": {
                    "remote": {
                        "models": ["remote-model"],
                        "provider": "openai",
                        "base_url": "https://example.invalid/v1",
                    },
                    "local": {
                        "models": ["local-model"],
                        "provider": "ollama",
                        "base_url": "http://localhost:11434",
                    },
                }
            }
            with open("gitbench.json", "w") as f:
                json.dump(config, f)

            with patch("gitbench.cli.check_git_availability", return_value=True), \
                 patch("gitbench.cli._benchmark_registry", {"commit_messages": object()}), \
                 patch("gitbench.harness.runner.BenchmarkRunner.run_all", side_effect=fake_run_all, autospec=True):
                result = runner.invoke(
                    cli,
                    [
                        "run",
                        "-a",
                        "--model-workers",
                        "2",
                    ],
                )

        assert result.exit_code == 0
        # providers are resolved via get_model_client; mock just records model names
        assert len(starts) == 2
        assert len(ends) == 2
        assert starts[1][1] < ends[0][1]

        json_start = result.output.find("{")
        assert json_start != -1
        data = json.loads(result.output[json_start:])
        assert data["summary"]["total_models"] == 2


def _doctor_payload() -> dict:
    return {
        "benchmark_suite_version": "0.1.0",
        "summary": {
            "total_profiles": 1,
            "total_models": 1,
            "total_fixtures": 3,
            "total_passed": 1,
            "overall_pass_at_k": 0.3333,
        },
        "profiles": [
            {
                "profile": "local",
                "summary": {
                    "total_models": 1,
                    "total_fixtures": 3,
                    "total_passed": 1,
                    "overall_pass_at_k": 0.3333,
                },
                "models": [
                    {
                        "model": "mock",
                        "summary": {
                            "total_benchmarks": 1,
                            "total_fixtures": 3,
                            "total_passed": 1,
                            "overall_pass_at_k": 0.3333,
                        },
                        "results": [
                            {
                                "benchmark": "commit_messages",
                                "total": 3,
                                "passed": 1,
                                "pass_at_k": 0.3333,
                                "errors": 2,
                                "scores": [
                                    {
                                        "fixture_id": "f001",
                                        "passed": True,
                                        "similarity": 1.0,
                                        "model_output": "ok",
                                        "error": None,
                                    },
                                    {
                                        "fixture_id": "f002",
                                        "passed": False,
                                        "similarity": 0.0,
                                        "model_output": "",
                                        "error": "APITimeoutError",
                                    },
                                    {
                                        "fixture_id": "f003",
                                        "passed": False,
                                        "similarity": 0.0,
                                        "model_output": "bad",
                                        "error": "expected got mismatch",
                                    },
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }


class TestDoctorCommand:
    """Tests for the doctor command."""

    def test_dry_run_reports_plan_without_model_calls_or_writes(self, runner, tmp_path):
        result_path = tmp_path / "results-v0.1.0.json"
        result_path.write_text(json.dumps(_doctor_payload()))

        with patch("gitbench.cli.get_model_client") as get_model_client:
            result = runner.invoke(
                cli,
                ["doctor", str(result_path), "--dry-run"],
            )

        assert result.exit_code == 0
        assert "Doctorable failed fixtures: 1" in result.output
        assert "Affected models: 1" in result.output
        assert "APITimeoutError: 1" in result.output
        get_model_client.assert_not_called()

    def test_latest_scans_all_timestamped_result_files(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            first = Path("gitbench-results/20260101T000000Z/results-v0.1.0.json")
            second = Path("gitbench-results/20260102T000000Z/results-v0.1.0.json")
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text(json.dumps(_doctor_payload()))
            second.write_text(json.dumps(_doctor_payload()))

            result = runner.invoke(cli, ["doctor", "--latest", "--dry-run"])

        assert result.exit_code == 0
        assert "Inputs: 2" in result.output
        assert "20260101T000000Z" in result.output
        assert "20260102T000000Z" in result.output
        assert "Total doctorable failed fixtures: 2" in result.output

    def test_doctor_updates_input_file_by_default(self, runner, tmp_path):
        from gitbench.harness.types import BenchmarkResult, Score

        rerun_result = BenchmarkResult(
            benchmark="commit_messages",
            total=1,
            passed=1,
            pass_at_k=1.0,
            errors=0,
            scores=[
                Score(
                    fixture_id="f002",
                    passed=True,
                    similarity=1.0,
                    model_output="fixed",
                    error=None,
                )
            ],
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result_path = Path("results-v0.1.0.json")
            result_path.write_text(json.dumps(_doctor_payload()))

            config = {"models": {"local": {"models": ["mock"]}}}
            Path("gitbench.json").write_text(json.dumps(config))

            with patch("gitbench.cli._benchmark_registry", {"commit_messages": object()}), \
                 patch("gitbench.harness.runner.BenchmarkRunner.run_benchmark", return_value=rerun_result) as run_benchmark:
                result = runner.invoke(
                    cli,
                    [
                        "doctor",
                        str(result_path),
                    ],
                )

        assert result.exit_code == 0
        run_benchmark.assert_called_once()
        assert run_benchmark.call_args.kwargs["selected_fixture_ids"] == ["f002"]
        input_path = next(tmp_path.glob("*/results-v0.1.0.json"))

        fixed = json.loads(input_path.read_text())
        scores = fixed["profiles"][0]["models"][0]["results"][0]["scores"]
        assert scores[1]["model_output"] == "fixed"
        assert scores[2]["error"] == "expected got mismatch"
        assert fixed["summary"]["total_passed"] == 2

    def test_doctor_uses_longer_default_timeout_and_cli_override(self, runner, tmp_path):
        from gitbench.harness.types import BenchmarkResult, Score

        rerun_result = BenchmarkResult(
            benchmark="commit_messages",
            total=1,
            passed=1,
            pass_at_k=1.0,
            errors=0,
            scores=[
                Score(
                    fixture_id="f002",
                    passed=True,
                    similarity=1.0,
                    model_output="fixed",
                    error=None,
                )
            ],
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result_path = Path("results-v0.1.0.json")
            result_path.write_text(json.dumps(_doctor_payload()))
            Path("gitbench.json").write_text(json.dumps({"models": {"local": {"models": ["mock"]}}}))

            with patch("gitbench.cli._benchmark_registry", {"commit_messages": object()}), \
                 patch("gitbench.cli.get_model_client", return_value=Mock()) as get_model_client, \
                 patch("gitbench.harness.runner.BenchmarkRunner.run_benchmark", return_value=rerun_result):
                default_result = runner.invoke(cli, ["doctor", str(result_path)])
                default_timeout = get_model_client.call_args.kwargs["timeout"]

            result_path.write_text(json.dumps(_doctor_payload()))

            with patch("gitbench.cli._benchmark_registry", {"commit_messages": object()}), \
                 patch("gitbench.cli.get_model_client", return_value=Mock()) as get_model_client, \
                 patch("gitbench.harness.runner.BenchmarkRunner.run_benchmark", return_value=rerun_result):
                override_result = runner.invoke(
                    cli,
                    ["doctor", str(result_path), "--timeout", "180"],
                )
                override_timeout = get_model_client.call_args.kwargs["timeout"]

        assert default_result.exit_code == 0
        assert default_timeout == DEFAULT_DOCTOR_TIMEOUT
        assert override_result.exit_code == 0
        assert override_timeout == 180

    def test_doctor_shows_progress_for_repaired_fixtures(self, runner, tmp_path):
        from gitbench.harness.types import BenchmarkResult, Score

        rerun_result = BenchmarkResult(
            benchmark="commit_messages",
            total=1,
            passed=1,
            pass_at_k=1.0,
            errors=0,
            scores=[
                Score(
                    fixture_id="f002",
                    passed=True,
                    similarity=1.0,
                    model_output="fixed",
                    error=None,
                )
            ],
        )
        progress_context = MagicMock()
        progress = MagicMock()
        progress.add_task.return_value = 123
        progress_context.__enter__.return_value = progress

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result_path = Path("results-v0.1.0.json")
            result_path.write_text(json.dumps(_doctor_payload()))
            Path("gitbench.json").write_text(json.dumps({"models": {"local": {"models": ["mock"]}}}))

            with patch("gitbench.cli._benchmark_registry", {"commit_messages": object()}), \
                 patch("gitbench.cli.Progress", return_value=progress_context) as progress_factory, \
                 patch("gitbench.harness.runner.BenchmarkRunner.run_benchmark", return_value=rerun_result):
                result = runner.invoke(cli, ["doctor", str(result_path)])

        assert result.exit_code == 0
        progress_factory.assert_called_once()
        progress.add_task.assert_called_once_with("Doctoring results", total=1)
        assert progress.update.call_count == 2
        assert "openai/mock/commit_messages" in progress.update.call_args_list[0].kwargs["description"]
        assert progress.update.call_args_list[1].kwargs["advance"] == 1
        assert "openai/mock/commit_messages" in progress.update.call_args_list[1].kwargs["description"]

    def test_doctor_progress_label_includes_provider_model_and_effort(self):
        assert _doctor_progress_label(
            {"provider": "openai"},
            "gpt-5#high",
        ) == "openai/gpt-5:high"
        assert _doctor_progress_label(
            {"provider": "openrouter"},
            "anthropic/claude-sonnet-4#low",
        ) == "openrouter/anthropic/claude-sonnet-4:low"
        assert _doctor_progress_label(
            {"base_url": "http://localhost:11434"},
            "gemma4:26b",
        ) == "ollama/gemma4:26b"

    def test_latest_updates_all_timestamped_files_then_second_run_does_nothing(self, runner, tmp_path):
        from gitbench.harness.types import BenchmarkResult, Score

        rerun_result = BenchmarkResult(
            benchmark="commit_messages",
            total=1,
            passed=1,
            pass_at_k=1.0,
            errors=0,
            scores=[
                Score(
                    fixture_id="f002",
                    passed=True,
                    similarity=1.0,
                    model_output="fixed",
                    error=None,
                )
            ],
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            first = Path("gitbench-results/20260101T000000Z/results-v0.1.0.json")
            second = Path("gitbench-results/20260102T000000Z/results-v0.1.0.json")
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text(json.dumps(_doctor_payload()))
            second.write_text(json.dumps(_doctor_payload()))
            Path("gitbench.json").write_text(json.dumps({"models": {"local": {"models": ["mock"]}}}))

            with patch("gitbench.cli._benchmark_registry", {"commit_messages": object()}), \
                 patch("gitbench.harness.runner.BenchmarkRunner.run_benchmark", return_value=rerun_result) as run_benchmark:
                first_result = runner.invoke(cli, ["doctor", "--latest"])

            with patch("gitbench.cli.get_model_client") as get_model_client:
                second_result = runner.invoke(cli, ["doctor", "--latest"])

            fixed_first = json.loads(first.read_text())
            fixed_second = json.loads(second.read_text())

        assert first_result.exit_code == 0
        assert run_benchmark.call_count == 2
        assert fixed_first["summary"]["total_passed"] == 2
        assert fixed_second["summary"]["total_passed"] == 2
        assert second_result.exit_code == 0
        assert "No doctorable failures found" in second_result.output
        get_model_client.assert_not_called()

    def test_doctor_persists_successful_targets_before_later_failure(self, runner, tmp_path):
        from gitbench.harness.types import BenchmarkResult, Score

        payload = _doctor_payload()
        payload["profiles"][0]["models"][0]["results"].append(
            {
                "benchmark": "git_show",
                "total": 1,
                "passed": 0,
                "pass_at_k": 0.0,
                "errors": 1,
                "scores": [
                    {
                        "fixture_id": "f002",
                        "passed": False,
                        "similarity": 0.0,
                        "model_output": "",
                        "error": "APITimeoutError",
                    }
                ],
            }
        )

        first_rerun = BenchmarkResult(
            benchmark="commit_messages",
            total=1,
            passed=1,
            pass_at_k=1.0,
            errors=0,
            scores=[
                Score(
                    fixture_id="f002",
                    passed=True,
                    similarity=1.0,
                    model_output="fixed",
                    error=None,
                )
            ],
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result_path = Path("results-v0.1.0.json")
            result_path.write_text(json.dumps(payload))
            Path("gitbench.json").write_text(json.dumps({"models": {"local": {"models": ["mock"]}}}))

            with patch("gitbench.cli._benchmark_registry", {"commit_messages": object(), "git_show": object()}), \
                 patch("gitbench.harness.runner.BenchmarkRunner.run_benchmark", side_effect=[first_rerun, RuntimeError("boom")]):
                result = runner.invoke(cli, ["doctor", str(result_path)])

            saved = json.loads(result_path.read_text())

        assert result.exit_code == 1
        assert saved["profiles"][0]["models"][0]["results"][0]["scores"][1]["model_output"] == "fixed"
        assert saved["profiles"][0]["models"][0]["results"][1]["scores"][0]["error"] == "APITimeoutError"

    def test_output_writes_explicit_copy_when_requested(self, runner, tmp_path):
        from gitbench.harness.types import BenchmarkResult, Score

        rerun_result = BenchmarkResult(
            benchmark="commit_messages",
            total=1,
            passed=1,
            pass_at_k=1.0,
            errors=0,
            scores=[
                Score(
                    fixture_id="f002",
                    passed=True,
                    similarity=1.0,
                    model_output="fixed",
                    error=None,
                )
            ],
        )

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result_path = Path("results-v0.1.0.json")
            output_path = Path("fixed.json")
            original_payload = _doctor_payload()
            result_path.write_text(json.dumps(original_payload))
            Path("gitbench.json").write_text(json.dumps({"models": {"local": {"models": ["mock"]}}}))

            with patch("gitbench.cli._benchmark_registry", {"commit_messages": object()}), \
                 patch("gitbench.harness.runner.BenchmarkRunner.run_benchmark", return_value=rerun_result):
                result = runner.invoke(
                    cli,
                    [
                        "doctor",
                        str(result_path),
                        "--output",
                        str(output_path),
                    ],
                )

        assert result.exit_code == 0
        fixed_path = next(tmp_path.glob("*/fixed.json"))
        input_path = fixed_path.parent / "results-v0.1.0.json"
        assert json.loads(input_path.read_text()) == original_payload
        assert json.loads(fixed_path.read_text())["summary"]["total_passed"] == 2


class TtyStringIO(StringIO):
    """StringIO that behaves like an interactive terminal."""

    def isatty(self):
        return True


class TestRichProgressDisplay:
    """Tests for RichProgressDisplay."""

    def test_progress_model_names_disambiguates_duplicates(self):
        assert _progress_model_names(["mock", "gpt-4o", "mock"]) == [
            "mock #1",
            "gpt-4o",
            "mock #2",
        ]

    def test_progress_model_names_for_runs_uses_model_names_only(self):
        runs = [
            ("local", {}, ["mock"]),
            ("remote", {}, ["mock", "gpt-4o", "claude"]),
        ]

        assert _progress_model_names_for_runs(runs) == [
            ["mock #1"],
            ["mock #2", "gpt-4o", "claude"],
        ]

    def test_non_tty_skips_live_display(self):
        """When stderr is not a TTY, Live is not started."""
        stream = StringIO()
        d = RichProgressDisplay(["mock"], ["commit_messages"])
        assert d.enabled is False  # stderr is not a TTY in pytest
        assert d._live is None
        d.close()

    def test_state_tracks_model_progress(self):
        """Callbacks update internal state correctly."""
        d = RichProgressDisplay(["mock"], ["commit_messages", "rebase"])
        d.model_started("mock")
        assert d._rows["mock"]["status"] == "queued"

        d.benchmark_started("mock", "commit_messages", 10)
        assert d._rows["mock"]["status"] == "running"
        assert d._rows["mock"]["fixtures_total"] == 10

        d.fixture_finished("mock", "commit_messages", True, fixture_id="f1", similarity=0.85)
        assert d._rows["mock"]["fixtures_done"] == 1
        assert d._rows["mock"]["passed"] == 1

        d.benchmark_finished("mock", "commit_messages", 0)
        assert d._rows["mock"]["benchmarks_done"] == 1

        d.model_finished("mock", {"total_fixtures": 10, "total_passed": 8})
        assert d._rows["mock"]["status"] == "done"
        d.close()

    def test_bench_results_tracks_per_benchmark(self):
        """Per-benchmark results are tracked in _bench_results."""
        d = RichProgressDisplay(["mock"], ["commit_messages"])
        d.benchmark_started("mock", "commit_messages", 5)
        d.fixture_finished("mock", "commit_messages", True)
        d.fixture_finished("mock", "commit_messages", False)
        d.benchmark_finished("mock", "commit_messages", 0)

        br = d._bench_results["mock"]["commit_messages"]
        assert br["total"] == 2
        assert br["passed"] == 1
        assert br["done"] is True
        d.close()

    def test_summary_table_renders_rows(self):
        """Summary table shows benchmark rows with pass rates."""
        d = RichProgressDisplay(["mock", "gpt-4o"], ["commit_messages", "rebase"])

        # Run commit_messages for both models
        for model in ["mock", "gpt-4o"]:
            d.model_started(model)
            d.benchmark_started(model, "commit_messages", 5)
            for _ in range(5):
                d.fixture_finished(model, "commit_messages", True)
            d.benchmark_finished(model, "commit_messages", 0)
            d.model_finished(model, {"total_fixtures": 5, "total_passed": 5})

        table = d._render_summary_table()
        # Table should have rows for both benchmarks
        assert table.row_count >= 2
        d.close()

    def test_build_layout_uses_supported_rich_layout_api(self):
        """Layout construction works with Rich versions without item assignment."""
        d = RichProgressDisplay(["mock", "gpt-4o"], ["commit_messages"])
        layout = d._build_layout()

        assert layout["main"]["panels"] is not None
        assert layout["main"]["summary"] is not None
        d.close()

    def test_panel_columns_scale_with_terminal_width(self):
        """Model panels wrap into more rows when the terminal is narrow."""
        d = RichProgressDisplay(
            ["m1", "m2", "m3", "m4", "m5"],
            ["commit_messages"],
        )

        assert d._panel_columns(80, 5) == 3
        assert d._panel_columns(120, 5) == 3
        assert d._panel_columns(180, 5) == 5
        d.close()

    def test_refresh_repaints_live_display_immediately(self):
        """Manual-refresh Live display repaints on each state update."""
        d = RichProgressDisplay(["mock"], ["commit_messages"])
        d.enabled = True
        d._live = Mock()

        d.model_started("mock")

        d._live.update.assert_called_once()
        assert d._live.update.call_args.kwargs["refresh"] is True
        d._live = None
        d.close()

    def test_refresh_swallows_live_update_errors(self):
        """Transient Rich update errors do not escape progress callbacks."""
        d = RichProgressDisplay(["mock"], ["commit_messages"])
        d.enabled = True
        d._live = Mock()
        d._live.update.side_effect = RuntimeError("terminal changed size")

        d.model_started("mock")

        assert d._rows["mock"]["status"] == "queued"
        d._live.update.assert_called_once()
        d._live = None
        d.close()

    def test_refresh_swallows_layout_errors(self):
        """Transient layout errors do not escape progress callbacks."""
        d = RichProgressDisplay(["mock"], ["commit_messages"])
        d.enabled = True
        d._live = Mock()
        d._build_layout = Mock(side_effect=RuntimeError("layout failed"))

        d.model_started("mock")

        assert d._rows["mock"]["status"] == "queued"
        d._live.update.assert_not_called()
        d._live = None
        d.close()

    def test_close_swallows_live_stop_errors(self):
        """Terminal cleanup errors do not escape close()."""
        d = RichProgressDisplay(["mock"], ["commit_messages"])
        d.enabled = True
        d._live = Mock()
        d._live.stop.side_effect = RuntimeError("already stopped")

        d.close()

        assert d._live is None

    def test_close_is_idempotent_and_restores_terminal(self):
        """close() emits best-effort terminal restore only once."""
        stream = TtyStringIO()
        d = RichProgressDisplay(["mock"], ["commit_messages"])
        d.enabled = True
        d._live = Mock()

        with patch("sys.stderr", stream):
            d.close()
            d.close()

        assert d._live is None
        assert "\x1b[?1049l" in stream.getvalue()

    def test_periodic_refresh_repaints_while_no_callbacks_arrive(self):
        """Heartbeat refresh keeps the live display moving during slow fixtures."""
        d = RichProgressDisplay(
            ["mock"],
            ["commit_messages"],
            refresh_interval=0.01,
        )
        d.enabled = True
        d._live = Mock()
        d._start_periodic_refresh()

        time.sleep(0.05)

        assert d._live.update.call_count >= 1
        d.close()

    def test_model_panel_colour_by_status(self):
        """Model panels are coloured by status."""
        from io import StringIO as SIO

        # Use non-TTY to avoid live display
        d = RichProgressDisplay(["mock"], ["commit_messages"])

        # Pending
        panel = d._render_model_panel("mock")
        assert "waiting" in str(panel.renderable)

        # Running — call fixture_finished for each fixture to accumulate pass rate
        d.model_started("mock")
        d.benchmark_started("mock", "commit_messages", 3)
        d.fixture_finished("mock", "commit_messages", True)
        d.fixture_finished("mock", "commit_messages", True)
        d.fixture_finished("mock", "commit_messages", False)
        panel = d._render_model_panel("mock")
        rendered = str(panel.renderable)
        assert "commit_messages" in rendered

        # Done
        d.benchmark_finished("mock", "commit_messages", 0)
        d.model_finished("mock", {"total_fixtures": 3, "total_passed": 2})
        panel = d._render_model_panel("mock")
        rendered = str(panel.renderable)
        assert "66.7%" in rendered
        d.close()

    def test_model_panel_renders_markup_as_styles(self):
        """Model panel markup is parsed instead of displayed as tags."""
        from rich.console import Console as RichConsole

        d = RichProgressDisplay(["mock"], ["commit_messages"])
        d.model_started("mock")
        d.benchmark_started("mock", "commit_messages", 2)
        d.fixture_finished("mock", "commit_messages", True)

        console = RichConsole(width=80, color_system=None)
        with console.capture() as capture:
            console.print(d._render_model_panel("mock"))

        rendered = capture.get()
        assert "[cyan]" not in rendered
        assert "[/]" not in rendered
        assert "50.0%" in rendered
        d.close()

    def test_compact_model_panel_hides_token_details(self):
        """Compact model panels prioritize progress and pass rate."""
        from rich.console import Console as RichConsole

        d = RichProgressDisplay(["mock"], ["commit_messages"])
        d.model_started("mock")
        d.benchmark_started("mock", "commit_messages", 2)
        d.fixture_finished("mock", "commit_messages", True)

        console = RichConsole(width=32, color_system=None)
        with console.capture() as capture:
            console.print(d._render_model_panel("mock", compact=True))

        rendered = capture.get()
        assert "50.0%" in rendered
        assert "Tokens:" not in rendered
        assert "Cost:" not in rendered
        d.close()

    def test_compact_model_panel_does_not_wrap_done_benchmark_label(self):
        """Completed compact panels fit in narrow grid cells."""
        from rich.console import Console as RichConsole

        d = RichProgressDisplay(
            ["google/gemini-3.1-flash-lite-preview"],
            ["commit_messages"],
        )
        model = "google/gemini-3.1-flash-lite-preview"
        d._rows[model].update(
            status="done",
            benchmarks_done=1,
            fixtures_total=17,
            fixtures_done=17,
            passed=14,
            errors=3,
        )

        console = RichConsole(width=37, color_system=None)
        with console.capture() as capture:
            console.print(d._render_model_panel(model, compact=True))
        rendered = capture.get()

        assert "1/1 bench" in rendered
        assert "benchmarks" not in rendered
        assert all(len(line) <= 37 for line in rendered.splitlines())
        d.close()

    def test_summary_limit_prioritizes_active_benchmarks(self):
        """Short terminals keep running benchmarks in the visible summary."""
        benchmarks = [
            "blame_forensics",
            "branch_cleanup",
            "cherry_pick",
            "commit_messages",
            "git_clean",
        ]
        d = RichProgressDisplay(["mock"], benchmarks)
        d.model_started("mock")
        d.benchmark_started("mock", "git_clean", 12)

        visible, omitted = d._summary_benchmarks(limit=3)

        assert "git_clean" in visible
        assert omitted == 3
        d.close()

    def test_short_layout_uses_dense_panels_and_limits_summary_rows(self):
        """Short terminals reduce panel height and summary rows to fit."""
        d = RichProgressDisplay(
            ["m1", "m2", "m3", "m4", "m5"],
            ["b1", "b2", "b3", "b4", "b5"],
        )

        plan = d._layout_plan(width=80, height=16)

        assert plan["dense"] is True
        assert plan["panel_height"] == 3
        assert plan["show_summary"] is True
        assert plan["summary_limit"] == 3
        d.close()

    def test_tiny_layout_hides_summary_before_overflowing_vertically(self):
        """Very short terminals prioritize model status over the summary table."""
        d = RichProgressDisplay(
            ["m1", "m2", "m3", "m4", "m5"],
            ["b1", "b2", "b3"],
        )

        plan = d._layout_plan(width=80, height=8)

        assert plan["dense"] is True
        assert plan["show_summary"] is False
        assert plan["summary_limit"] == 0
        assert plan["panel_rows"] == 1
        d.close()

    def test_verbose_log_buffer(self):
        """Verbose mode buffers log lines."""
        d = RichProgressDisplay(["mock"], ["commit_messages"], verbose=True)
        d.benchmark_started("mock", "commit_messages", 3)
        d.fixture_finished("mock", "commit_messages", True, fixture_id="f1", similarity=0.9)
        d.fixture_finished("mock", "commit_messages", False, fixture_id="f2", similarity=0.2)

        assert len(d._log_lines) == 2
        assert "PASS" in d._log_lines[0]
        assert "FAIL" in d._log_lines[1]
        log_panel = d._render_log_panel()
        assert "f1" in str(log_panel.renderable)
        assert "f2" in str(log_panel.renderable)
        d.close()

    def test_close_stops_live_and_prints_summary(self):
        """close() stops live display and prints final summary."""
        d = RichProgressDisplay(["mock"], ["commit_messages"])
        d.model_started("mock")
        d.benchmark_started("mock", "commit_messages", 2)
        d.fixture_finished("mock", "commit_messages", True)
        d.fixture_finished("mock", "commit_messages", True)
        d.benchmark_finished("mock", "commit_messages", 0)
        d.model_finished("mock", {"total_fixtures": 2, "total_passed": 2})
        d.close()
        # Should not raise — close is idempotent when live is None

    def test_multiple_models_summary_omits_delta(self):
        """Multi-model summary keeps only benchmark and model columns."""
        from rich.console import Console as RichConsole

        d = RichProgressDisplay(["mock", "gpt-4o"], ["commit_messages"])

        for model in ["mock", "gpt-4o"]:
            d.model_started(model)
            d.benchmark_started(model, "commit_messages", 4)
            passed = 3 if model == "mock" else 4
            for _ in range(passed):
                d.fixture_finished(model, "commit_messages", True)
            for _ in range(4 - passed):
                d.fixture_finished(model, "commit_messages", False)
            d.benchmark_finished(model, "commit_messages", 0)
            d.model_finished(model, {"total_fixtures": 4, "total_passed": passed})

        table = d._render_summary_table()
        # Render the Rich table to a string for inspection
        console = RichConsole(width=120)
        with console.capture() as capture:
            console.print(table)
        rendered = capture.get()
        assert "Δ" not in rendered
        assert "delta" not in rendered.lower()
        d.close()

    def test_summary_table_uses_one_column_per_model(self):
        """Full summary does not add comparison columns."""
        d = RichProgressDisplay(
            ["m1", "m2", "m3", "m4"],
            ["commit_messages"],
        )

        for index, model in enumerate(["m1", "m2", "m3", "m4"]):
            d.model_started(model)
            d.benchmark_started(model, "commit_messages", 4)
            passed = index + 1
            for _ in range(passed):
                d.fixture_finished(model, "commit_messages", True)
            for _ in range(4 - passed):
                d.fixture_finished(model, "commit_messages", False)
            d.benchmark_finished(model, "commit_messages", 4 - passed)
            d.model_finished(model, {"total_fixtures": 4, "total_passed": passed})

        table = d._render_summary_table(width=140)

        assert len(table.columns) == 5  # Benchmark + 4 models
        d.close()

    def test_summary_table_keeps_model_cells_on_one_line(self):
        """Pass-rate cells do not wrap percentage and raw counts apart."""
        from rich.console import Console as RichConsole

        d = RichProgressDisplay(
            ["m1", "m2", "m3", "m4"],
            ["blame_forensics", "branch_cleanup"],
        )

        for model in ["m1", "m2", "m3", "m4"]:
            for bench in ["blame_forensics", "branch_cleanup"]:
                d.model_started(model)
                d.benchmark_started(model, bench, 12)
                for _ in range(10):
                    d.fixture_finished(model, bench, True)
                for _ in range(2):
                    d.fixture_finished(model, bench, False)
                d.benchmark_finished(model, bench, 2)
            d.model_finished(model, {"total_fixtures": 24, "total_passed": 20})

        console = RichConsole(width=80, color_system=None)
        with console.capture() as capture:
            console.print(d._render_summary_table(width=80))
        rendered = capture.get()

        assert "(10/12)" in rendered
        assert all(line.strip() != "(10/12)" for line in rendered.splitlines())
        d.close()

    def test_summary_table_compacts_for_many_model_layouts(self):
        """Five-plus model runs get an aggregate summary for scalability."""
        from rich.console import Console as RichConsole

        models = [
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
            "minimax/minimax-m2.5",
            "deepseek/deepseek-v4-flash",
            "google/gemini-3.1-flash-lite-preview",
        ]
        d = RichProgressDisplay(models, ["commit_messages"])

        for index, model in enumerate(models):
            d.model_started(model)
            d.benchmark_started(model, "commit_messages", 4)
            passed = min(4, index + 1)
            for _ in range(passed):
                d.fixture_finished(model, "commit_messages", True)
            for _ in range(4 - passed):
                d.fixture_finished(model, "commit_messages", False)
            d.benchmark_finished(model, "commit_messages", 4 - passed)
            d.model_finished(model, {"total_fixtures": 4, "total_passed": passed})

        table = d._render_summary_table(width=112)

        assert [column.header for column in table.columns] == [
            "Benchmark",
            "Done",
            "Best",
            "Range",
        ]

        console = RichConsole(width=112, color_system=None)
        with console.capture() as capture:
            console.print(table)
        rendered = capture.get()

        assert all(len(line) <= 112 for line in rendered.splitlines())
        d.close()


class TestBuildRunEnvelope:
    """Tests for build_run_envelope helper."""

    def test_envelope_structure(self):
        """Test that envelope has expected structure."""
        from gitbench.cli import build_run_envelope

        results = [
            {"benchmark": "commit_messages", "total": 12, "passed": 10, "pass_at_k": 0.8333, "scores": [], "errors": 0},
        ]
        envelope = build_run_envelope(model="gpt-4o", profile="openai", results=results)

        assert envelope["version"] == 1
        assert envelope["schema_version"] == 1
        assert envelope["benchmark_suite_version"] == BENCHMARK_SUITE_VERSION
        assert "timestamp" in envelope
        assert envelope["model"] == "gpt-4o"
        assert envelope["profile"] == "openai"
        assert envelope["summary"]["total_benchmarks"] == 1
        assert envelope["summary"]["total_fixtures"] == 12
        assert envelope["summary"]["total_passed"] == 10
        assert envelope["summary"]["overall_pass_at_k"] == 0.8333
        assert envelope["results"] == results

    def test_envelope_git_sha(self):
        """Test that envelope includes git SHA when available."""
        from gitbench.cli import build_run_envelope

        envelope = build_run_envelope(model="mock", profile="(inline)", results=[])
        # git_sha may be None if not in a git repo, but the key should exist
        assert "git_sha" in envelope


class TestWriteOutputDir:
    """Tests for write_output_dir helper."""

    def test_creates_directory_and_file(self, tmp_path):
        """Test that write_output_dir creates the directory and writes a file."""
        from gitbench.cli import write_output_dir

        envelope = {
            "version": 1,
            "timestamp": "2026-04-25T13:30:00+00:00",
            "model": "gpt-4o",
            "profile": "openai",
            "summary": {},
            "results": [],
        }

        output_dir = tmp_path / "results"
        written = write_output_dir(envelope, str(output_dir))

        assert written.exists()
        assert written.parent == output_dir
        assert "gpt-4o" in written.name
        assert written.suffix == ".json"

        data = json.loads(written.read_text())
        assert data["model"] == "gpt-4o"

    def test_sanitizes_model_name(self, tmp_path):
        """Test that model names with special chars are sanitized in filenames."""
        from gitbench.cli import write_output_dir

        envelope = {
            "version": 1,
            "timestamp": "2026-04-25T13:30:00+00:00",
            "model": "anthropic/claude-3.5:latest",
            "profile": "(inline)",
            "summary": {},
            "results": [],
        }

        written = write_output_dir(envelope, str(tmp_path))
        assert "/" not in written.name
        assert ":" not in written.name

    def test_collision_avoids_overwrite(self, tmp_path):
        """Test that same timestamp+model produces separate files instead of overwriting."""
        from gitbench.cli import write_output_dir

        envelope = {
            "version": 1,
            "timestamp": "2026-04-25T13:30:00+00:00",
            "model": "gpt-4o",
            "profile": "openai",
            "summary": {"total_passed": 1},
            "results": [],
        }

        first = write_output_dir(envelope, str(tmp_path))
        second = write_output_dir(envelope, str(tmp_path))

        # Both files should exist (no overwrite)
        assert first.exists()
        assert second.exists()
        assert first != second

        # First file should have base name, second should have _2 suffix
        assert "gpt-4o" in first.name
        assert "_2" in second.name

        # Contents differ (different pass counts)
        data_first = json.loads(first.read_text())
        data_second = json.loads(second.read_text())
        assert data_first["summary"]["total_passed"] == data_second["summary"]["total_passed"]

    def test_three_collisions(self, tmp_path):
        """Test that multiple collisions get _2, _3, etc."""
        from gitbench.cli import write_output_dir

        envelope = {
            "version": 1,
            "timestamp": "2026-04-25T13:30:00+00:00",
            "model": "mock",
            "profile": "(inline)",
            "summary": {},
            "results": [],
        }

        paths = [write_output_dir(envelope, str(tmp_path)) for _ in range(4)]
        names = [p.name for p in paths]

        assert names[0] == f"2026-04-25T13-30-00_mock_v{BENCHMARK_SUITE_VERSION}.json"
        assert names[1] == f"2026-04-25T13-30-00_mock_v{BENCHMARK_SUITE_VERSION}_2.json"
        assert names[2] == f"2026-04-25T13-30-00_mock_v{BENCHMARK_SUITE_VERSION}_3.json"
        assert names[3] == f"2026-04-25T13-30-00_mock_v{BENCHMARK_SUITE_VERSION}_4.json"

        # All files exist
        for p in paths:
            assert p.exists()


class TestWriteJsonl:
    """Tests for write_jsonl helper."""

    def test_appends_to_file(self, tmp_path):
        """Test that write_jsonl appends a line to the file."""
        from gitbench.cli import write_jsonl

        envelope = {
            "version": 1,
            "timestamp": "2026-04-25T13:30:00+00:00",
            "model": "mock",
            "profile": "(inline)",
            "summary": {},
            "results": [],
        }

        jsonl_path = tmp_path / "results.jsonl"
        write_jsonl(envelope, str(jsonl_path))
        write_jsonl(envelope, str(jsonl_path))

        lines = jsonl_path.read_text().strip().split("\n")
        assert len(lines) == 2

        for line in lines:
            data = json.loads(line)
            assert data["model"] == "mock"


class TestResolveRunOutputPath:
    """Tests for resolving run artifact output paths."""

    def test_defaults(self):
        result = resolve_run_output_path(
            {},
            json_output=None,
            default_timestamp="20260504T010203Z",
        )
        assert result == DEFAULT_JSON_OUTPUT_PATH.format(
            timestamp="20260504T010203Z",
            version=BENCHMARK_SUITE_VERSION,
        )

    def test_config_outputs(self):
        config = {"outputs": {"json": "runs/latest.json"}}
        result = resolve_run_output_path(config, json_output=None)
        assert result == "runs/latest.json"

    def test_cli_options_win_over_config(self):
        config = {"outputs": {"json": "config.json"}}
        result = resolve_run_output_path(
            config,
            json_output="cli.json",
            default_timestamp="20260504T010203Z",
        )
        assert result == "cli.json"

    def test_creates_parent_directories(self, tmp_path):
        """Test that write_jsonl creates parent directories if needed."""
        from gitbench.cli import write_jsonl

        envelope = {"version": 1, "model": "mock", "timestamp": "", "profile": "", "summary": {}, "results": []}
        jsonl_path = tmp_path / "sub" / "dir" / "results.jsonl"
        write_jsonl(envelope, str(jsonl_path))

        assert jsonl_path.exists()


class TestRunnerReasoningLevel:
    """Tests for BenchmarkRunner reasoning_level into Score."""

    def test_runner_populates_reasoning_level_in_score(self):
        """Score gets reasoning_level from the adapter."""
        from gitbench.harness.model import MockModelClient
        from gitbench.harness.runner import BenchmarkRunner
        from gitbench.harness.types import Fixture

        client = MockModelClient(response="test output")
        client.reasoning_level = "high"

        runner = BenchmarkRunner({}, client)

        class FakeBench:
            def load_fixtures(self):
                return []
            def setup_fixture(self, fixture):
                return None, None
            def get_diff(self, repo_path):
                return ""
            def format_prompt(self, fixture, diff):
                return ""
            def score(self, fixture, output, repo_path=None):
                from gitbench.harness.types import Score
                return Score(fixture_id="f1", passed=True, similarity=1.0, model_output="test")

        fixture = Fixture(
            id="f1", description="test", setup=[], prompt="",
            expected="", scoring={"type": "exact_match", "threshold": 1.0},
        )
        _, score = runner._run_fixture(FakeBench(), fixture)
        assert score.reasoning_level == "high"

    def test_runner_score_none_when_no_reasoning(self):
        """Score reasoning_level is None when adapter has none."""
        from gitbench.harness.model import MockModelClient
        from gitbench.harness.runner import BenchmarkRunner
        from gitbench.harness.types import Fixture

        client = MockModelClient(response="test output")

        runner = BenchmarkRunner({}, client)

        class FakeBench:
            def load_fixtures(self):
                return []
            def setup_fixture(self, fixture):
                return None, None
            def get_diff(self, repo_path):
                return ""
            def format_prompt(self, fixture, diff):
                return ""
            def score(self, fixture, output, repo_path=None):
                from gitbench.harness.types import Score
                return Score(fixture_id="f1", passed=True, similarity=1.0, model_output="test")

        fixture = Fixture(
            id="f1", description="test", setup=[], prompt="",
            expected="", scoring={"type": "exact_match", "threshold": 1.0},
        )
        _, score = runner._run_fixture(FakeBench(), fixture)
        assert score.reasoning_level is None


class TestRunnerSelectedFixtures:
    """Tests for internal selected fixture execution."""

    def test_run_benchmark_executes_only_selected_fixtures_in_order(self):
        from gitbench.harness.model import MockModelClient
        from gitbench.harness.runner import BenchmarkRunner
        from gitbench.harness.types import Fixture, Score

        calls = []

        class FakeBench:
            def load_fixtures(self):
                return [
                    Fixture("f001", "one", [], "p1", "ok", {}),
                    Fixture("f002", "two", [], "p2", "ok", {}),
                    Fixture("f003", "three", [], "p3", "ok", {}),
                ]

            def setup_fixture(self, fixture):
                calls.append(("setup", fixture.id))

                class Executor:
                    def cleanup(self):
                        calls.append(("cleanup", fixture.id))

                return Executor(), "/tmp/repo"

            def get_diff(self, repo_path):
                calls.append(("diff", repo_path))
                return "diff"

            def format_prompt(self, fixture, diff):
                calls.append(("prompt", fixture.id, diff))
                return fixture.prompt

            def score(self, fixture, output, repo_path=None):
                calls.append(("score", fixture.id, output, repo_path))
                return Score(
                    fixture_id=fixture.id,
                    passed=True,
                    similarity=1.0,
                    model_output=output,
                )

        runner = BenchmarkRunner({"fake": FakeBench}, MockModelClient(response="ok"))
        result = runner.run_benchmark("fake", selected_fixture_ids=["f003", "f001"])

        assert [score.fixture_id for score in result.scores] == ["f003", "f001"]
        assert [call for call in calls if call[0] == "setup"] == [
            ("setup", "f003"),
            ("setup", "f001"),
        ]
        assert result.total == 2
        assert result.passed == 2

    def test_run_benchmark_fails_before_execution_for_missing_selected_fixture(self):
        from gitbench.harness.model import MockModelClient
        from gitbench.harness.runner import BenchmarkRunner
        from gitbench.harness.types import Fixture

        class FakeBench:
            def load_fixtures(self):
                return [Fixture("f001", "one", [], "p1", "ok", {})]

            def setup_fixture(self, fixture):
                raise AssertionError("setup should not run")

        runner = BenchmarkRunner({"fake": FakeBench}, MockModelClient())

        with pytest.raises(ValueError, match="f999"):
            runner.run_benchmark("fake", selected_fixture_ids=["f999"])
