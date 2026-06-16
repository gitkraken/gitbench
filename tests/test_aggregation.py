"""Tests for campaign aggregation functions."""

from gitbench.harness.aggregation import (
    compute_benchmark_aggregates,
    compute_campaign_resource_summary,
    compute_model_aggregates,
    compute_trial_aggregates,
    refresh_campaign_aggregates,
)
from gitbench.harness.campaign import (
    AttemptIdentity,
    AttemptStatus,
    CampaignState,
    FixtureExpectedHashes,
    Provenance,
    RawAttempt,
    Trial,
    make_campaign,
)


def _attempt(
    campaign,
    fixture_id: str,
    trial_index: int,
    model_id: str = "m1",
    *,
    reasoning_effort: str = "none",
    output_mode: str = "text",
    benchmark: str = "",
    passed: bool = False,
    status: AttemptStatus | None = None,
    cost_usd: float | None = None,
    input_tokens: int | None = None,
    api_duration_ms: float | None = None,
) -> RawAttempt:
    if status is None:
        status = AttemptStatus.VALID_PASS if passed else AttemptStatus.VALID_FAIL
    return RawAttempt(
        identity=AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=trial_index,
            model_id=model_id,
            reasoning_effort=reasoning_effort,
            output_mode=output_mode,
            fixture_id=fixture_id,
            benchmark=benchmark,
        ),
        status=status,
        passed=passed,
        cost_usd=cost_usd,
        input_tokens=input_tokens,
        api_duration_ms=api_duration_ms,
    )


class TestTrialAggregation:
    """Per-trial aggregates count valid and excluded attempts."""

    def test_complete_trial(self):
        campaign = make_campaign(
            campaign_id="cmp-trial",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        id1 = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="none",
            output_mode="text",
            fixture_id="f1",
        )
        id2 = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=2,
            model_id="m1",
            reasoning_effort="none",
            output_mode="text",
            fixture_id="f1",
        )
        campaign.trials = [
            Trial(trial_index=1, planned_attempts=1, attempt_identities=[id1]),
            Trial(trial_index=2, planned_attempts=1, attempt_identities=[id2]),
        ]
        campaign.raw_attempts = [
            _attempt(campaign, "f1", 1, passed=True),
            _attempt(campaign, "f1", 2, passed=True),
        ]
        trials = compute_trial_aggregates(campaign)
        assert len(trials) == 2
        assert all(t.complete for t in trials)

    def test_excluded_attempt_makes_trial_incomplete(self):
        campaign = make_campaign(
            campaign_id="cmp-trial-excl",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        id1 = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="none",
            output_mode="text",
            fixture_id="f1",
        )
        campaign.trials = [Trial(trial_index=1, planned_attempts=1, attempt_identities=[id1])]
        campaign.raw_attempts = [
            _attempt(
                campaign, "f1", 1, passed=False, status=AttemptStatus.INFRASTRUCTURE_FAILURE
            ),
        ]
        trials = compute_trial_aggregates(campaign)
        assert not trials[0].complete
        assert trials[0].excluded_attempts == 1


