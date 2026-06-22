"""Runner-level dispatch and scoring regression tests.

Covers:
1.1  llm_judge characterization — exact scorer inputs, evidence, exhaustion.
1.2  Custom-scored benchmarks (commit_squash, git_bisect, reflog, stash_recovery)
     pass when the model provides the expected answer.
1.3  Stateful benchmarks (git_clean, submodule_usage, tag_management,
     worktree_usage) execute model commands before assertions.
1.4  Parallel worktree lifecycle isolation — no shared benchmark instance.
3.1  Unsupported scoring configuration is classified as infrastructure.
3.2  Setup and scoring-framework failures are infrastructure outcomes.
3.3  Campaign aggregation excludes infrastructure failures.
4.1  Expected-answer and wrong-answer runner tests in text mode.
4.2  False-pass prevention for branch_cleanup, git_clean, submodule_usage,
     tag_management.
4.3  Representative custom and stateful fixtures in JSON-schema mode.
"""

from __future__ import annotations

import re
import subprocess
from typing import Any
from unittest.mock import MagicMock

import pytest

from gitbench.harness.campaign import (
    AttemptIdentity,
    AttemptStatus,
    Campaign,
    make_campaign,
    compute_fixture_aggregates,
)
from gitbench.harness.campaign_executor import raw_attempt_from_score
from gitbench.harness.model import MockModelClient
from gitbench.harness.runner import BenchmarkRunner
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score
from gitbench.harness.judge import JudgeEvidence


# ---------------------------------------------------------------------------
# Helper model clients
# ---------------------------------------------------------------------------


class ScriptedModelClient(MockModelClient):
    """Mock client whose response is computed from the prompt.

    Pass a callable that receives the user-message content and returns the
    model output string.  This lets tests produce dynamic answers (e.g.
    extracting a commit hash from reflog output).
    """

    def __init__(self, responder, *, model: str = "mock"):
        super().__init__(response="", model=model)
        self._responder = responder

    def generate(self, messages, **kwargs):
        prompt_text = messages[-1].content if messages else ""
        self.response = self._responder(prompt_text)
        return super().generate(messages, **kwargs)


def _registry_for(*benchmark_classes) -> dict[str, type]:
    """Build a runner registry from benchmark classes."""
    return {cls.name: cls for cls in benchmark_classes}


def _run_first_fixture(
    runner: BenchmarkRunner,
    benchmark_name: str,
    *,
    model_client: MockModelClient | None = None,
) -> Score:
    """Run the first fixture of *benchmark_name* through the runner."""
    if model_client is not None:
        runner._model_client = model_client
    return runner.run_fixture_identity(benchmark_name, "f001")


# ---------------------------------------------------------------------------
# 1.1  llm_judge characterization
# ---------------------------------------------------------------------------


