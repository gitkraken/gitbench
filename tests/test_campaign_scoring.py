"""Scoring tests for repeated-trial campaigns.

Covers mixed outcomes, invalid structured output, operational exclusion,
judge cache reuse, judge config changes, and judge exhaustion.
"""

from unittest.mock import MagicMock

import pytest

from gitbench.harness.campaign import (
    AttemptIdentity,
    AttemptStatus,
    Campaign,
    FixtureReliability,
    JudgeEvidence,
    RawAttempt,
    compute_fixture_aggregates,
    make_campaign,
)
from gitbench.harness.judge import JudgeCache, JudgeClient
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture, Score


def _raw_attempt(
    campaign: Campaign,
    fixture_id: str,
    trial_index: int,
    *,
    passed: bool = False,
    status: AttemptStatus | None = None,
) -> RawAttempt:
    """Build a raw attempt for aggregate tests."""
    if status is None:
        status = AttemptStatus.VALID_PASS if passed else AttemptStatus.VALID_FAIL
    return RawAttempt(
        identity=AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=trial_index,
            model_id="m1",
            reasoning_effort="none",
            output_mode="text",
            fixture_id=fixture_id,
        ),
        status=status,
        passed=passed,
    )


class TestMixedOutcomes:
    """Aggregates over mixed pass/fail outcomes produce correct classifications."""

    def test_three_trial_flaky(self):
        campaign = make_campaign(
            campaign_id="cmp-mixed",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=3,
        )
        campaign.raw_attempts = [
            _raw_attempt(campaign, "f1", 1, passed=True),
            _raw_attempt(campaign, "f1", 2, passed=False),
            _raw_attempt(campaign, "f1", 3, passed=True),
        ]
        agg = compute_fixture_aggregates(campaign)[0]
        assert agg.reliability_classification == FixtureReliability.FLAKY
        assert agg.mean_success_rate == round(2 / 3, 4)
        assert agg.pass_any_at_n[1] is True
        assert agg.pass_any_at_n[3] is True

    def test_all_fail_stable_fail(self):
        campaign = make_campaign(
            campaign_id="cmp-fail",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        campaign.raw_attempts = [
            _raw_attempt(campaign, "f1", 1, passed=False),
            _raw_attempt(campaign, "f1", 2, passed=False),
        ]
        agg = compute_fixture_aggregates(campaign)[0]
        assert agg.reliability_classification == FixtureReliability.STABLE_FAIL
        assert agg.mean_success_rate == 0.0


class TestOperationalExclusion:
    """Operational failures are excluded from quality denominators."""

    def test_infrastructure_failure_excluded(self):
        campaign = make_campaign(
            campaign_id="cmp-excl",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        campaign.raw_attempts = [
            _raw_attempt(
                campaign, "f1", 1, passed=False, status=AttemptStatus.INFRASTRUCTURE_FAILURE
            ),
            _raw_attempt(campaign, "f1", 2, passed=True),
        ]
        agg = compute_fixture_aggregates(campaign)[0]
        assert agg.valid_attempts == 1
        assert agg.excluded_attempts == 1
        assert agg.mean_success_rate == 1.0
        assert agg.incomplete is True


class TestScoreClassification:
    """Runner-level score classification feeds campaign aggregates."""

    def test_score_with_operational_failure(self):
        score = Score(
            fixture_id="f1",
            passed=False,
            similarity=0.0,
            model_output="",
            error="timeout",
            operational_failure=True,
        )
        assert score.operational_failure is True
        assert score.unscored is False

    def test_score_with_unscored(self):
        score = Score(
            fixture_id="f1",
            passed=False,
            similarity=0.0,
            model_output="",
            error="judge exhausted",
            unscored=True,
        )
        assert score.unscored is True


class TestJudgeCacheReuse:
    """Campaign-scoped judge caching reuses decisions for identical evidence."""

    def test_second_identical_call_uses_cache(self):
        mock_client = MagicMock()
        mock_client.generate.return_value = {"text": "0.9"}
        mock_client.model = "judge-model"
        cache = JudgeCache()
        client = JudgeClient([mock_client], cache=cache)

        client.evaluate_commit_message(
            "diff", "message", cache_key=("input-a", "output-a")
        )
        client.evaluate_commit_message(
            "diff", "message", cache_key=("input-a", "output-a")
        )
        assert mock_client.generate.call_count == 1

    def test_scorer_context_uses_judge_cache(self):
        fixture = Fixture(
            id="judge_001",
            description="Judge-enabled fixture",
            setup=["git init"],
            prompt="Generate commit message",
            expected="fix: correct spelling error in file.txt",
            scoring={"type": "llm_judge", "threshold": 0.7},
        )
        mock_client = MagicMock()
        mock_client.generate.return_value = {"text": "0.9"}
        mock_client.model = "judge-model"
        scorer = Scorer(judge_client=JudgeClient([mock_client], cache=JudgeCache()))
        context = {
            "fixture_input_hash": "input-a",
            "target_output_hash": "output-a",
        }

        first = scorer.score(
            fixture,
            "fix: correct spelling error",
            diff="diff",
            campaign_scoring_context=context,
        )
        second = scorer.score(
            fixture,
            "fix: correct spelling error",
            diff="diff",
            campaign_scoring_context=context,
        )

        assert first.similarity == 0.9
        assert second.similarity == 0.9
        assert mock_client.generate.call_count == 1


class TestJudgeConfigChanges:
    """Changing the judge configuration invalidates cached decisions."""

    def test_different_config_hash_misses_cache(self):
        from gitbench.harness.model import MockModelClient

        cache = JudgeCache()
        client_a = JudgeClient([MockModelClient(model="judge-a")], cache=cache)
        # Pre-seed the cache with a score for the first judge configuration.
        cache.set("input", "output", client_a._config_hash, 0.9)

        client_b = JudgeClient([MockModelClient(model="judge-b")], cache=cache)

        # Different config hash means a fresh call even with the same key.
        # MockModelClient.generate returns a MagicMock that is not numeric, so
        # we assert that the second client does not reuse the cached 0.9.
        with pytest.raises(ValueError):
            client_b.evaluate_commit_message(
                "diff", "message", cache_key=("input", "output")
            )


class TestJudgeExhaustion:
    """Exhausted judge failures mark campaign attempts unscored."""

    def test_campaign_scorer_marks_unscored_without_fallback(self):
        fixture = Fixture(
            id="judge_001",
            description="Judge-enabled fixture",
            setup=["git init"],
            prompt="Generate commit message",
            expected="fix: correct spelling error in file.txt",
            scoring={"type": "llm_judge", "threshold": 0.7},
        )
        mock_judge = MagicMock()
        mock_judge.evaluate_commit_message_evidence.return_value = JudgeEvidence(
            final_score=None,
            members=[],
            error="All judge models failed",
            exhausted=True,
        )
        scorer = Scorer(judge_client=mock_judge)

        result = scorer.score(
            fixture,
            "fix: correct spelling error",
            diff="diff",
            campaign_scoring_context={
                "fixture_input_hash": "input-a",
                "target_output_hash": "output-a",
            },
        )
        assert result.unscored is True
        assert "judge_exhausted" in result.error
        assert result.similarity == 0.0
        assert result.passed is False
