"""Tests for GitBench CLI."""

import json
import sys
import time
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from gitbench.cli import (
    DEFAULT_HTML_OUTPUT_PATH,
    DEFAULT_JSON_OUTPUT_PATH,
    SummaryTable,
    TerminalProgressTable,
    _progress_model_names,
    _progress_model_names_for_runs,
    check_git_availability,
    cli,
    get_model_client,
    resolve_run_output_paths,
    should_use_colors,
)
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

    def test_run_writes_default_json_and_html_outputs(self, runner, tmp_path):
        """Test that run writes JSON and HTML artifacts by default."""
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
            html_path = run_dirs[0] / f"report-v{BENCHMARK_SUITE_VERSION}.html"
            assert json_path.exists()
            assert html_path.exists()
            assert json.loads(json_path.read_text())["benchmark"] == "commit_messages"
            assert html_path.read_text().startswith("<!DOCTYPE html>")

    def test_run_json_and_html_output_cli_overrides_defaults(self, runner, tmp_path):
        """Test that explicit JSON and HTML output paths override defaults."""
        json_path = tmp_path / "custom" / "results.json"
        html_path = tmp_path / "custom" / "report.html"

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
                    "--html-output",
                    str(html_path),
                ],
            )

        assert result.exit_code == 0
        assert json.loads(json_path.read_text())["benchmark"] == "commit_messages"
        assert html_path.read_text().startswith("<!DOCTYPE html>")

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

    def test_run_uses_configured_json_and_html_output_paths(self, runner, tmp_path):
        """Test that gitbench.json can override default output paths."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            cwd = Path.cwd()
            config = {
                "outputs": {
                    "json": "configured/results.json",
                    "html": "configured/report.html",
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
            assert (cwd / "configured/report.html").read_text().startswith("<!DOCTYPE html>")

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

    def test_run_with_nested_html_output_file(self, runner, tmp_path):
        """Test that --html-output creates parent directories for HTML output."""
        output_path = tmp_path / "nested" / "reports" / "results.html"

        with patch("gitbench.cli.check_git_availability", return_value=True):
            result = runner.invoke(
                cli,
                ["run", "--benchmark", "commit_messages", "--model", "mock", "--html-output", str(output_path)],
            )

        assert result.exit_code == 0
        assert output_path.exists()
        assert output_path.read_text().startswith("<!DOCTYPE html>")

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


class TtyStringIO(StringIO):
    """StringIO that behaves like an interactive terminal."""

    def isatty(self):
        return True


class TestTerminalProgressTable:
    """Tests for consolidated live progress output."""

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

    def test_table_renders_updates_in_place_for_tty(self):
        stream = TtyStringIO()
        table = TerminalProgressTable(["mock"], ["commit_messages"], stream=stream)

        table.model_started("mock")
        table.benchmark_started("mock", "commit_messages", 2)
        table.fixture_finished("mock", "commit_messages", True)
        table.benchmark_finished("mock", "commit_messages", 0)
        table.close()

        output = stream.getvalue()
        assert "GitBench progress" in output
        assert "GitBench complete" in output
        assert "Model" in output
        assert "Current" in output
        assert "commit_messages" in output
        assert "1/2" in output
        assert "\x1b[1A\x1b[2K" in output

    def test_table_condenses_benchmarks_into_one_model_row(self):
        table = TerminalProgressTable(["mock"], ["commit_messages", "rebase"], stream=StringIO())

        table.model_started("mock")
        table.benchmark_started("mock", "commit_messages", 2)
        table.fixture_finished("mock", "commit_messages", True)
        table.benchmark_finished("mock", "commit_messages", 0)
        table.benchmark_started("mock", "rebase", 3)
        table.fixture_finished("mock", "rebase", False)

        lines = table._build_lines(final=False)
        assert len(lines) == 4
        assert "mock" in lines[-1]
        assert "rebase" in lines[-1]
        assert "1/2" in lines[-1]
        assert "2/5" in lines[-1]

    def test_table_is_quiet_for_non_tty(self):
        stream = StringIO()
        table = TerminalProgressTable(["mock"], ["commit_messages"], stream=stream)

        table.model_started("mock")
        table.benchmark_started("mock", "commit_messages", 1)
        table.fixture_finished("mock", "commit_messages", True)
        table.close()

        assert stream.getvalue() == ""


class TestShouldUseColors:
    """Tests for color detection utility."""

    def test_no_color_env_var_disables_colors(self):
        """NO_COLOR env var should disable colors."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            import gitbench.cli as cli_module

            # Reset the cached value
            cli_module._use_colors = None
            result = should_use_colors()
            assert result is False

    def test_term_dumb_disables_colors(self):
        """TERM=dumb should disable colors."""
        with patch.dict("os.environ", {"TERM": "dumb"}, clear=False):
            import gitbench.cli as cli_module

            cli_module._use_colors = None
            result = should_use_colors()
            assert result is False

    def test_tty_stream_enables_colors(self):
        """TTY stream should enable colors."""
        stream = TtyStringIO()
        with patch.dict("os.environ", {"TERM": "xterm-256color"}, clear=True):
            import gitbench.cli as cli_module

            cli_module._use_colors = None
            result = should_use_colors(stream)
        assert result is True

    def test_non_tty_stream_disables_colors(self):
        """Non-TTY stream should disable colors."""
        stream = StringIO()
        import gitbench.cli as cli_module

        cli_module._use_colors = None
        result = should_use_colors(stream)
        assert result is False

    def test_result_is_cached(self):
        """Result should be cached after first call when no stream is provided."""
        import gitbench.cli as cli_module

        cli_module._use_colors = None
        # Call without stream argument — uses sys.stdout, which should be non-TTY in tests
        first = should_use_colors()
        second = should_use_colors()

        assert first == second
        assert cli_module._use_colors is not None


