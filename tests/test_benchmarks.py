"""Tests for benchmark classes."""

from abc import ABC

import pytest

from gitbench.benchmarks import Benchmark
from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark


class TestBenchmarkABC:
    """Test that Benchmark ABC properly enforces the interface."""

    def test_benchmark_is_abstract(self):
        """Verify that Benchmark is an ABC."""
        assert hasattr(Benchmark, "__abstractmethods__")
        assert len(Benchmark.__abstractmethods__) > 0

    def test_cannot_instantiate_benchmark_directly(self):
        """Test that Benchmark cannot be instantiated without implementing abstract methods."""
        with pytest.raises(TypeError) as exc_info:
            Benchmark()
        # TypeError should be raised because abstract methods are not implemented
        assert "abstract" in str(exc_info.value).lower()

    def test_benchmark_has_required_methods(self):
        """Test that Benchmark ABC defines the required abstract methods."""
        abstract_methods = Benchmark.__abstractmethods__
        assert "load_fixtures" in abstract_methods
        assert "score" in abstract_methods

    def test_benchmark_has_class_attributes(self):
        """Test that Benchmark defines name and description class attributes."""
        assert hasattr(Benchmark, "name")
        assert hasattr(Benchmark, "description")


class TestCommitMessagesBenchmark:
    """Test the commit_messages benchmark implementation."""

    def test_benchmark_inherits_from_benchmark_abc(self):
        """Test that CommitMessagesBenchmark is a subclass of Benchmark."""
        assert issubclass(CommitMessagesBenchmark, Benchmark)

    def test_benchmark_has_name(self):
        """Test that the benchmark has the expected name."""
        assert CommitMessagesBenchmark.name == "commit_messages"

    def test_benchmark_has_description(self):
        """Test that the benchmark has a description."""
        assert isinstance(CommitMessagesBenchmark.description, str)
        assert len(CommitMessagesBenchmark.description) > 0

    def test_benchmark_can_be_instantiated(self):
        """Test that CommitMessagesBenchmark can be instantiated."""
        benchmark = CommitMessagesBenchmark()
        assert benchmark is not None

    def test_load_fixtures_returns_list(self):
        """Test that load_fixtures returns a list of fixtures."""
        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()
        assert isinstance(fixtures, list)

    def test_fixture_count_at_least_10(self):
        """Test that at least 10 fixtures are loaded."""
        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()
        assert len(fixtures) >= 10, f"Expected at least 10 fixtures, got {len(fixtures)}"

    def test_fixtures_have_required_fields(self):
        """Test that all fixtures have required fields."""
        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()

        for fixture in fixtures:
            assert hasattr(fixture, "id")
            assert hasattr(fixture, "description")
            assert hasattr(fixture, "setup")
            assert hasattr(fixture, "prompt")
            assert hasattr(fixture, "expected")
            assert hasattr(fixture, "scoring")

            assert isinstance(fixture.id, str)
            assert isinstance(fixture.setup, list)
            assert isinstance(fixture.prompt, str)
            assert isinstance(fixture.expected, str)
            assert isinstance(fixture.scoring, dict)

    def test_fixture_ids_are_unique(self):
        """Test that all fixture IDs are unique."""
        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()

        ids = [f.id for f in fixtures]
        assert len(ids) == len(set(ids)), f"Duplicate fixture IDs found: {ids}"

    def test_score_method_works(self):
        """Test that the score method works correctly."""
        from gitbench.harness.types import Fixture, Score

        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()

        # Score with an identical message should score high
        fixture = fixtures[0]
        result = benchmark.score(fixture, fixture.expected)

        assert isinstance(result, Score)
        assert result.fixture_id == fixture.id
        assert result.similarity > 0.8  # Should be very similar

    def test_score_method_handles_different_output(self):
        """Test that the score method handles different outputs correctly."""
        from gitbench.harness.types import Fixture, Score

        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()

        fixture = fixtures[0]
        # Score with a completely different message should score low
        result = benchmark.score(fixture, "completely unrelated text that has nothing to do with the expected message")

        assert isinstance(result, Score)
        assert result.similarity < 0.4  # Should be fairly different (not extremely low due to common words)


class TestBenchmarkDiscovery:
    """Test that benchmarks are properly discovered."""

    def test_commit_messages_benchmark_is_importable(self):
        """Test that the commit_messages benchmark can be imported."""
        from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark

        assert CommitMessagesBenchmark.name == "commit_messages"

    def test_all_benchmarks_have_names(self):
        """Test that all discovered benchmarks have names."""
        from gitbench.cli import discover_benchmarks

        benchmarks = discover_benchmarks()
        for name, benchmark_class in benchmarks.items():
            assert hasattr(benchmark_class, "name")
            assert isinstance(benchmark_class.name, str)
            assert len(benchmark_class.name) > 0


class TestBenchmarkFixtureLoading:
    """Test fixture loading for the commit_messages benchmark."""

    def test_loads_from_correct_directory(self):
        """Test that fixtures are loaded from the correct directory."""
        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()

        # All fixtures should have IDs starting with 'f' and 3 digits
        for fixture in fixtures:
            assert fixture.id.startswith("f")
            assert len(fixture.id) >= 4

    def test_fixtures_have_diverse_descriptions(self):
        """Test that fixtures have diverse descriptions covering different scenarios."""
        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()

        # Get all descriptions
        descriptions = [f.description for f in fixtures]

        # Check that we have variety (at least 5 unique descriptions)
        unique_descriptions = set(descriptions)
        assert len(unique_descriptions) >= 5, (
            f"Expected at least 5 unique fixture descriptions, "
            f"got {len(unique_descriptions)}: {descriptions}"
        )

    def test_fixtures_cover_different_git_operations(self):
        """Test that fixtures cover different git operations."""
        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()

        # All fixtures should have non-empty setup commands
        for fixture in fixtures:
            assert len(fixture.setup) > 0, f"Fixture {fixture.id} has no setup commands"

        # The total number of setup commands across all fixtures should be substantial
        total_commands = sum(len(f.setup) for f in fixtures)
        assert total_commands >= 30, (
            f"Expected at least 30 total setup commands across fixtures, "
            f"got {total_commands}"
        )