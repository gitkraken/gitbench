"""Integration tests for the full GitBench harness pipeline."""

import json
import subprocess
import sys
from pathlib import Path

from gitbench.benchmarks import Benchmark
from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark
from gitbench.cli import discover_benchmarks
from gitbench.harness.model import MockModelClient
from gitbench.harness.scorer import Scorer


class TestCLIListCommand:
    """Test the `gitbench list` CLI command."""

    def test_list_shows_commit_messages_benchmark(self):
        """Verify `gitbench list` shows the commit_messages benchmark."""
        result = subprocess.run(
            [sys.executable, "-m", "gitbench.cli", "list"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0, f"CLI exited with code {result.returncode}: {result.stderr}"
        assert "commit_messages" in result.stdout, (
            f"Expected 'commit_messages' in output, got:\n{result.stdout}"
        )

    def test_list_shows_benchmark_description(self):
        """Verify the benchmark listing includes the description."""
        result = subprocess.run(
            [sys.executable, "-m", "gitbench.cli", "list"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "commit message" in result.stdout.lower()


class TestFixtureCount:
    """Test that the commit_messages benchmark loads the expected number of fixtures."""

    def test_fixture_count_at_least_10(self):
        """Verify at least 10 fixtures are loaded."""
        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()
        assert len(fixtures) >= 10, f"Expected at least 10 fixtures, got {len(fixtures)}"


class TestJSONOutputContract:
    """Test that the CLI produces valid JSON output matching the R009 contract."""

    def _parse_json_output(self, stdout: str) -> dict:
        """Parse JSON from CLI output that may have a progress header line."""
        # CLI emits "Running benchmark 'commit_messages' with model 'mock'..." before JSON.
        # Find the first '{' and parse from there.
        json_start = stdout.find("{")
        if json_start == -1:
            raise ValueError(f"No JSON found in output:\n{stdout}")
        return json.loads(stdout[json_start:])

    def _run_benchmark_cli(self) -> str:
        """Run the benchmark CLI and return stdout."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "gitbench.cli",
                "run",
                "--benchmark",
                "commit_messages",
                "--model",
                "mock",
                "--output-mode",
                "text",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0, (
            f"CLI exited with code {result.returncode}. stderr:\n{result.stderr}\nstdout:\n{result.stdout}"
        )
        return result.stdout

    def _run_json_benchmark(self) -> dict:
        """Run the benchmark CLI and parse the JSON result."""
        stdout = self._run_benchmark_cli()
        return self._parse_json_output(stdout)

    def test_output_is_valid_json(self):
        """Verify the CLI output contains valid JSON (possibly after a progress line)."""
        data = self._run_json_benchmark()
        assert isinstance(data, dict), "JSON root must be an object"

    def test_output_has_required_top_level_fields(self):
        """Verify output contains benchmark, total, passed, pass_at_k, scores, errors."""
        data = self._run_json_benchmark()
        required_fields = ["benchmark", "total", "passed", "pass_at_k", "scores", "errors"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_output_has_correct_field_types(self):
        """Verify field types match the R009 contract."""
        data = self._run_json_benchmark()
        assert isinstance(data["benchmark"], str)
        assert isinstance(data["total"], int)
        assert isinstance(data["passed"], int)
        assert isinstance(data["pass_at_k"], (int, float))
        assert isinstance(data["scores"], list)
        assert isinstance(data["errors"], int)

    def test_scores_list_has_entries(self):
        """Verify the scores list contains entries."""
        data = self._run_json_benchmark()
        assert len(data["scores"]) > 0, "scores list should not be empty"

    def test_each_score_has_required_fields(self):
        """Verify each score entry has fixture_id, passed, similarity, model_output."""
        data = self._run_json_benchmark()
        score_fields = ["fixture_id", "passed", "similarity", "model_output"]
        for i, score in enumerate(data["scores"]):
            for field in score_fields:
                assert field in score, f"Score {i} missing field: {field}"
            # Type checks
            assert isinstance(score["fixture_id"], str)
            assert isinstance(score["passed"], bool)
            assert isinstance(score["similarity"], (int, float))
            assert isinstance(score["model_output"], str)

    def test_pass_at_k_in_output(self):
        """Verify pass_at_k field is present (R009 core requirement)."""
        data = self._run_json_benchmark()
        assert "pass_at_k" in data, "pass_at_k field missing from output"
        assert isinstance(data["pass_at_k"], (int, float))
        assert 0.0 <= data["pass_at_k"] <= 1.0, "pass_at_k should be between 0 and 1"

    def test_total_equals_scores_count(self):
        """Verify total field matches the length of the scores list."""
        data = self._run_json_benchmark()
        assert data["total"] == len(data["scores"]), (
            f"total ({data['total']}) should equal len(scores) ({len(data['scores'])})"
        )

    def test_passed_count_matches_scores(self):
        """Verify passed count matches the number of passing scores in the list."""
        data = self._run_json_benchmark()
        passed_count = sum(1 for s in data["scores"] if s["passed"])
        assert data["passed"] == passed_count, (
            f"passed ({data['passed']}) should equal sum of passing scores ({passed_count})"
        )


class TestBenchmarkAutoDiscovery:
    """Test that benchmarks are auto-discovered correctly."""

    def test_commit_messages_in_registry(self):
        """Verify commit_messages is in the discovered benchmark registry."""
        benchmarks = discover_benchmarks()
        assert "commit_messages" in benchmarks, (
            f"commit_messages not found in benchmarks: {list(benchmarks.keys())}"
        )

    def test_all_discovered_benchmarks_are_valid(self):
        """Verify all discovered benchmarks are valid Benchmark subclasses."""
        benchmarks = discover_benchmarks()
        for name, benchmark_class in benchmarks.items():
            assert issubclass(benchmark_class, Benchmark), (
                f"{name} is not a Benchmark subclass"
            )
            assert hasattr(benchmark_class, "name"), f"{name} missing name attribute"
            assert benchmark_class.name == name, (
                f"Benchmark class name '{benchmark_class.name}' != registry key '{name}'"
            )


class TestMockModelClient:
    """Test that MockModelClient works correctly with the full pipeline."""

    def test_mock_model_used_by_default(self):
        """Verify mock model is used when --model mock is specified."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "gitbench.cli",
                "run",
                "--benchmark",
                "commit_messages",
                "--model",
                "mock",
                "--output-mode",
                "text",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0

    def _run_json_benchmark(self) -> dict:
        """Run the benchmark CLI and parse the JSON result."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "gitbench.cli",
                "run",
                "--benchmark",
                "commit_messages",
                "--model",
                "mock",
                "--output-mode",
                "text",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        stdout = result.stdout
        json_start = stdout.find("{")
        if json_start == -1:
            raise ValueError(f"No JSON found in output:\n{stdout}")
        return json.loads(stdout[json_start:])

    def test_mock_model_returns_mock_response(self):
        """Verify the mock model output is 'Mock response' in all scores."""
        data = self._run_json_benchmark()
        for score in data["scores"]:
            assert score["model_output"] == "Mock response", (
                f"Expected 'Mock response', got: {score['model_output']}"
            )

    def test_mock_model_uses_message_history(self):
        """Verify MockModelClient stores message history for inspection."""
        client = MockModelClient()
        from gitbench.harness.types import ModelMessage

        messages = [ModelMessage(role="user", content="Hello")]
        client.generate(messages)
        assert client.last_messages == messages
        assert client.call_count == 1

    def test_mock_model_response_update(self):
        """Verify MockModelClient response can be updated."""
        client = MockModelClient(response="First")
        from gitbench.harness.types import ModelMessage

        messages = [ModelMessage(role="user", content="Hello")]
        assert client.generate(messages)["text"] == "First"
        client.set_response("Second")
        assert client.generate(messages)["text"] == "Second"


class TestScorer:
    """Test the scorer works correctly in the full pipeline."""

    def test_scorer_produces_consistent_scores(self):
        """Verify the Scorer produces consistent similarity scores."""
        scorer = Scorer()
        from gitbench.harness.types import Fixture

        fixture = Fixture(
            id="test",
            description="test",
            setup=[],
            prompt="test",
            expected="fix: resolve issue",
            scoring={"type": "similarity", "threshold": 0.5},
        )

        score = scorer.score(fixture, "fix: resolve issue")
        assert 0.0 <= score.similarity <= 1.0
        assert isinstance(score.passed, bool)

    def test_scorer_identical_strings_score_high(self):
        """Verify identical strings produce a high similarity score."""
        scorer = Scorer()
        from gitbench.harness.types import Fixture

        fixture = Fixture(
            id="test",
            description="test",
            setup=[],
            prompt="test",
            expected="feat: add new feature",
            scoring={"type": "similarity", "threshold": 0.5},
        )

        score = scorer.score(fixture, "feat: add new feature")
        assert score.similarity > 0.9, f"Expected high similarity for identical strings, got {score.similarity}"

    def test_scorer_different_strings_score_low(self):
        """Verify very different strings produce a low similarity score."""
        scorer = Scorer()
        from gitbench.harness.types import Fixture

        fixture = Fixture(
            id="test",
            description="test",
            setup=[],
            prompt="test",
            expected="feat: add new feature",
            scoring={"type": "similarity", "threshold": 0.5},
        )

        score = scorer.score(fixture, "unrelated gibberish text here")
        assert score.similarity < 0.3, f"Expected low similarity for different strings, got {score.similarity}"

    def test_scorer_threshold_affects_passed(self):
        """Verify the threshold setting affects the passed field."""
        from gitbench.harness.types import Fixture

        fixture = Fixture(
            id="test",
            description="test",
            setup=[],
            prompt="test",
            expected="feat: add new feature",
            scoring={"type": "similarity", "threshold": 0.5},
        )

        # Score the fixture with two slightly different outputs
        scorer = Scorer()

        # Perfect match should pass
        score_perfect = scorer.score(fixture, "feat: add new feature")
        assert score_perfect.passed, (
            f"Perfect match should pass but got similarity={score_perfect.similarity}"
        )

        # Very different should not pass
        score_different = scorer.score(fixture, "completely unrelated text that makes no sense")
        assert not score_different.passed, (
            f"Very different text should not pass but got similarity={score_different.similarity}"
        )


class TestVerboseOutput:
    """Test that verbose output works correctly."""

    def test_verbose_flag_produces_per_fixture_output(self):
        """Verify --verbose flag produces per-fixture output on stderr."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "gitbench.cli",
                "run",
                "--benchmark",
                "commit_messages",
                "--model",
                "mock",
                "--output-mode",
                "text",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "passed=" in result.stderr, "Verbose output should contain 'passed='"
        assert "similarity=" in result.stderr, "Verbose output should contain 'similarity='"


class TestEndToEndPipeline:
    """End-to-end pipeline integration tests."""

    def test_full_pipeline_produces_valid_results(self):
        """Verify the full pipeline from fixtures to scoring produces valid results."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "gitbench.cli",
                "run",
                "--benchmark",
                "commit_messages",
                "--model",
                "mock",
                "--output-mode",
                "text",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        stdout = result.stdout
        json_start = stdout.find("{")
        assert json_start != -1, f"No JSON in output:\n{stdout}"
        data = json.loads(stdout[json_start:])

        # Verify overall structure
        assert data["benchmark"] == "commit_messages"
        assert data["total"] >= 10
        assert data["errors"] == 0  # No errors with mock model

        # Verify all scores have required fields
        for score in data["scores"]:
            assert "fixture_id" in score
            assert "passed" in score
            assert "similarity" in score
            assert "model_output" in score

    def test_cli_exits_zero_on_success(self):
        """Verify the CLI exits with code 0 on successful completion."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "gitbench.cli",
                "run",
                "--benchmark",
                "commit_messages",
                "--model",
                "mock",
                "--output-mode",
                "text",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0

    def test_unknown_benchmark_exits_nonzero(self):
        """Verify the CLI exits with a non-zero code for an unknown benchmark."""
        result = subprocess.run(
            [sys.executable, "-m", "gitbench.cli", "run", "--benchmark", "nonexistent", "--model", "mock"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode != 0, "CLI should exit with non-zero code for unknown benchmark"