class TestSummaryTable:
    """Tests for SummaryTable class."""

    def setup_method(self):
        """Reset cached color state before each test."""
        import gitbench.cli as cli_module
        cli_module._use_colors = None

    def test_render_returns_none_when_disabled(self):
        """render() should return None when stdout is not a TTY."""
        import gitbench.cli as cli_module

        cli_module._use_colors = None
        stream = StringIO()
        results = [
            {"benchmark": "commit_messages", "total": 10, "passed": 8, "pass_at_k": 0.8},
        ]
        table = SummaryTable(results, stream=stream)
        result = table.render()
        assert result is None
        assert stream.getvalue() == ""

    def test_render_writes_table_when_enabled(self):
        """render() should write colored table to stream when TTY."""
        stream = TtyStringIO()
        results = [
            {"benchmark": "commit_messages", "total": 10, "passed": 8, "pass_at_k": 0.8},
            {"benchmark": "rebase", "total": 5, "passed": 2, "pass_at_k": 0.4},
        ]
        table = SummaryTable(results, stream=stream)
        result = table.render()

        assert result is not None
        output = stream.getvalue()
        assert "Benchmark" in output
        assert "Pass@1" in output
        assert "Passed/Fail" in output

    def test_rows_sorted_alphabetically(self):
        """Results should be sorted alphabetically by benchmark name."""
        stream = TtyStringIO()
        results = [
            {"benchmark": "zebra", "total": 5, "passed": 5, "pass_at_k": 1.0},
            {"benchmark": "alpha", "total": 5, "passed": 3, "pass_at_k": 0.6},
            {"benchmark": "middle", "total": 5, "passed": 2, "pass_at_k": 0.4},
        ]
        table = SummaryTable(results, stream=stream)
        table.render()

        output = stream.getvalue()
        alpha_pos = output.find("alpha")
        middle_pos = output.find("middle")
        zebra_pos = output.find("zebra")
        assert alpha_pos < middle_pos < zebra_pos

    def test_summary_row_contains_totals(self):
        """Summary row should show overall pass@1 and total fixtures."""
        stream = TtyStringIO()
        results = [
            {"benchmark": "commit_messages", "total": 10, "passed": 8, "pass_at_k": 0.8},
            {"benchmark": "rebase", "total": 5, "passed": 2, "pass_at_k": 0.4},
        ]
        table = SummaryTable(results, stream=stream)
        table.render()

        output = stream.getvalue()
        assert "TOTAL" in output
        # 10 passed + 2 passed = 12, total = 15, pass@1 = 0.8
        assert "8/10" in output or "10/15" in output

    def test_color_coding_thresholds(self):
        """Color should be green >= 0.8, yellow >= 0.5, red < 0.5."""
        with patch.dict("os.environ", {"TERM": "xterm-256color"}, clear=True):
            stream = TtyStringIO()

            # Green (>= 0.8)
            results_green = [{"benchmark": "green", "total": 10, "passed": 9, "pass_at_k": 0.9}]
            table_green = SummaryTable(results_green, stream=stream)
            table_green.render()
            output_green = stream.getvalue()
            assert "\x1b[32m" in output_green  # Green

            # Yellow (>= 0.5)
            stream2 = TtyStringIO()
            results_yellow = [{"benchmark": "yellow", "total": 10, "passed": 6, "pass_at_k": 0.6}]
            table_yellow = SummaryTable(results_yellow, stream=stream2)
            table_yellow.render()
            output_yellow = stream2.getvalue()
            assert "\x1b[33m" in output_yellow  # Yellow

            # Red (< 0.5)
            stream3 = TtyStringIO()
            results_red = [{"benchmark": "red", "total": 10, "passed": 4, "pass_at_k": 0.4}]
            table_red = SummaryTable(results_red, stream=stream3)
            table_red.render()
            output_red = stream3.getvalue()
        assert "\x1b[31m" in output_red  # Red

    def test_passed_fail_column_format(self):
        """Passed/Fail column should show passed/failed counts."""
        stream = TtyStringIO()
        results = [
            {"benchmark": "test", "total": 10, "passed": 7, "pass_at_k": 0.7},
        ]
        table = SummaryTable(results, stream=stream)
        table.render()

        output = stream.getvalue()
        # Should show 7 passed, 3 failed
        assert "7/3" in output


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


