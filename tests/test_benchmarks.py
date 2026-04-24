"""Tests for benchmark classes."""

from abc import ABC

import pytest

from gitbench.benchmarks import Benchmark
from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark
from gitbench.benchmarks.merge_conflicts import MergeConflictsBenchmark
from gitbench.benchmarks.cherry_pick import CherryPickBenchmark
from gitbench.benchmarks.git_bisect import GitBisectBenchmark
from gitbench.benchmarks.rebase import RebaseBenchmark
from gitbench.benchmarks.reflog import ReflogBenchmark


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


class TestMergeConflictsBenchmark:
    """Test the merge_conflicts benchmark implementation."""

    def test_benchmark_inherits_from_benchmark_abc(self):
        """Test that MergeConflictsBenchmark is a subclass of Benchmark."""
        assert issubclass(MergeConflictsBenchmark, Benchmark)

    def test_benchmark_has_name(self):
        """Test that the benchmark has the expected name."""
        assert MergeConflictsBenchmark.name == "merge_conflicts"

    def test_benchmark_has_description(self):
        """Test that the benchmark has a description."""
        assert isinstance(MergeConflictsBenchmark.description, str)
        assert len(MergeConflictsBenchmark.description) > 0

    def test_benchmark_can_be_instantiated(self):
        """Test that MergeConflictsBenchmark can be instantiated."""
        benchmark = MergeConflictsBenchmark()
        assert benchmark is not None

    def test_load_fixtures_returns_list(self):
        """Test that load_fixtures returns a list of fixtures."""
        benchmark = MergeConflictsBenchmark()
        fixtures = benchmark.load_fixtures()
        assert isinstance(fixtures, list)

    def test_fixture_count_at_least_10(self):
        """Test that at least 10 fixtures are loaded."""
        benchmark = MergeConflictsBenchmark()
        fixtures = benchmark.load_fixtures()
        assert len(fixtures) >= 10, f"Expected at least 10 fixtures, got {len(fixtures)}"

    def test_fixtures_have_required_fields(self):
        """Test that all fixtures have required fields."""
        benchmark = MergeConflictsBenchmark()
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
        benchmark = MergeConflictsBenchmark()
        fixtures = benchmark.load_fixtures()

        ids = [f.id for f in fixtures]
        assert len(ids) == len(set(ids)), f"Duplicate fixture IDs found: {ids}"

    def test_score_method_works(self):
        """Test that the score method works correctly."""
        from gitbench.harness.types import Score

        benchmark = MergeConflictsBenchmark()
        fixtures = benchmark.load_fixtures()

        # Score with an identical expected value should score high
        fixture = fixtures[0]
        result = benchmark.score(fixture, fixture.expected)

        assert isinstance(result, Score)
        assert result.fixture_id == fixture.id
        assert result.similarity > 0.8  # Should be very similar


