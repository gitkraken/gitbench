"""Tests for runner attempt-status classification."""

from unittest.mock import MagicMock, patch

import pytest

from gitbench.harness.model import MockModelClient, RetriesExhaustedError
from gitbench.harness.runner import BenchmarkRunner
from gitbench.harness.types import ModelMessage, Score


class _FailingModelClient(MockModelClient):
    """Mock client that always exhausts retries."""

    def __init__(self):
        # Deliberately avoid super().__init__ so we don't need a model name.
        self.reasoning_level = None

    def generate(self, messages, **kwargs):
        from gitbench.harness.model import RequestTelemetry
        raise RetriesExhaustedError(
            message="failed",
            last_error=TimeoutError("timed out"),
            telemetry=RequestTelemetry(attempts=3),
        )


class TestRunnerFailureClassification:
    """The runner classifies exhausted transport failures as operational."""

    def test_retries_exhausted_marked_operational(self, tmp_path):
        """Exhausted retries produce an operational-failure score."""
        from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark

        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()
        fixture = fixtures[0]

        runner = BenchmarkRunner(
            {"commit_messages": type(benchmark)},
            _FailingModelClient(),
            output_mode="text",
        )
        fixture_id, score = runner._run_fixture(benchmark, fixture)

        assert fixture_id == fixture.id
        assert isinstance(score, Score)
        assert score.passed is False
        assert score.operational_failure is True
        assert score.request_telemetry is not None
        assert score.request_telemetry["attempts"] == 3

    def test_structured_output_error_is_quality_failure(self, tmp_path):
        """Structured-output parse failures are model-quality failures."""
        from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark
        from gitbench.structured_output import contract_for_benchmark_fixture

        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()
        # Find a fixture with a structured-output contract.
        fixture = None
        for f in fixtures:
            if contract_for_benchmark_fixture(f, "commit_messages") is not None:
                fixture = f
                break
        if fixture is None:
            pytest.skip("No structured-output fixture available")

        # Mock client returns content that will fail schema validation.
        client = MockModelClient(model="mock")
        client.generate = lambda messages, **kwargs: {
            "text": "not valid json",
            "parsed_payload": None,
            "structured_error": "invalid json",
        }

        runner = BenchmarkRunner(
            {"commit_messages": type(benchmark)},
            client,
            output_mode="json_schema",
        )
        fixture_id, score = runner._run_fixture(benchmark, fixture)

        assert score.passed is False
        assert score.operational_failure is False
        assert score._structured_error is not None

    def test_successful_attempt_records_provenance(self, tmp_path):
        """Successful attempts record route metadata and request config."""
        from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark

        benchmark = CommitMessagesBenchmark()
        fixture = benchmark.load_fixtures()[0]
        client = MockModelClient(model="mock")

        runner = BenchmarkRunner(
            {"commit_messages": type(benchmark)},
            client,
            output_mode="text",
            model_generate_kwargs={"max_tokens": 100},
        )
        fixture_id, score = runner._run_fixture(benchmark, fixture)

        assert score.provider_route_metadata is not None
        assert score.provider_route_metadata.get("model_id") == "mock"
        assert score.request_config is not None
        assert score.request_config.get("output_mode") == "text"
        assert score.request_config.get("model_generate_kwargs") == {"max_tokens": 100}

