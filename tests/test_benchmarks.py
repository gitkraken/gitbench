"""Tests for benchmark classes."""

from abc import ABC

import pytest

from gitbench.benchmarks import Benchmark
from gitbench.benchmarks.branch_cleanup import BranchCleanupBenchmark
from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark
from gitbench.benchmarks.commit_squash import CommitSquashBenchmark
from gitbench.benchmarks.merge_conflicts import MergeConflictsBenchmark
from gitbench.benchmarks.cherry_pick import CherryPickBenchmark
from gitbench.benchmarks.git_bisect import GitBisectBenchmark
from gitbench.benchmarks.rebase import RebaseBenchmark
from gitbench.benchmarks.reflog import ReflogBenchmark
from gitbench.benchmarks.stash_recovery import StashRecoveryBenchmark
from gitbench.benchmarks.submodule_usage import SubmoduleUsageBenchmark
from gitbench.benchmarks.tag_management import TagManagementBenchmark
from gitbench.benchmarks.worktree_usage import WorktreeUsageBenchmark
from gitbench.benchmarks.git_log_format import GitLogFormatBenchmark
from gitbench.benchmarks.git_show import GitShowBenchmark
from gitbench.benchmarks.git_clean import GitCleanBenchmark


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
        assert "score" in abstract_methods

    def test_benchmark_has_class_attributes(self):
        """Test that Benchmark defines name and description class attributes."""
        assert hasattr(Benchmark, "name")
        assert hasattr(Benchmark, "description")


# Lazily populated — benchmarks are discovered once at module level.
_ALL_BENCHMARKS: list[type] | None = None


def _get_all_benchmarks() -> list[type]:
    global _ALL_BENCHMARKS
    if _ALL_BENCHMARKS is None:
        from gitbench.cli import discover_benchmarks
        _ALL_BENCHMARKS = list(discover_benchmarks().values())
    return _ALL_BENCHMARKS


class TestBenchmarkContract:
    """Parametrized conformance tests — every benchmark subclass must pass."""

    @pytest.mark.parametrize("benchmark_cls", _get_all_benchmarks())
    def test_inherits_from_benchmark_abc(self, benchmark_cls):
        assert issubclass(benchmark_cls, Benchmark)

    @pytest.mark.parametrize("benchmark_cls", _get_all_benchmarks())
    def test_has_name(self, benchmark_cls):
        assert isinstance(benchmark_cls.name, str)
        assert len(benchmark_cls.name) > 0

    @pytest.mark.parametrize("benchmark_cls", _get_all_benchmarks())
    def test_has_description(self, benchmark_cls):
        assert isinstance(benchmark_cls.description, str)
        assert len(benchmark_cls.description) > 0

    @pytest.mark.parametrize("benchmark_cls", _get_all_benchmarks())
    def test_can_be_instantiated(self, benchmark_cls):
        benchmark = benchmark_cls()
        assert benchmark is not None

    @pytest.mark.parametrize("benchmark_cls", _get_all_benchmarks())
    def test_load_fixtures_returns_list(self, benchmark_cls):
        benchmark = benchmark_cls()
        fixtures = benchmark.load_fixtures()
        assert isinstance(fixtures, list)
        assert len(fixtures) >= 10, (
            f"Expected at least 10 fixtures for {benchmark_cls.name}, "
            f"got {len(fixtures)}"
        )

    @pytest.mark.parametrize("benchmark_cls", _get_all_benchmarks())
    def test_fixtures_have_required_fields(self, benchmark_cls):
        benchmark = benchmark_cls()
        for fixture in benchmark.load_fixtures():
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

    @pytest.mark.parametrize("benchmark_cls", _get_all_benchmarks())
    def test_fixture_ids_are_unique(self, benchmark_cls):
        benchmark = benchmark_cls()
        ids = [f.id for f in benchmark.load_fixtures()]
        assert len(ids) == len(set(ids)), (
            f"Duplicate fixture IDs in {benchmark_cls.name}: {ids}"
        )