class TestCherryPickBenchmark:
    """Test the cherry_pick benchmark implementation."""

    def test_benchmark_inherits_from_benchmark_abc(self):
        """Test that CherryPickBenchmark is a subclass of Benchmark."""
        assert issubclass(CherryPickBenchmark, Benchmark)

    def test_benchmark_has_name(self):
        """Test that the benchmark has the expected name."""
        assert CherryPickBenchmark.name == "cherry_pick"

    def test_benchmark_has_description(self):
        """Test that the benchmark has a description."""
        assert isinstance(CherryPickBenchmark.description, str)
        assert len(CherryPickBenchmark.description) > 0

    def test_benchmark_can_be_instantiated(self):
        """Test that CherryPickBenchmark can be instantiated."""
        benchmark = CherryPickBenchmark()
        assert benchmark is not None

    def test_load_fixtures_returns_list(self):
        """Test that load_fixtures returns a list of fixtures."""
        benchmark = CherryPickBenchmark()
        fixtures = benchmark.load_fixtures()
        assert isinstance(fixtures, list)

    def test_fixture_count_at_least_10(self):
        """Test that at least 10 fixtures are loaded."""
        benchmark = CherryPickBenchmark()
        fixtures = benchmark.load_fixtures()
        assert len(fixtures) >= 10, f"Expected at least 10 fixtures, got {len(fixtures)}"

    def test_fixtures_have_required_fields(self):
        """Test that all fixtures have required fields."""
        benchmark = CherryPickBenchmark()
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
        benchmark = CherryPickBenchmark()
        fixtures = benchmark.load_fixtures()

        ids = [f.id for f in fixtures]
        assert len(ids) == len(set(ids)), f"Duplicate fixture IDs found: {ids}"

    def test_score_method_works(self):
        """Test that the score method works correctly."""
        from gitbench.harness.types import Score

        benchmark = CherryPickBenchmark()
        fixtures = benchmark.load_fixtures()

        # Score with an identical expected value should score high
        fixture = fixtures[0]
        result = benchmark.score(fixture, fixture.expected)

        assert isinstance(result, Score)
        assert result.fixture_id == fixture.id
        assert result.similarity > 0.8  # Should be very similar

    def test_setup_fixture_produces_conflict(self):
        """Test that setup_fixture produces a conflicted repo for each fixture."""
        import tempfile
        from gitbench.utils.git import GitExecutor

        benchmark = CherryPickBenchmark()
        fixtures = benchmark.load_fixtures()

        # Test first fixture only to keep test fast
        fixture = fixtures[0]
        executor, repo_path = benchmark.setup_fixture(fixture)

        # Verify cherry-pick left the repo in a conflicted state
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        conflicted_files = [f for f in result.stdout.strip().split("\n") if f]
        assert len(conflicted_files) > 0, "Expected conflicted files after cherry-pick"

        executor.cleanup()

    def test_get_diff_contains_conflict_markers(self):
        """Test that get_diff returns content with conflict markers."""
        benchmark = CherryPickBenchmark()
        fixtures = benchmark.load_fixtures()

        fixture = fixtures[0]
        executor, repo_path = benchmark.setup_fixture(fixture)
        diff = benchmark.get_diff(repo_path)

        assert "<<<<<<<" in diff, "Expected conflict markers in diff"
        assert "=======" in diff, "Expected conflict markers in diff"
        assert ">>>>>>>" in diff, "Expected conflict markers in diff"

        executor.cleanup()


class TestGitBisectBenchmark:
    """Test the git_bisect benchmark implementation."""

    def test_benchmark_inherits_from_benchmark_abc(self):
        """Test that GitBisectBenchmark is a subclass of Benchmark."""
        assert issubclass(GitBisectBenchmark, Benchmark)

    def test_benchmark_has_name(self):
        """Test that the benchmark has the expected name."""
        assert GitBisectBenchmark.name == "git_bisect"

    def test_benchmark_has_description(self):
        """Test that the benchmark has a description."""
        assert isinstance(GitBisectBenchmark.description, str)
        assert len(GitBisectBenchmark.description) > 0

    def test_benchmark_can_be_instantiated(self):
        """Test that GitBisectBenchmark can be instantiated."""
        benchmark = GitBisectBenchmark()
        assert benchmark is not None

    def test_load_fixtures_returns_list(self):
        """Test that load_fixtures returns a list of fixtures."""
        benchmark = GitBisectBenchmark()
        fixtures = benchmark.load_fixtures()
        assert isinstance(fixtures, list)

    def test_fixture_count_at_least_10(self):
        """Test that at least 10 fixtures are loaded."""
        benchmark = GitBisectBenchmark()
        fixtures = benchmark.load_fixtures()
        assert len(fixtures) >= 10, f"Expected at least 10 fixtures, got {len(fixtures)}"

    def test_fixtures_have_required_fields(self):
        """Test that all fixtures have required fields."""
        benchmark = GitBisectBenchmark()
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
        benchmark = GitBisectBenchmark()
        fixtures = benchmark.load_fixtures()

        ids = [f.id for f in fixtures]
        assert len(ids) == len(set(ids)), f"Duplicate fixture IDs found: {ids}"

    def test_score_method_works(self):
        """Test that the score method works correctly."""
        from gitbench.harness.types import Score

        benchmark = GitBisectBenchmark()
        fixtures = benchmark.load_fixtures()

        # Score with an identical expected value should score high
        fixture = fixtures[0]
        result = benchmark.score(fixture, fixture.expected)

        assert isinstance(result, Score)
        assert result.fixture_id == fixture.id
        assert result.similarity > 0.8  # Should be very similar