class TestLlmJudgeCharacterization:
    """Assert exact inputs passed through the judge-aware scorer path."""

    def test_judge_receives_fixture_output_diff_prompt_and_context(self):
        """The scorer receives the fixture, output, diff, prompt, and
        campaign scoring context for llm_judge fixtures."""
        from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark

        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()
        fixture = fixtures[0]  # f001 — llm_judge

        # Spy on the scorer to capture arguments.
        captured: dict[str, Any] = {}
        original_score = Scorer.score

        def spy_score(self_scorer, fx, model_output, **kwargs):
            captured["fixture"] = fx
            captured["model_output"] = model_output
            captured["repo_path"] = kwargs.get("repo_path")
            captured["diff"] = kwargs.get("diff")
            captured["prompt"] = kwargs.get("prompt")
            captured["campaign_scoring_context"] = kwargs.get(
                "campaign_scoring_context"
            )
            return Score(
                fixture_id=fx.id,
                passed=True,
                similarity=0.9,
                model_output=model_output,
            )

        Scorer.score = spy_score
        try:
            runner = BenchmarkRunner(
                {"commit_messages": CommitMessagesBenchmark},
                MockModelClient(response="Add hello.txt greeting message"),
                output_mode="text",
            )
            score = runner.run_fixture_identity("commit_messages", "f001")
        finally:
            Scorer.score = original_score

        assert captured["fixture"].id == fixture.id
        assert captured["model_output"] == "Add hello.txt greeting message"
        assert captured["repo_path"] is not None
        assert captured["diff"] is not None
        assert captured["prompt"] == fixture.prompt
        assert captured["campaign_scoring_context"] is None  # no campaign ctx

    def test_judge_campaign_context_includes_target_output_hash(self):
        """Campaign scoring context is enriched with target_output_hash."""
        from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark

        captured: dict[str, Any] = {}

        def spy_score(self_scorer, fx, model_output, **kwargs):
            captured["ctx"] = kwargs.get("campaign_scoring_context")
            return Score(
                fixture_id=fx.id, passed=True, similarity=0.9, model_output=model_output
            )

        original = Scorer.score
        Scorer.score = spy_score
        try:
            runner = BenchmarkRunner(
                {"commit_messages": CommitMessagesBenchmark},
                MockModelClient(response="good message"),
                output_mode="text",
            )
            runner.run_fixture_identity(
                "commit_messages",
                "f001",
                campaign_scoring_context={"fixture_input_hash": "abc"},
            )
        finally:
            Scorer.score = original

        assert captured["ctx"] is not None
        assert captured["ctx"]["fixture_input_hash"] == "abc"
        assert "target_output_hash" in captured["ctx"]

    def test_judge_exhaustion_classified_unscored(self):
        """When the judge is exhausted with campaign context, the attempt
        is unscored (not a quality failure)."""
        from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark

        mock_judge = MagicMock()
        mock_judge.evaluate_commit_message_evidence.return_value = JudgeEvidence(
            final_score=None,
            members=[],
            error="All judge models failed",
            exhausted=True,
        )
        runner = BenchmarkRunner(
            {"commit_messages": CommitMessagesBenchmark},
            MockModelClient(response="some message"),
            output_mode="text",
        )
        runner._scorer = Scorer(judge_client=mock_judge)

        score = runner.run_fixture_identity(
            "commit_messages",
            "f001",
            campaign_scoring_context={"fixture_input_hash": "abc"},
        )
        assert score.unscored is True
        assert score.passed is False
        assert score.judge_evidence is not None
        assert "judge_exhausted" in (score.error or "")

    def test_judge_evidence_recorded_on_success(self):
        """Judge evidence is attached to the score when the judge succeeds."""
        from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark

        mock_judge = MagicMock()
        mock_judge.evaluate_commit_message_evidence.return_value = JudgeEvidence(
            final_score=0.85,
            members=[],
        )
        runner = BenchmarkRunner(
            {"commit_messages": CommitMessagesBenchmark},
            MockModelClient(response="good message"),
            output_mode="text",
        )
        runner._scorer = Scorer(judge_client=mock_judge)

        score = runner.run_fixture_identity("commit_messages", "f001")
        assert score.passed is True
        assert score.judge_evidence is not None
        assert score.judge_evidence["final_score"] == 0.85


# ---------------------------------------------------------------------------
# 1.2  Custom-scored benchmarks pass through runner
# ---------------------------------------------------------------------------