class TestCommitMessagesBenchmark:
    """Test the commit_messages benchmark implementation."""

    @pytest.fixture
    def mock_judge_client(self):
        """Create a mock JudgeClient that returns high similarity."""
        from unittest.mock import MagicMock
        mock = MagicMock()
        mock.evaluate_commit_message.return_value = 0.95
        return mock

    def test_score_method_works(self, mock_judge_client):
        """Test that the score method works correctly."""
        from gitbench.harness.scorer import Scorer
        from gitbench.harness.types import Fixture, Score

        benchmark = CommitMessagesBenchmark()
        benchmark._scorer = Scorer(judge_client=mock_judge_client)
        fixtures = benchmark.load_fixtures()

        # Score with an identical message should score high
        fixture = fixtures[0]
        result = benchmark.score(fixture, fixture.expected)

        assert isinstance(result, Score)
        assert result.fixture_id == fixture.id
        assert result.similarity > 0.8  # Should be very similar

    def test_score_method_handles_different_output(self):
        """Test that the score method handles different outputs correctly."""
        from unittest.mock import MagicMock
        from gitbench.harness.scorer import Scorer
        from gitbench.harness.types import Fixture, Score

        mock_judge = MagicMock()
        mock_judge.evaluate_commit_message.return_value = 0.2

        benchmark = CommitMessagesBenchmark()
        benchmark._scorer = Scorer(judge_client=mock_judge)
        fixtures = benchmark.load_fixtures()

        fixture = fixtures[0]
        # Score with a completely different message should score low
        result = benchmark.score(fixture, "completely unrelated text that has nothing to do with the expected message")

        assert isinstance(result, Score)
        assert result.similarity < 0.4  # Should be fairly different (not extremely low due to common words)


class TestMergeConflictsBenchmark:
    """Test the merge_conflicts benchmark implementation."""


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

    def test_multi_file_incomplete_resolution_fails(self):
        """Test that resolving only one file in a multi-file fixture is insufficient."""
        benchmark = MergeConflictsBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == "f010")
        incomplete_output = "main.py:\ndef main():\n    print(\"Running enterprise\")\n"

        result = benchmark.score(fixture, incomplete_output)

        assert result.passed is False
        assert result.similarity == 0.0