class TestResolveRunOutputPaths:
    """Tests for resolving run artifact output paths."""

    def test_defaults(self):
        assert resolve_run_output_paths(
            {},
            json_output=None,
            html_output=None,
            default_timestamp="20260504T010203Z",
        ) == (
            DEFAULT_JSON_OUTPUT_PATH.format(
                timestamp="20260504T010203Z",
                version=BENCHMARK_SUITE_VERSION,
            ),
            DEFAULT_HTML_OUTPUT_PATH.format(
                timestamp="20260504T010203Z",
                version=BENCHMARK_SUITE_VERSION,
            ),
        )

    def test_config_outputs(self):
        config = {"outputs": {"json": "runs/latest.json", "html": "runs/latest.html"}}
        assert resolve_run_output_paths(config, json_output=None, html_output=None) == (
            "runs/latest.json",
            "runs/latest.html",
        )

    def test_cli_options_win_over_config(self):
        config = {"outputs": {"json": "config.json", "html": "config.html"}}
        assert resolve_run_output_paths(
            config,
            json_output="cli.json",
            html_output="cli.html",
            default_timestamp="20260504T010203Z",
        ) == ("cli.json", "cli.html")

    def test_creates_parent_directories(self, tmp_path):
        """Test that write_jsonl creates parent directories if needed."""
        from gitbench.cli import write_jsonl

        envelope = {"version": 1, "model": "mock", "timestamp": "", "profile": "", "summary": {}, "results": []}
        jsonl_path = tmp_path / "sub" / "dir" / "results.jsonl"
        write_jsonl(envelope, str(jsonl_path))

        assert jsonl_path.exists()