class TestRebaseBenchmark:
    """Test the rebase benchmark implementation."""

    def test_benchmark_inherits_from_benchmark_abc(self):
        """Test that RebaseBenchmark is a subclass of Benchmark."""
        assert issubclass(RebaseBenchmark, Benchmark)

    def test_benchmark_has_name(self):
        """Test that the benchmark has the expected name."""
        assert RebaseBenchmark.name == "rebase"

    def test_benchmark_has_description(self):
        """Test that the benchmark has a description."""
        assert isinstance(RebaseBenchmark.description, str)
        assert len(RebaseBenchmark.description) > 0

    def test_benchmark_can_be_instantiated(self):
        """Test that RebaseBenchmark can be instantiated."""
        benchmark = RebaseBenchmark()
        assert benchmark is not None

    def test_load_fixtures_returns_list(self):
        """Test that load_fixtures returns a list of fixtures."""
        benchmark = RebaseBenchmark()
        fixtures = benchmark.load_fixtures()
        assert isinstance(fixtures, list)

    def test_fixture_count_at_least_10(self):
        """Test that at least 10 fixtures are loaded."""
        benchmark = RebaseBenchmark()
        fixtures = benchmark.load_fixtures()
        assert len(fixtures) >= 10, f"Expected at least 10 fixtures, got {len(fixtures)}"

    def test_fixtures_have_required_fields(self):
        """Test that all fixtures have required fields."""
        benchmark = RebaseBenchmark()
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
        benchmark = RebaseBenchmark()
        fixtures = benchmark.load_fixtures()

        ids = [f.id for f in fixtures]
        assert len(ids) == len(set(ids)), f"Duplicate fixture IDs found: {ids}"

    def test_score_method_works(self):
        """Test that the score method works correctly."""
        from gitbench.harness.types import Score

        benchmark = RebaseBenchmark()
        fixtures = benchmark.load_fixtures()

        # Score with an identical expected value should score high
        fixture = fixtures[0]
        result = benchmark.score(fixture, fixture.expected)

        assert isinstance(result, Score)
        assert result.fixture_id == fixture.id
        assert result.similarity > 0.8  # Should be very similar


class TestReflogBenchmark:
    """Test the reflog benchmark implementation."""

    def test_benchmark_inherits_from_benchmark_abc(self):
        """Test that ReflogBenchmark is a subclass of Benchmark."""
        assert issubclass(ReflogBenchmark, Benchmark)

    def test_benchmark_has_name(self):
        """Test that the benchmark has the expected name."""
        assert ReflogBenchmark.name == "reflog"

    def test_benchmark_has_description(self):
        """Test that the benchmark has a description."""
        assert isinstance(ReflogBenchmark.description, str)
        assert len(ReflogBenchmark.description) > 0

    def test_benchmark_can_be_instantiated(self):
        """Test that ReflogBenchmark can be instantiated."""
        benchmark = ReflogBenchmark()
        assert benchmark is not None

    def test_load_fixtures_returns_list(self):
        """Test that load_fixtures returns a list of fixtures."""
        benchmark = ReflogBenchmark()
        fixtures = benchmark.load_fixtures()
        assert isinstance(fixtures, list)

    def test_fixture_count_at_least_10(self):
        """Test that at least 10 fixtures are loaded."""
        benchmark = ReflogBenchmark()
        fixtures = benchmark.load_fixtures()
        assert len(fixtures) >= 10, f"Expected at least 10 fixtures, got {len(fixtures)}"

    def test_fixtures_have_required_fields(self):
        """Test that all fixtures have required fields."""
        benchmark = ReflogBenchmark()
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
        benchmark = ReflogBenchmark()
        fixtures = benchmark.load_fixtures()

        ids = [f.id for f in fixtures]
        assert len(ids) == len(set(ids)), f"Duplicate fixture IDs found: {ids}"

    def test_score_method_works(self):
        """Test that the score method works correctly."""
        from gitbench.harness.types import Score

        benchmark = ReflogBenchmark()
        fixtures = benchmark.load_fixtures()

        # Score with an identical expected value should score high
        fixture = fixtures[0]
        result = benchmark.score(fixture, fixture.expected)

        assert isinstance(result, Score)
        assert result.fixture_id == fixture.id
        assert result.similarity > 0.8  # Should be very similar


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