class TestCommitSquashBenchmark:
    """Test the commit_squash benchmark implementation."""


    def test_load_fixtures_returns_commit_selection_fixtures(self):
        """Test that commit_squash fixtures use selection scoring."""
        benchmark = CommitSquashBenchmark()
        fixtures = benchmark.load_fixtures()

        assert len(fixtures) >= 10
        assert all(f.scoring["type"] == "commit_selection" for f in fixtures)

    def test_verbose_correct_answer_passes(self):
        """Test that correct verbose answers are not penalized."""
        from gitbench.harness.types import Score

        benchmark = CommitSquashBenchmark()
        fixture = benchmark.load_fixtures()[0]
        output = (
            "Use interactive rebase and mark these commits as squash:\n"
            "- abc1234 WIP: add main.py\n"
            "- def5678 WIP: continue work\n"
            "Keep the final Complete feature commit as the clean message."
        )

        result = benchmark.score(fixture, output)

        assert isinstance(result, Score)
        assert result.passed is True
        assert result.similarity == 1.0

    def test_target_commit_context_is_allowed(self):
        """Test that mentioning the squash target for context does not fail."""
        benchmark = CommitSquashBenchmark()
        fixture = benchmark.load_fixtures()[1]
        output = (
            "Commit to squash: fixup: Fix typo in hello.py. "
            "It should be squashed into Add hello world program."
        )

        result = benchmark.score(fixture, output)

        assert result.passed is True
        assert result.similarity == 1.0

    def test_missing_expected_commit_fails(self):
        """Test that omitting an expected WIP commit fails."""
        benchmark = CommitSquashBenchmark()
        fixture = benchmark.load_fixtures()[0]

        result = benchmark.score(fixture, "Only squash WIP: add main.py")

        assert result.passed is False
        assert result.similarity == 0.5
        assert "WIP: continue work" in result.error

    def test_extra_selected_commit_fails(self):
        """Test that selecting an extra non-squash commit fails."""
        benchmark = CommitSquashBenchmark()
        fixture = benchmark.load_fixtures()[0]
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            output = (
                "- WIP: add main.py\n"
                "- WIP: continue work\n"
                "- Initial commit"
            )

            result = benchmark.score(fixture, output, repo_path=repo_path)

            assert result.passed is False
            assert result.similarity == 1.0
            assert "Extra selected commit messages" in result.error
            assert "Initial commit" in result.error
        finally:
            executor.cleanup()

    def test_hash_only_correct_answer_passes(self):
        """Test that answers using commit hashes instead of messages pass."""
        import subprocess

        benchmark = CommitSquashBenchmark()
        fixture = benchmark.load_fixtures()[0]
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            hashes = []
            for subject in ("WIP: add main.py", "WIP: continue work"):
                result = subprocess.run(
                    ["git", "log", "--format=%h", "--grep", subject],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                hashes.append(result.stdout.strip())

            result = benchmark.score(fixture, ", ".join(hashes), repo_path=repo_path)

            assert result.passed is True
            assert result.similarity == 1.0
        finally:
            executor.cleanup()


class TestBranchCleanupBenchmark:
    """Test branch cleanup selection scoring."""

    def test_exact_branch_selection_passes(self):
        benchmark = BranchCleanupBenchmark()
        fixture = benchmark.load_fixtures()[0]

        result = benchmark.score(fixture, fixture.expected)

        assert result.passed is True
        assert result.similarity == 1.0
        assert result.error is None

    def test_missing_branch_selection_fails(self):
        benchmark = BranchCleanupBenchmark()
        fixture = benchmark.load_fixtures()[0]

        result = benchmark.score(fixture, "")

        assert result.passed is False
        assert result.similarity == 0.0
        assert "Missing" in result.error

    def test_extra_branch_selection_fails(self):
        benchmark = BranchCleanupBenchmark()
        fixture = benchmark.load_fixtures()[0]

        result = benchmark.score(fixture, f"{fixture.expected}\nfeature-login")

        assert result.passed is False
        assert result.similarity == 1.0
        assert "Extra" in result.error


class TestCherryPickBenchmark:
    """Test the cherry_pick benchmark implementation."""


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

    def test_get_diff_includes_test_results_by_commit(self):
        """Test that bisect context includes per-commit PASS/FAIL results."""
        benchmark = GitBisectBenchmark()
        fixture = benchmark.load_fixtures()[0]
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            diff = benchmark.get_diff(repo_path)

            assert "Test results by commit (oldest first):" in diff
            assert ": PASS" in diff
            assert f"{fixture.expected}: FAIL" in diff
        finally:
            executor.cleanup()

    def test_bisect_scores_dynamic_commit_hash(self):
        """Test that bisect scoring accepts the generated target hash."""
        benchmark = GitBisectBenchmark()
        fixture = benchmark.load_fixtures()[0]
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            target_hash = next(
                full_hash
                for full_hash, _, subject in benchmark._commits(repo_path)
                if subject == fixture.expected
            )

            result = benchmark.score(fixture, target_hash[:7], repo_path=repo_path)

            assert result.passed is True
            assert result.similarity == 1.0
        finally:
            executor.cleanup()

    def test_bisect_scores_target_subject(self):
        """Test that bisect scoring accepts the target subject line."""
        benchmark = GitBisectBenchmark()
        fixture = benchmark.load_fixtures()[0]
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            result = benchmark.score(fixture, fixture.expected, repo_path=repo_path)

            assert result.passed is True
            assert result.similarity == 1.0
        finally:
            executor.cleanup()

    def test_bisect_rejects_wrong_commit(self):
        """Test that bisect scoring rejects a non-target commit."""
        benchmark = GitBisectBenchmark()
        fixture = benchmark.load_fixtures()[0]
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            wrong_hash = next(
                full_hash
                for full_hash, _, subject in benchmark._commits(repo_path)
                if subject != fixture.expected
            )

            result = benchmark.score(fixture, wrong_hash[:7], repo_path=repo_path)

            assert result.passed is False
            assert result.similarity == 0.0
        finally:
            executor.cleanup()


class TestRebaseBenchmark:
    """Test the rebase benchmark implementation."""


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

    def test_reflog_scores_dynamic_commit_hash(self):
        """Test that reflog scoring accepts the live hash for the target commit."""
        benchmark = ReflogBenchmark()
        fixture = benchmark.load_fixtures()[0]
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            target_hash = next(
                line.split()[0]
                for line in benchmark.get_diff(repo_path).splitlines()
                if fixture.expected in line
            )

            result = benchmark.score(fixture, target_hash, repo_path=repo_path)

            assert result.passed is True
            assert result.similarity == 1.0
        finally:
            executor.cleanup()

    def test_reflog_scores_matching_head_selector(self):
        """Test that reflog scoring accepts a selector resolving to the target commit."""
        benchmark = ReflogBenchmark()
        fixture = benchmark.load_fixtures()[0]
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            result = benchmark.score(
                fixture,
                "git reset --hard HEAD@{1}",
                repo_path=repo_path,
            )

            assert result.passed is True
            assert result.similarity == 1.0
        finally:
            executor.cleanup()

    def test_reflog_does_not_accept_message_when_hash_requested(self):
        """Test that hash-command fixtures require identifying the reflog commit."""
        benchmark = ReflogBenchmark()
        fixture = benchmark.load_fixtures()[0]
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            result = benchmark.score(fixture, fixture.expected, repo_path=repo_path)

            assert result.passed is False
            assert result.similarity == 0.0
        finally:
            executor.cleanup()

    def test_reflog_accepts_message_for_message_fixture(self):
        """Test the one reflog fixture that asks for the commit message."""
        benchmark = ReflogBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == "f010")
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            result = benchmark.score(fixture, fixture.expected, repo_path=repo_path)

            assert result.passed is True
            assert result.similarity == 1.0
        finally:
            executor.cleanup()