class TestModelAggregation:
    """Per-model summaries aggregate valid attempts and resource usage."""

    def test_model_summary(self):
        campaign = make_campaign(
            campaign_id="cmp-model",
            fixture_ids=["f1", "f2"],
            model_ids=["m1", "m2"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        campaign.raw_attempts = [
            _attempt(campaign, "f1", 1, "m1", passed=True, cost_usd=0.1),
            _attempt(campaign, "f2", 1, "m1", passed=False, cost_usd=0.1),
            _attempt(campaign, "f1", 1, "m2", passed=True, cost_usd=0.2),
        ]
        summaries = compute_model_aggregates(campaign)
        by_model = {s.model_id: s for s in summaries}
        assert by_model["m1"].mean_success_rate == 0.5
        assert by_model["m1"].resource_summary.total_cost_usd == 0.2
        assert by_model["m2"].mean_success_rate == 1.0

    def test_same_model_effort_and_mode_dimensions_stay_separate(self):
        campaign = make_campaign(
            campaign_id="cmp-dims",
            benchmark_ids=["reflog"],
            fixture_ids=["reflog/f1"],
            model_ids=["m1"],
            reasoning_efforts=["low", "high"],
            output_modes=["text", "json_schema"],
            planned_trial_count=1,
        )
        campaign.raw_attempts = [
            _attempt(
                campaign,
                "f1",
                1,
                "m1",
                reasoning_effort="low",
                output_mode="text",
                benchmark="reflog",
                passed=True,
            ),
            _attempt(
                campaign,
                "f1",
                1,
                "m1",
                reasoning_effort="high",
                output_mode="text",
                benchmark="reflog",
                passed=False,
            ),
            _attempt(
                campaign,
                "f1",
                1,
                "m1",
                reasoning_effort="low",
                output_mode="json_schema",
                benchmark="reflog",
                passed=False,
            ),
        ]

        fixture_summaries = {
            (s.reasoning_effort, s.output_mode): s
            for s in refresh_campaign_aggregates(campaign).fixture_aggregates
        }
        model_summaries = {
            (s.reasoning_effort, s.output_mode): s
            for s in compute_model_aggregates(campaign)
        }

        assert fixture_summaries[("low", "text")].mean_success_rate == 1.0
        assert fixture_summaries[("high", "text")].mean_success_rate == 0.0
        assert fixture_summaries[("low", "json_schema")].mean_success_rate == 0.0
        assert model_summaries[("low", "text")].mean_success_rate == 1.0
        assert model_summaries[("high", "text")].mean_success_rate == 0.0


class TestBenchmarkAggregation:
    """Per-benchmark summaries group attempts by fixture prefix."""

    def test_benchmark_summary(self):
        campaign = make_campaign(
            campaign_id="cmp-bench",
            benchmark_ids=["reflog"],
            fixture_ids=["reflog/f1", "reflog/f2"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.raw_attempts = [
            _attempt(campaign, "reflog/f1", 1, passed=True),
            _attempt(campaign, "reflog/f2", 1, passed=False),
        ]
        summaries = compute_benchmark_aggregates(campaign)
        assert len(summaries) == 1
        assert summaries[0].mean_success_rate == 0.5


class TestCampaignResourceSummary:
    """Campaign-level resource totals include all attempts."""

    def test_resource_summary_totals(self):
        campaign = make_campaign(
            campaign_id="cmp-res",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        campaign.raw_attempts = [
            _attempt(campaign, "f1", 1, passed=True, cost_usd=0.1, input_tokens=10),
            _attempt(campaign, "f1", 2, passed=True, cost_usd=0.2, input_tokens=20),
        ]
        summary = compute_campaign_resource_summary(campaign)
        assert summary.total_cost_usd == 0.3
        assert summary.total_input_tokens == 30


class TestRefreshCampaignAggregates:
    """Refreshing a campaign updates all aggregates and state."""

    def test_refresh_completes_campaign(self):
        campaign = make_campaign(
            campaign_id="cmp-refresh",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        campaign.trials = [
            Trial(
                trial_index=1,
                planned_attempts=1,
                attempt_identities=[
                    AttemptIdentity(
                        campaign_id=campaign.campaign_id,
                        trial_index=1,
                        model_id="m1",
                        reasoning_effort="none",
                        output_mode="text",
                        fixture_id="f1",
                    )
                ],
            ),
            Trial(
                trial_index=2,
                planned_attempts=1,
                attempt_identities=[
                    AttemptIdentity(
                        campaign_id=campaign.campaign_id,
                        trial_index=2,
                        model_id="m1",
                        reasoning_effort="none",
                        output_mode="text",
                        fixture_id="f1",
                    )
                ],
            ),
        ]
        campaign.raw_attempts = [
            _attempt(campaign, "f1", 1, passed=True),
            _attempt(campaign, "f1", 2, passed=True),
        ]
        refresh_campaign_aggregates(campaign)
        assert campaign.state == CampaignState.COMPLETE
        assert campaign.completed_attempts == 2
        assert campaign.excluded_attempts == 0

    def test_refresh_incomplete_with_missing_attempt(self):
        campaign = make_campaign(
            campaign_id="cmp-refresh-inc",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        campaign.trials = [
            Trial(
                trial_index=1,
                planned_attempts=1,
                attempt_identities=[
                    AttemptIdentity(
                        campaign_id=campaign.campaign_id,
                        trial_index=1,
                        model_id="m1",
                        reasoning_effort="none",
                        output_mode="text",
                        fixture_id="f1",
                    )
                ],
            ),
            Trial(
                trial_index=2,
                planned_attempts=1,
                attempt_identities=[
                    AttemptIdentity(
                        campaign_id=campaign.campaign_id,
                        trial_index=2,
                        model_id="m1",
                        reasoning_effort="none",
                        output_mode="text",
                        fixture_id="f1",
                    )
                ],
            ),
        ]
        campaign.raw_attempts = [_attempt(campaign, "f1", 1, passed=True)]
        refresh_campaign_aggregates(campaign)
        assert campaign.state == CampaignState.INCOMPLETE



class TestRankingEligibility:
    """Default rankings use only complete, balanced campaigns."""

    def test_complete_campaign_is_eligible(self):
        from gitbench.harness.aggregation import is_ranking_eligible
        campaign = make_campaign(
            campaign_id="cmp-elig",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.planned_attempts = 1
        campaign.completed_attempts = 1
        campaign.excluded_attempts = 0
        assert is_ranking_eligible(campaign) is True

    def test_incomplete_campaign_is_not_eligible(self):
        from gitbench.harness.aggregation import is_ranking_eligible
        campaign = make_campaign(
            campaign_id="cmp-inelig",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        campaign.planned_attempts = 2
        campaign.completed_attempts = 1
        campaign.excluded_attempts = 0
        assert is_ranking_eligible(campaign) is False

    def test_excluded_attempts_make_ineligible(self):
        from gitbench.harness.aggregation import is_ranking_eligible
        campaign = make_campaign(
            campaign_id="cmp-excl",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.planned_attempts = 1
        campaign.completed_attempts = 1
        campaign.excluded_attempts = 1
        assert is_ranking_eligible(campaign) is False

    def test_legacy_campaign_is_not_eligible(self):
        from gitbench.harness.aggregation import is_ranking_eligible
        campaign = make_campaign(
            campaign_id="cmp-legacy",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.planned_attempts = 1
        campaign.completed_attempts = 1
        campaign.excluded_attempts = 0
        campaign.legacy = True
        assert is_ranking_eligible(campaign) is False


class TestMeanPerCompleteTrial:
    """Mean resource usage per complete trial."""

    def test_mean_per_complete_trial(self):
        campaign = make_campaign(
            campaign_id="cmp-mean",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        campaign.trials = [
            Trial(
                trial_index=1,
                planned_attempts=1,
                attempt_identities=[
                    AttemptIdentity(
                        campaign_id=campaign.campaign_id,
                        trial_index=1,
                        model_id="m1",
                        reasoning_effort="none",
                        output_mode="text",
                        fixture_id="f1",
                    )
                ],
                complete=True,
            ),
            Trial(
                trial_index=2,
                planned_attempts=1,
                attempt_identities=[
                    AttemptIdentity(
                        campaign_id=campaign.campaign_id,
                        trial_index=2,
                        model_id="m1",
                        reasoning_effort="none",
                        output_mode="text",
                        fixture_id="f1",
                    )
                ],
                complete=True,
            ),
        ]
        campaign.raw_attempts = [
            _attempt(campaign, "f1", 1, passed=True, cost_usd=0.1, input_tokens=10, api_duration_ms=100.0),
            _attempt(campaign, "f1", 2, passed=True, cost_usd=0.3, input_tokens=30, api_duration_ms=300.0),
        ]
        for attempt, tokens in zip(campaign.raw_attempts, [10, 30]):
            attempt.total_tokens = tokens
        summary = compute_campaign_resource_summary(campaign)
        assert summary.total_cost_usd == 0.4
        assert summary.mean_cost_per_complete_trial_usd == 0.2
        assert summary.total_input_tokens == 40
        assert summary.mean_tokens_per_complete_trial == 20.0
        assert summary.mean_api_duration_per_complete_trial_ms == 200.0


class TestFailedCallRetention:
    """Resource consumption from failed calls is retained in totals."""

    def test_failed_call_costs_are_retained(self):
        campaign = make_campaign(
            campaign_id="cmp-failed",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.trials = [
            Trial(
                trial_index=1,
                planned_attempts=1,
                attempt_identities=[
                    AttemptIdentity(
                        campaign_id=campaign.campaign_id,
                        trial_index=1,
                        model_id="m1",
                        reasoning_effort="none",
                        output_mode="text",
                        fixture_id="f1",
                    )
                ],
            ),
        ]
        campaign.raw_attempts = [
            _attempt(
                campaign, "f1", 1, passed=False,
                status=AttemptStatus.INFRASTRUCTURE_FAILURE,
                cost_usd=0.05,
            ),
        ]
        summary = compute_campaign_resource_summary(campaign)
        assert summary.total_cost_usd == 0.05


class TestWallClockDuration:
    """Wall-clock duration is separate from summed API time."""

    def test_wall_clock_duration_recorded(self):
        from gitbench.harness.campaign import _now_iso

        campaign = make_campaign(
            campaign_id="cmp-wall",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.created_at = _now_iso()
        campaign.updated_at = _now_iso()
        campaign.trials = [
            Trial(
                trial_index=1,
                planned_attempts=1,
                attempt_identities=[
                    AttemptIdentity(
                        campaign_id=campaign.campaign_id,
                        trial_index=1,
                        model_id="m1",
                        reasoning_effort="none",
                        output_mode="text",
                        fixture_id="f1",
                    )
                ],
            ),
        ]
        campaign.raw_attempts = [
            _attempt(campaign, "f1", 1, passed=True, api_duration_ms=50.0),
        ]
        summary = compute_campaign_resource_summary(campaign)
        assert summary.total_api_duration_ms == 50.0
        assert summary.total_wall_duration_ms is not None



class TestCostReconciliation:
    """Total cost reconciles target, judge, and safety costs."""

    def test_target_and_judge_costs_reconciled(self):
        from gitbench.harness.campaign import JudgeEvidence, JudgeMemberResult
        campaign = make_campaign(
            campaign_id="cmp-cost",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.trials = [
            Trial(
                trial_index=1,
                planned_attempts=1,
                attempt_identities=[
                    AttemptIdentity(
                        campaign_id=campaign.campaign_id,
                        trial_index=1,
                        model_id="m1",
                        reasoning_effort="none",
                        output_mode="text",
                        fixture_id="f1",
                    )
                ],
            ),
        ]
        attempt = _attempt(campaign, "f1", 1, passed=True, cost_usd=0.1)
        attempt.judge_evidence = JudgeEvidence(
            members=[
                JudgeMemberResult(member_id="j1", model_id="judge", cost_usd=0.05),
            ],
        )
        attempt.safety_cost_usd = 0.02
        campaign.raw_attempts = [attempt]
        summary = compute_campaign_resource_summary(campaign)
        assert summary.total_cost_usd == 0.17

    def test_partial_pricing_when_cost_missing(self):
        campaign = make_campaign(
            campaign_id="cmp-partial",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.trials = [
            Trial(
                trial_index=1,
                planned_attempts=1,
                attempt_identities=[
                    AttemptIdentity(
                        campaign_id=campaign.campaign_id,
                        trial_index=1,
                        model_id="m1",
                        reasoning_effort="none",
                        output_mode="text",
                        fixture_id="f1",
                    )
                ],
            ),
        ]
        campaign.raw_attempts = [_attempt(campaign, "f1", 1, passed=True)]
        summary = compute_campaign_resource_summary(campaign)
        assert summary.partial_pricing is True



class TestAggregationGoldenScenarios:
    """Golden-style coverage of complete, incomplete, incompatible, legacy, and partial-pricing data."""

    def test_golden_complete_campaign(self):
        campaign = make_campaign(
            campaign_id="cmp-golden-complete",
            fixture_ids=["f1", "f2"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        ids = []
        for trial in (1, 2):
            for fixture in ("f1", "f2"):
                ids.append(AttemptIdentity(
                    campaign_id=campaign.campaign_id,
                    trial_index=trial,
                    model_id="m1",
                    reasoning_effort="none",
                    output_mode="text",
                    fixture_id=fixture,
                ))
        campaign.trials = [
            Trial(trial_index=1, planned_attempts=2, attempt_identities=ids[:2]),
            Trial(trial_index=2, planned_attempts=2, attempt_identities=ids[2:]),
        ]
        campaign.raw_attempts = [
            RawAttempt(identity=ids[0], status=AttemptStatus.VALID_PASS, passed=True),
            RawAttempt(identity=ids[1], status=AttemptStatus.VALID_PASS, passed=True),
            RawAttempt(identity=ids[2], status=AttemptStatus.VALID_PASS, passed=True),
            RawAttempt(identity=ids[3], status=AttemptStatus.VALID_FAIL, passed=False),
        ]
        refresh_campaign_aggregates(campaign)
        assert campaign.state == CampaignState.COMPLETE
        assert campaign.passing_attempts == 3
        assert campaign.excluded_attempts == 0

    def test_golden_incomplete_missing_attempt(self):
        campaign = make_campaign(
            campaign_id="cmp-golden-inc",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        id1 = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="none",
            output_mode="text",
            fixture_id="f1",
        )
        id2 = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=2,
            model_id="m1",
            reasoning_effort="none",
            output_mode="text",
            fixture_id="f1",
        )
        campaign.trials = [
            Trial(trial_index=1, planned_attempts=1, attempt_identities=[id1]),
            Trial(trial_index=2, planned_attempts=1, attempt_identities=[id2]),
        ]
        campaign.raw_attempts = [RawAttempt(identity=id1, status=AttemptStatus.VALID_PASS, passed=True)]
        refresh_campaign_aggregates(campaign)
        assert campaign.state == CampaignState.INCOMPLETE

    def test_golden_incompatible_hash_mismatch(self):
        campaign = make_campaign(
            campaign_id="cmp-golden-mismatch",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        id1 = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="none",
            output_mode="text",
            fixture_id="f1",
        )
        campaign.trials = [Trial(trial_index=1, planned_attempts=1, attempt_identities=[id1])]
        campaign.config.expected_fixture_hashes = {
            "f1": FixtureExpectedHashes(fixture_input_hash="expected"),
        }
        attempt = RawAttempt(
            identity=id1,
            status=AttemptStatus.VALID_PASS,
            passed=True,
            provenance=Provenance(
                fixture_input_hash="wrong",
                rendered_prompt_hash="",
                expected_hash="",
            ),
        )
        campaign.raw_attempts = [attempt]
        campaign.classify_attempts()
        refresh_campaign_aggregates(campaign)
        assert campaign.excluded_attempts == 1
        assert campaign.state == CampaignState.INCOMPLETE

    def test_golden_partial_pricing(self):
        campaign = make_campaign(
            campaign_id="cmp-golden-partial",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        id1 = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="none",
            output_mode="text",
            fixture_id="f1",
        )
        campaign.trials = [Trial(trial_index=1, planned_attempts=1, attempt_identities=[id1])]
        campaign.raw_attempts = [
            RawAttempt(identity=id1, status=AttemptStatus.VALID_PASS, passed=True),
        ]
        summary = compute_campaign_resource_summary(campaign)
        assert summary.partial_pricing is True
        assert summary.total_cost_usd is None