class TestCustomScoredBenchmarks:
    """commit_squash, git_bisect, reflog, stash_recovery pass with correct
    model output once the runner dispatches to benchmark.score()."""

    def test_commit_squash_passes_with_expected_answer(self):
        from gitbench.benchmarks.commit_squash import CommitSquashBenchmark

        runner = BenchmarkRunner(
            _registry_for(CommitSquashBenchmark),
            MockModelClient(response="WIP: add main.py\nWIP: continue work"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "commit_squash")
        assert score.passed is True, f"Expected pass, got error: {score.error}"

    def test_commit_squash_fails_with_wrong_answer(self):
        from gitbench.benchmarks.commit_squash import CommitSquashBenchmark

        runner = BenchmarkRunner(
            _registry_for(CommitSquashBenchmark),
            MockModelClient(response="Initial commit\nComplete feature"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "commit_squash")
        assert score.passed is False

    def test_git_bisect_passes_with_expected_subject(self):
        from gitbench.benchmarks.git_bisect import GitBisectBenchmark

        runner = BenchmarkRunner(
            _registry_for(GitBisectBenchmark),
            MockModelClient(response="change add operation"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "git_bisect")
        assert score.passed is True, f"Expected pass, got error: {score.error}"

    def test_git_bisect_fails_with_wrong_answer(self):
        from gitbench.benchmarks.git_bisect import GitBisectBenchmark

        runner = BenchmarkRunner(
            _registry_for(GitBisectBenchmark),
            MockModelClient(response="Initial commit"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "git_bisect")
        assert score.passed is False

    def test_reflog_passes_with_correct_hash(self):
        from gitbench.benchmarks.reflog import ReflogBenchmark

        def extract_reflog_hash(prompt: str) -> str:
            """Extract the hash of the commit that was reset away."""
            # The reflog output is after 'Git reflog:'.
            reflog_section = prompt.split("Git reflog:", 1)[-1]
            # Find HEAD@{1} entry (the one that was reset away).
            for line in reflog_section.splitlines():
                line = line.strip()
                if "HEAD@{1}" in line and "reset" not in line.lower():
                    parts = line.split()
                    if parts:
                        return parts[0]
            # Fallback: first hash in reflog that isn't HEAD@{0}
            for line in reflog_section.splitlines():
                line = line.strip()
                m = re.match(r"([0-9a-f]{7,40})\s+HEAD@\{1\}", line)
                if m:
                    return m.group(1)
            return "unknown"

        runner = BenchmarkRunner(
            _registry_for(ReflogBenchmark),
            ScriptedModelClient(extract_reflog_hash),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "reflog")
        assert score.passed is True, f"Expected pass, got error: {score.error}"

    def test_reflog_fails_with_wrong_answer(self):
        from gitbench.benchmarks.reflog import ReflogBenchmark

        runner = BenchmarkRunner(
            _registry_for(ReflogBenchmark),
            MockModelClient(response="0000000000000000000000000000000000000000"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "reflog")
        assert score.passed is False

    def test_stash_recovery_passes_with_correct_ref(self):
        from gitbench.benchmarks.stash_recovery import StashRecoveryBenchmark

        runner = BenchmarkRunner(
            _registry_for(StashRecoveryBenchmark),
            MockModelClient(response="git stash apply stash@{0}"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "stash_recovery")
        assert score.passed is True, f"Expected pass, got error: {score.error}"

    def test_stash_recovery_fails_with_wrong_ref(self):
        from gitbench.benchmarks.stash_recovery import StashRecoveryBenchmark

        runner = BenchmarkRunner(
            _registry_for(StashRecoveryBenchmark),
            MockModelClient(response="git stash apply stash@{5}"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "stash_recovery")
        assert score.passed is False


# ---------------------------------------------------------------------------
# 1.3  Stateful benchmarks execute model commands
# ---------------------------------------------------------------------------


class TestStatefulBenchmarkExecution:
    """git_clean, submodule_usage, tag_management, worktree_usage must
    execute the model's commands before checking state assertions."""

    def test_git_clean_executes_command_then_passes(self):
        from gitbench.benchmarks.git_clean import GitCleanBenchmark

        runner = BenchmarkRunner(
            _registry_for(GitCleanBenchmark),
            MockModelClient(response="git clean -f"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "git_clean")
        assert score.passed is True, f"Expected pass, got error: {score.error}"

    def test_git_clean_wrong_command_fails(self):
        from gitbench.benchmarks.git_clean import GitCleanBenchmark

        runner = BenchmarkRunner(
            _registry_for(GitCleanBenchmark),
            MockModelClient(response="git status"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "git_clean")
        assert score.passed is False

    def test_tag_management_executes_command_then_passes(self):
        from gitbench.benchmarks.tag_management import TagManagementBenchmark

        runner = BenchmarkRunner(
            _registry_for(TagManagementBenchmark),
            MockModelClient(response="git tag v1.0"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "tag_management")
        assert score.passed is True, f"Expected pass, got error: {score.error}"

    def test_tag_management_wrong_command_fails(self):
        from gitbench.benchmarks.tag_management import TagManagementBenchmark

        runner = BenchmarkRunner(
            _registry_for(TagManagementBenchmark),
            MockModelClient(response="git status"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "tag_management")
        assert score.passed is False

    def test_submodule_usage_executes_command_then_passes(self):
        from gitbench.benchmarks.submodule_usage import SubmoduleUsageBenchmark

        runner = BenchmarkRunner(
            _registry_for(SubmoduleUsageBenchmark),
            MockModelClient(
                response="git submodule add ../lib-bare lib"
            ),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "submodule_usage")
        assert score.passed is True, f"Expected pass, got error: {score.error}"

    def test_submodule_usage_wrong_command_fails(self):
        from gitbench.benchmarks.submodule_usage import SubmoduleUsageBenchmark

        runner = BenchmarkRunner(
            _registry_for(SubmoduleUsageBenchmark),
            MockModelClient(response="git status"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "submodule_usage")
        assert score.passed is False

    def test_worktree_usage_executes_command_then_passes(self):
        from gitbench.benchmarks.worktree_usage import WorktreeUsageBenchmark

        runner = BenchmarkRunner(
            _registry_for(WorktreeUsageBenchmark),
            MockModelClient(response="git worktree add ../feature-wt feature"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "worktree_usage")
        assert score.passed is True, f"Expected pass, got error: {score.error}"

    def test_worktree_usage_wrong_command_fails(self):
        from gitbench.benchmarks.worktree_usage import WorktreeUsageBenchmark

        runner = BenchmarkRunner(
            _registry_for(WorktreeUsageBenchmark),
            MockModelClient(response="git status"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "worktree_usage")
        assert score.passed is False


# ---------------------------------------------------------------------------
# 1.4  Parallel worktree lifecycle isolation
# ---------------------------------------------------------------------------


class TestParallelWorktreeIsolation:
    """Parallel fixtures must use isolated benchmark instances."""

    def test_parallel_worktree_no_instance_sharing(self):
        """Two worktree_usage fixtures run in parallel must not share a
        benchmark instance or executor reference."""
        from gitbench.benchmarks.worktree_usage import WorktreeUsageBenchmark

        # Collect instance ids created during parallel execution.
        created_instances: list[int] = []

        original_init = WorktreeUsageBenchmark.__init__

        def tracking_init(self, fixtures_root=None):
            original_init(self, fixtures_root=fixtures_root)
            created_instances.append(id(self))

        WorktreeUsageBenchmark.__init__ = tracking_init
        try:
            runner = BenchmarkRunner(
                _registry_for(WorktreeUsageBenchmark),
                MockModelClient(response="git worktree add ../feature-wt feature"),
                output_mode="text",
            )
            # Run with 2 workers — should create at least 2 instances
            # (one per parallel fixture).
            result = runner.run_benchmark(
                "worktree_usage", fixture_workers=2,
            )
        finally:
            WorktreeUsageBenchmark.__init__ = original_init

        # With parallel execution, each fixture should get a fresh instance.
        # The runner creates one instance for load_fixtures, then one per
        # parallel fixture. So we expect at least 3 (1 + 2+).
        assert len(created_instances) >= 3, (
            f"Expected at least 3 instances (1 for load + 2 for parallel "
            f"fixtures), got {len(created_instances)}: {created_instances}"
        )

    def test_parallel_worktree_results_correct(self):
        """Parallel worktree fixtures produce correct pass/fail results."""
        from gitbench.benchmarks.worktree_usage import WorktreeUsageBenchmark

        runner = BenchmarkRunner(
            _registry_for(WorktreeUsageBenchmark),
            MockModelClient(response="git worktree add ../feature-wt feature"),
            output_mode="text",
        )
        result = runner.run_benchmark(
            "worktree_usage", fixture_workers=2,
        )
        # All fixtures should pass with the correct command.
        assert result.total > 0
        # At least the first fixture should pass.
        assert any(s.passed for s in result.scores), (
            f"No fixtures passed: {[(s.fixture_id, s.passed, s.error) for s in result.scores]}"
        )


# ---------------------------------------------------------------------------
# Spec scenario: Non-judge benchmark with judge configuration
# ---------------------------------------------------------------------------


class TestJudgeNotCalledForNonJudgeFixtures:
    """When a judge is configured, non-judge fixtures SHALL NOT invoke it."""

    def test_judge_not_called_for_non_judge_fixture(self):
        """A commit_squash fixture (commit_selection scoring) evaluated with
        a configured judge must not invoke the judge at all."""
        from gitbench.benchmarks.commit_squash import CommitSquashBenchmark

        mock_judge = MagicMock()
        mock_judge.evaluate_commit_message_evidence.return_value = JudgeEvidence(
            final_score=0.99, members=[]
        )

        runner = BenchmarkRunner(
            _registry_for(CommitSquashBenchmark),
            MockModelClient(response="WIP: add main.py\nWIP: continue work"),
            output_mode="text",
        )
        # Install a judge-aware scorer on the runner.
        runner._scorer = Scorer(judge_client=mock_judge)
        # Also install a judge on the benchmark's own scorer to detect any
        # indirect invocation.
        benchmark = CommitSquashBenchmark()
        benchmark._scorer = Scorer(judge_client=mock_judge)

        _, score = runner._run_fixture(
            benchmark,
            benchmark.load_fixtures()[0],
        )

        assert score.passed is True
        mock_judge.evaluate_commit_message_evidence.assert_not_called()

    def test_judge_not_called_for_stateful_fixture(self):
        """A git_clean fixture (state_assertions scoring) evaluated with
        a configured judge must not invoke the judge."""
        from gitbench.benchmarks.git_clean import GitCleanBenchmark

        mock_judge = MagicMock()
        mock_judge.evaluate_commit_message_evidence.return_value = JudgeEvidence(
            final_score=0.99, members=[]
        )

        runner = BenchmarkRunner(
            _registry_for(GitCleanBenchmark),
            MockModelClient(response="git clean -f"),
            output_mode="text",
        )
        runner._scorer = Scorer(judge_client=mock_judge)
        benchmark = GitCleanBenchmark()
        benchmark._scorer = Scorer(judge_client=mock_judge)

        _, score = runner._run_fixture(
            benchmark,
            benchmark.load_fixtures()[0],
        )

        assert score.passed is True
        mock_judge.evaluate_commit_message_evidence.assert_not_called()


# ---------------------------------------------------------------------------
# Spec scenario: Deterministic worktree fixture setup
# ---------------------------------------------------------------------------


class TestWorktreeSetupWithContext:
    """WorktreeUsageBenchmark.setup_fixture accepts fixture_generation_context."""

    def test_setup_with_fixture_generation_context(self):
        """setup_fixture accepts a FixtureGenerationContext without a
        signature error and uses it for Git identity."""
        import os
        from gitbench.benchmarks.worktree_usage import WorktreeUsageBenchmark
        from gitbench.utils.git import FixtureGenerationContext

        ctx = FixtureGenerationContext(
            version="test-v1",
            seed=42,
            author_name="Deterministic Author",
            author_email="det@example.com",
        )
        benchmark = WorktreeUsageBenchmark()
        fixture = benchmark.load_fixtures()[0]

        executor, repo_path = benchmark.setup_fixture(
            fixture,
            fixture_generation_context=ctx,
        )

        try:
            assert os.path.isdir(repo_path)

            # Verify that Git identities use the context.
            result = subprocess.run(
                ["git", "log", "--format=%an <%ae>"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            assert "Deterministic Author" in result.stdout
            assert "det@example.com" in result.stdout
        finally:
            executor.cleanup()

    def test_run_fixture_identity_with_generation_context(self):
        """run_fixture_identity passes fixture_generation_context through to
        setup_fixture for worktree_usage."""
        from gitbench.benchmarks.worktree_usage import WorktreeUsageBenchmark
        from gitbench.utils.git import FixtureGenerationContext

        ctx = FixtureGenerationContext(
            version="test-v1",
            seed=99,
            author_name="Campaign Author",
            author_email="campaign@example.com",
        )
        runner = BenchmarkRunner(
            _registry_for(WorktreeUsageBenchmark),
            MockModelClient(response="git worktree add ../feature-wt feature"),
            output_mode="text",
        )
        # This should not raise a TypeError from the setup_fixture signature.
        score = runner.run_fixture_identity(
            "worktree_usage",
            "f001",
            fixture_generation_context=ctx,
        )
        assert score.passed is True, f"Expected pass, got: {score.error}"


# ---------------------------------------------------------------------------
# 3.1 / 3.2  Infrastructure failure classification
# ---------------------------------------------------------------------------


class TestInfrastructureFailureClassification:
    """Setup, scoring-framework, and unsupported-scoring failures are
    classified as infrastructure (operational_failure), not quality."""

    def test_unsupported_scoring_type_is_infrastructure(self):
        """An unsupported scoring type produces an operational failure."""
        from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark

        # Build a fixture with an unsupported scoring type.
        fixture = Fixture(
            id="bad_001",
            description="Unsupported scoring",
            setup=["git init"],
            prompt="Do something",
            expected="result",
            scoring={"type": "nonexistent_scoring_type"},
        )

        benchmark = CommitMessagesBenchmark()
        # Monkey-patch load_fixtures to return our fixture.
        benchmark.load_fixtures = lambda: [fixture]

        runner = BenchmarkRunner(
            {"commit_messages": CommitMessagesBenchmark},
            MockModelClient(response="result"),
            output_mode="text",
        )
        _, score = runner._run_fixture(benchmark, fixture)

        assert score.passed is False
        assert score.operational_failure is True, (
            f"Expected operational_failure for unsupported scoring type, "
            f"got error: {score.error}"
        )

    def test_setup_failure_is_infrastructure(self):
        """A setup failure (bad fixture setup) is classified as infrastructure."""
        from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark

        fixture = Fixture(
            id="setup_fail",
            description="Setup fails",
            setup=["git init", "git checkout nonexistent_branch"],  # will fail
            prompt="Do something",
            expected="result",
            scoring={"type": "similarity", "threshold": 0.5},
        )

        benchmark = CommitMessagesBenchmark()
        runner = BenchmarkRunner(
            {"commit_messages": CommitMessagesBenchmark},
            MockModelClient(response="result"),
            output_mode="text",
        )
        _, score = runner._run_fixture(benchmark, fixture)

        assert score.passed is False
        assert score.operational_failure is True, (
            f"Expected operational_failure for setup failure, "
            f"got error: {score.error}"
        )

    def test_structured_output_error_remains_quality_failure(self):
        """Structured-output validation failure is NOT operational."""
        from gitbench.benchmarks.commit_messages import CommitMessagesBenchmark
        from gitbench.structured_output import contract_for_benchmark_fixture

        benchmark = CommitMessagesBenchmark()
        fixtures = benchmark.load_fixtures()
        fixture = None
        for f in fixtures:
            if contract_for_benchmark_fixture(f, "commit_messages") is not None:
                fixture = f
                break
        if fixture is None:
            pytest.skip("No structured-output fixture available")

        client = MockModelClient(model="mock")
        client.generate = lambda messages, **kwargs: {
            "text": "not valid json",
            "parsed_payload": None,
            "raw_structured_output": "not valid json",
            "structured_error": "invalid json",
        }

        runner = BenchmarkRunner(
            {"commit_messages": CommitMessagesBenchmark},
            client,
            output_mode="json_schema",
        )
        _, score = runner._run_fixture(benchmark, fixture)

        assert score.passed is False
        assert score.operational_failure is False


# ---------------------------------------------------------------------------
# 3.3  Campaign aggregation excludes infrastructure failures
# ---------------------------------------------------------------------------


class TestCampaignInfrastructureExclusion:
    """Infrastructure failures are excluded from quality denominators and
    make campaigns incomplete."""

    def test_infrastructure_attempt_excluded_from_aggregates(self):
        """A campaign with one infra failure and one pass is incomplete."""
        campaign = make_campaign(
            campaign_id="cmp-infra",
            fixture_ids=["commit_messages/f001"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )

        # Trial 1: infrastructure failure.
        score_infra = Score(
            fixture_id="f001",
            passed=False,
            similarity=0.0,
            model_output="",
            error="setup failed",
            operational_failure=True,
        )
        identity1 = AttemptIdentity(
            campaign_id="cmp-infra",
            trial_index=1,
            model_id="m1",
            reasoning_effort="none",
            output_mode="text",
            fixture_id="commit_messages/f001",
            benchmark="commit_messages",
        )
        attempt1 = raw_attempt_from_score(campaign, identity1, score_infra)

        # Trial 2: valid pass.
        score_pass = Score(
            fixture_id="f001",
            passed=True,
            similarity=1.0,
            model_output="good",
        )
        identity2 = AttemptIdentity(
            campaign_id="cmp-infra",
            trial_index=2,
            model_id="m1",
            reasoning_effort="none",
            output_mode="text",
            fixture_id="commit_messages/f001",
            benchmark="commit_messages",
        )
        attempt2 = raw_attempt_from_score(campaign, identity2, score_pass)

        campaign.raw_attempts = [attempt1, attempt2]
        aggregates = compute_fixture_aggregates(campaign)

        assert len(aggregates) == 1
        agg = aggregates[0]
        assert agg.valid_attempts == 1
        assert agg.excluded_attempts == 1
        assert agg.mean_success_rate == 1.0
        assert agg.incomplete is True

    def test_all_infrastructure_makes_campaign_incomplete(self):
        """All-infrastructure campaign is incomplete with no quality attempts."""
        campaign = make_campaign(
            campaign_id="cmp-all-infra",
            fixture_ids=["commit_messages/f001"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )

        for trial_index in [1, 2]:
            score = Score(
                fixture_id="f001",
                passed=False,
                similarity=0.0,
                model_output="",
                error="scoring error",
                operational_failure=True,
            )
            identity = AttemptIdentity(
                campaign_id="cmp-all-infra",
                trial_index=trial_index,
                model_id="m1",
                reasoning_effort="none",
                output_mode="text",
                fixture_id="commit_messages/f001",
                benchmark="commit_messages",
            )
            campaign.raw_attempts.append(
                raw_attempt_from_score(campaign, identity, score)
            )

        aggregates = compute_fixture_aggregates(campaign)
        assert len(aggregates) == 1
        agg = aggregates[0]
        assert agg.valid_attempts == 0
        assert agg.excluded_attempts == 2
        assert agg.mean_success_rate is None
        assert agg.incomplete is True


# ---------------------------------------------------------------------------
# 4.1  Expected-answer and wrong-answer tests in text mode
#    (for the five reported benchmarks)
# ---------------------------------------------------------------------------


class TestExpectedAndWrongAnswers:
    """Expected answers pass and wrong answers fail for the five reported
    benchmarks in text mode."""

    @pytest.mark.parametrize("benchmark_name,response,should_pass", [
        ("commit_squash", "WIP: add main.py\nWIP: continue work", True),
        ("commit_squash", "Initial commit", False),
        ("git_bisect", "change add operation", True),
        ("git_bisect", "Initial commit", False),
        ("stash_recovery", "git stash apply stash@{0}", True),
        ("stash_recovery", "git stash apply stash@{5}", False),
        ("git_clean", "git clean -f", True),
        ("git_clean", "git status", False),
        ("worktree_usage", "git worktree add ../feature-wt feature", True),
        ("worktree_usage", "git status", False),
    ])
    def test_expected_and_wrong_answers(self, benchmark_name, response, should_pass):
        from gitbench.cli import discover_benchmarks

        registry = discover_benchmarks()
        runner = BenchmarkRunner(
            {benchmark_name: registry[benchmark_name]},
            MockModelClient(response=response),
            output_mode="text",
        )
        score = runner.run_fixture_identity(benchmark_name, "f001")
        assert score.passed == should_pass, (
            f"{benchmark_name}: expected pass={should_pass}, "
            f"got pass={score.passed}, error={score.error}"
        )


# ---------------------------------------------------------------------------
# 4.2  False-pass prevention for branch_cleanup, git_clean,
#      submodule_usage, tag_management
# ---------------------------------------------------------------------------


class TestFalsePassPrevention:
    """Wrong answers must not false-pass due to initial repository state."""

    def test_branch_cleanup_wrong_answer_fails(self):
        from gitbench.benchmarks.branch_cleanup import BranchCleanupBenchmark

        runner = BenchmarkRunner(
            _registry_for(BranchCleanupBenchmark),
            MockModelClient(response="feature-login"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "branch_cleanup")
        # feature-login is NOT merged, so it's a wrong answer.
        assert score.passed is False, (
            f"Wrong answer 'feature-login' should fail, got pass={score.passed}"
        )

    def test_branch_cleanup_correct_answer_passes(self):
        from gitbench.benchmarks.branch_cleanup import BranchCleanupBenchmark

        runner = BenchmarkRunner(
            _registry_for(BranchCleanupBenchmark),
            MockModelClient(response="fix-typo"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "branch_cleanup")
        assert score.passed is True, f"Expected pass, got: {score.error}"

    def test_git_clean_noop_fails(self):
        from gitbench.benchmarks.git_clean import GitCleanBenchmark

        runner = BenchmarkRunner(
            _registry_for(GitCleanBenchmark),
            MockModelClient(response="echo noop"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "git_clean")
        assert score.passed is False

    def test_tag_management_noop_fails(self):
        from gitbench.benchmarks.tag_management import TagManagementBenchmark

        runner = BenchmarkRunner(
            _registry_for(TagManagementBenchmark),
            MockModelClient(response="echo noop"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "tag_management")
        assert score.passed is False

    def test_submodule_usage_noop_fails(self):
        from gitbench.benchmarks.submodule_usage import SubmoduleUsageBenchmark

        runner = BenchmarkRunner(
            _registry_for(SubmoduleUsageBenchmark),
            MockModelClient(response="echo noop"),
            output_mode="text",
        )
        score = _run_first_fixture(runner, "submodule_usage")
        assert score.passed is False


# ---------------------------------------------------------------------------
# 4.3  JSON-schema mode verification
# ---------------------------------------------------------------------------


class TestJsonSchemaMode:
    """Representative custom and stateful fixtures in JSON-schema mode."""

    def test_commit_squash_json_schema_mode(self):
        """commit_squash fixture works in JSON-schema mode after
        canonicalization (or falls back gracefully)."""
        from gitbench.benchmarks.commit_squash import CommitSquashBenchmark
        from gitbench.structured_output import contract_for_benchmark_fixture

        benchmark = CommitSquashBenchmark()
        fixture = benchmark.load_fixtures()[0]
        contract = contract_for_benchmark_fixture(fixture, "commit_squash")
        if contract is None:
            pytest.skip("No JSON-schema contract for commit_squash f001")

        runner = BenchmarkRunner(
            _registry_for(CommitSquashBenchmark),
            MockModelClient(response="WIP: add main.py\nWIP: continue work"),
            output_mode="json_schema",
        )
        score = _run_first_fixture(runner, "commit_squash")
        # Should not error with an infrastructure failure.
        assert not score.operational_failure, f"Infrastructure failure: {score.error}"

    def test_git_clean_json_schema_mode(self):
        """git_clean fixture works in JSON-schema mode."""
        from gitbench.benchmarks.git_clean import GitCleanBenchmark
        from gitbench.structured_output import contract_for_benchmark_fixture

        benchmark = GitCleanBenchmark()
        fixture = benchmark.load_fixtures()[0]
        contract = contract_for_benchmark_fixture(fixture, "git_clean")
        if contract is None:
            pytest.skip("No JSON-schema contract for git_clean f001")

        runner = BenchmarkRunner(
            _registry_for(GitCleanBenchmark),
            MockModelClient(response="git clean -f"),
            output_mode="json_schema",
        )
        score = _run_first_fixture(runner, "git_clean")
        assert not score.operational_failure, f"Infrastructure failure: {score.error}"