class TestStashRecoveryBenchmark:
    """Test the stash_recovery benchmark implementation."""


    def test_get_diff_includes_stash_details(self):
        """Test that stash context includes patch details for generic WIP entries."""
        benchmark = StashRecoveryBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == "f002")
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            diff = benchmark.get_diff(repo_path)

            assert "Stash details:" in diff
            assert "stash@{2}:" in diff
            assert "+Work A" in diff
        finally:
            executor.cleanup()

    def test_stash_recovery_scores_reference_inside_command(self):
        """Test that stash scoring accepts the expected reference in a command."""
        benchmark = StashRecoveryBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == "f002")

        result = benchmark.score(fixture, "git stash apply stash@{2}")

        assert result.passed is True
        assert result.similarity == 1.0

    def test_stash_recovery_rejects_wrong_reference(self):
        """Test that adjacent stash refs do not pass by string similarity."""
        benchmark = StashRecoveryBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == "f002")

        result = benchmark.score(fixture, "stash@{0}")

        assert result.passed is False
        assert result.similarity == 0.0

    def test_stash_recovery_fixture_f009_targets_older_stash(self):
        """Test that keep-this points to the older stash entry."""
        benchmark = StashRecoveryBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == "f009")
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            diff = benchmark.get_diff(repo_path)

            assert fixture.expected == "stash@{1}"
            assert "stash@{1}: On main: keep-this" in diff
        finally:
            executor.cleanup()


class TestSubmoduleUsageBenchmark:
    """Test the submodule_usage benchmark against its real fixtures."""

    def test_load_fixtures_returns_stateful_submodule_fixtures(self):
        benchmark = SubmoduleUsageBenchmark()
        fixtures = benchmark.load_fixtures()

        assert len(fixtures) == 12
        assert {fixture.id for fixture in fixtures} == {f"f{i:03d}" for i in range(1, 13)}
        assert all(
            fixture.scoring["type"] in {"state_assertions", "exact_match", "command_equivalence"}
            for fixture in fixtures
        )

    @pytest.mark.parametrize("fixture_id", [f"f{i:03d}" for i in range(1, 13)])
    def test_expected_answer_passes_fixture_state_checks(self, fixture_id):
        benchmark = SubmoduleUsageBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == fixture_id)
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            result = benchmark.score(fixture, fixture.expected, repo_path=repo_path)

            assert result.passed is True, result.error
            assert result.similarity == 1.0
        finally:
            executor.cleanup()

    @pytest.mark.parametrize("fixture_id", [f"f{i:03d}" for i in range(1, 13)])
    def test_noop_answer_fails_fixture_state_checks(self, fixture_id):
        benchmark = SubmoduleUsageBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == fixture_id)
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            result = benchmark.score(fixture, "git status", repo_path=repo_path)

            assert result.passed is False
        finally:
            executor.cleanup()

    def test_sync_fixture_starts_with_stale_local_url(self):
        benchmark = SubmoduleUsageBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == "f009")
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            import subprocess

            result = subprocess.run(
                ["git", "config", "--get", "submodule.lib.url"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            assert result.stdout.strip() == "../wrong-bare"
        finally:
            executor.cleanup()

    def test_list_submodules_accepts_status_form(self):
        benchmark = SubmoduleUsageBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == "f006")

        result = benchmark.score(fixture, "git submodule status")

        assert result.passed is True
        assert result.similarity == 1.0


class TestWorktreeUsageBenchmark:
    """Test the worktree_usage benchmark against its real fixtures."""

    def test_load_fixtures_returns_stateful_worktree_fixtures(self):
        benchmark = WorktreeUsageBenchmark()
        fixtures = benchmark.load_fixtures()

        assert len(fixtures) == 12
        assert {fixture.id for fixture in fixtures} == {f"f{i:03d}" for i in range(1, 13)}
        assert all(
            fixture.scoring["type"] in {"state_assertions", "exact_match", "command_equivalence"}
            for fixture in fixtures
        )

    @pytest.mark.parametrize("fixture_id", [f"f{i:03d}" for i in range(1, 13)])
    def test_expected_answer_passes_fixture_state_checks(self, fixture_id):
        benchmark = WorktreeUsageBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == fixture_id)
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            result = benchmark.score(fixture, fixture.expected, repo_path=repo_path)

            assert result.passed is True, result.error
            assert result.similarity == 1.0
        finally:
            executor.cleanup()

    @pytest.mark.parametrize("fixture_id", [f"f{i:03d}" for i in range(1, 13)])
    def test_noop_answer_fails_fixture_state_checks(self, fixture_id):
        benchmark = WorktreeUsageBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == fixture_id)
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            result = benchmark.score(fixture, "git status", repo_path=repo_path)

            assert result.passed is False
        finally:
            executor.cleanup()

    def test_list_worktrees_accepts_porcelain_form(self):
        benchmark = WorktreeUsageBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == "f004")

        result = benchmark.score(fixture, "git worktree list --porcelain")

        assert result.passed is True
        assert result.similarity == 1.0


class TestTagManagementBenchmark:
    """Test the tag_management benchmark against its real fixtures."""

    def test_load_fixtures_returns_stateful_tag_fixtures(self):
        benchmark = TagManagementBenchmark()
        fixtures = benchmark.load_fixtures()

        assert len(fixtures) == 12
        assert {fixture.id for fixture in fixtures} == {f"f{i:03d}" for i in range(1, 13)}
        assert all(fixture.scoring["type"] in {"state_assertions", "exact_match"} for fixture in fixtures)

    @pytest.mark.parametrize("fixture_id", [f"f{i:03d}" for i in range(1, 13)])
    def test_expected_answer_passes_fixture_state_checks(self, fixture_id):
        benchmark = TagManagementBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == fixture_id)
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            result = benchmark.score(fixture, fixture.expected, repo_path=repo_path)

            assert result.passed is True, result.error
            assert result.similarity == 1.0
        finally:
            executor.cleanup()

    @pytest.mark.parametrize("fixture_id", [f"f{i:03d}" for i in range(1, 13)])
    def test_noop_answer_fails_fixture_state_checks(self, fixture_id):
        benchmark = TagManagementBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == fixture_id)
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            result = benchmark.score(fixture, "git status", repo_path=repo_path)

            assert result.passed is False
        finally:
            executor.cleanup()


class TestGitLogFormatBenchmark:
    """Test the git_log_format benchmark implementation."""


    def test_score_method_works(self):
        """Test that the score method works correctly."""
        from gitbench.harness.types import Score

        benchmark = GitLogFormatBenchmark()
        fixtures = benchmark.load_fixtures()

        # Score with an identical expected value should score high
        fixture = fixtures[0]
        result = benchmark.score(fixture, fixture.expected)

        assert isinstance(result, Score)
        assert result.fixture_id == fixture.id
        assert result.similarity > 0.8  # Should be very similar

    def test_score_method_handles_different_output(self):
        """Test that the score method handles different outputs correctly."""
        from gitbench.harness.types import Score

        benchmark = GitLogFormatBenchmark()
        fixtures = benchmark.load_fixtures()

        fixture = fixtures[0]
        # Score with a completely different message should score low
        result = benchmark.score(fixture, "completely unrelated text that has nothing to do with the expected answer")

        assert isinstance(result, Score)
        assert result.similarity < 0.4  # Should be fairly different


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


class TestGitShowBenchmark:
    """Test the git_show benchmark implementation."""


    def test_score_exact_match_passes(self):
        """Test that an exact match scores as passed."""
        from gitbench.harness.types import Score

        benchmark = GitShowBenchmark()
        fixture = benchmark.load_fixtures()[0]
        result = benchmark.score(fixture, fixture.expected)

        assert isinstance(result, Score)
        assert result.passed is True
        assert result.similarity == 1.0

    def test_score_wrong_answer_fails(self):
        """Test that a wrong answer scores as failed."""
        benchmark = GitShowBenchmark()
        fixture = benchmark.load_fixtures()[0]
        result = benchmark.score(fixture, "definitely-wrong@answer.com")

        assert result.passed is False
        assert result.similarity == 0.0

    def test_full_hash_fixture_scores_dynamic_commit_hash(self):
        benchmark = GitShowBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == "f008")
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            import subprocess

            git_result = subprocess.run(
                ["git", "log", "--format=%H", "--grep", "^Second commit$"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            full_hash = git_result.stdout.strip()

            result = benchmark.score(fixture, full_hash, repo_path=repo_path)
            wrong_result = benchmark.score(fixture, "Second commit", repo_path=repo_path)

            assert fixture.expected != "Second commit"
            assert result.passed is True
            assert result.similarity == 1.0
            assert wrong_result.passed is False
        finally:
            executor.cleanup()


class TestGitCleanBenchmark:
    """Test the git_clean benchmark against its real fixtures."""

    def test_load_fixtures_returns_stateful_git_clean_fixtures(self):
        benchmark = GitCleanBenchmark()
        fixtures = benchmark.load_fixtures()

        assert len(fixtures) == 12
        assert {fixture.id for fixture in fixtures} == {f"f{i:03d}" for i in range(1, 13)}
        assert all(fixture.scoring["type"] in {"state_assertions", "exact_match"} for fixture in fixtures)

    @pytest.mark.parametrize("fixture_id", [f"f{i:03d}" for i in range(1, 13)])
    def test_expected_answer_passes_fixture_state_checks(self, fixture_id):
        benchmark = GitCleanBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == fixture_id)
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            result = benchmark.score(fixture, fixture.expected, repo_path=repo_path)

            assert result.passed is True, result.error
            assert result.similarity == 1.0
        finally:
            executor.cleanup()

    @pytest.mark.parametrize("fixture_id", [f"f{i:03d}" for i in range(1, 13)])
    def test_noop_answer_fails_fixture_state_checks(self, fixture_id):
        benchmark = GitCleanBenchmark()
        fixture = next(f for f in benchmark.load_fixtures() if f.id == fixture_id)
        executor, repo_path = benchmark.setup_fixture(fixture)

        try:
            # Dry-run fixtures assert files SHOULD exist; git clean -f removes them.
            # All other fixtures assert files should NOT exist; git stash keeps them.
            noop_command = "git clean -f" if fixture_id in ("f002", "f010") else "git stash"
            result = benchmark.score(fixture, noop_command, repo_path=repo_path)

            assert result.passed is False
        finally:
            executor.cleanup()
