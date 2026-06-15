"""End-to-end test for a fixture evaluation campaign.

This test exercises campaign planning, repeated trials across text and
structured-output modes, judge scoring provenance, interruption/resume,
aggregation, report generation, and the public campaign-report schema.
It does not make live provider calls; raw attempts are constructed directly.
"""

from gitbench.export import build_campaign_report
from gitbench.harness.aggregation import (
    compute_benchmark_aggregates,
    compute_model_aggregates,
    refresh_campaign_aggregates,
)
from gitbench.harness.campaign import (
    AttemptIdentity,
    AttemptStatus,
    CampaignState,
    JudgeEvidence,
    JudgeMemberResult,
    RawAttempt,
    ResourceSummary,
    Trial,
    make_campaign,
)
from gitbench.harness.campaign_store import CampaignStore, build_resume_plan


class TestFixtureCampaignE2E:
    """End-to-end campaign covering text/structured output, trials, and reporting."""

    def _identity(self, trial, model, output_mode, fixture):
        return AttemptIdentity(
            campaign_id="cmp-e2e",
            trial_index=trial,
            model_id=model,
            reasoning_effort="low",
            output_mode=output_mode,
            fixture_id=fixture,
        )

    def _attempt(
        self,
        trial,
        model,
        output_mode,
        fixture,
        passed,
        status=AttemptStatus.VALID_PASS,
        structured_output=None,
    ):
        return RawAttempt(
            identity=self._identity(trial, model, output_mode, fixture),
            status=status if passed else AttemptStatus.VALID_FAIL,
            passed=passed,
            model_output="git status" if passed else "git log",
            parsed_payload=structured_output,
            raw_structured_output="{}" if structured_output is not None else None,
            similarity=1.0 if passed else 0.2,
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            cost_usd=0.001,
            api_duration_ms=100.0,
            judge_evidence=JudgeEvidence(
                judge_config_hash="jch-1",
                aggregation_method="single",
                final_passed=passed,
                final_score=1.0 if passed else 0.2,
                members=[
                    JudgeMemberResult(
                        member_id="judge-1",
                        model_id="judge-model",
                        passed=passed,
                        score=1.0 if passed else 0.2,
                        rationale="ok" if passed else "wrong",
                        cache_hit=False,
                    )
                ],
                cache_key="ck",
            ),
        )

    def test_full_campaign_lifecycle(self, tmp_path):
        campaign = make_campaign(
            campaign_id="cmp-e2e",
            benchmark_ids=["commit_messages"],
            fixture_ids=["commit_messages/f1", "commit_messages/f2"],
            model_ids=["model-a", "model-b"],
            reasoning_efforts=["low"],
            output_modes=["text", "json_schema"],
            planned_trial_count=2,
            scheduler_seed=42,
            fixture_generation_version="0.1.0",
        )
        campaign.trials = [
            Trial(trial_index=1, planned_attempts=8, attempt_identities=[]),
            Trial(trial_index=2, planned_attempts=8, attempt_identities=[]),
        ]
        for trial in campaign.trials:
            for model in campaign.config.model_ids:
                for output_mode in campaign.config.output_modes:
                    for fixture in campaign.config.fixture_ids:
                        trial.attempt_identities.append(
                            self._identity(trial.trial_index, model, output_mode, fixture)
                        )

        store = CampaignStore("cmp-e2e", base_dir=str(tmp_path))
        store.save_manifest(campaign)

        # Write all attempts for trial 1 and half of trial 2, simulating an interruption.
        attempts = []
        for trial_index in [1, 2]:
            for model in campaign.config.model_ids:
                for output_mode in campaign.config.output_modes:
                    for idx, fixture in enumerate(campaign.config.fixture_ids):
                        # Make text fail for fixture f2 on model-b to create flaky aggregate.
                        passed = not (
                            model == "model-b"
                            and output_mode == "text"
                            and fixture == "commit_messages/f2"
                        )
                        # Structured output only for json_schema mode.
                        structured = {"commit": "fix"} if output_mode == "json_schema" else None
                        attempt = self._attempt(
                            trial_index,
                            model,
                            output_mode,
                            fixture,
                            passed,
                            structured_output=structured,
                        )
                        attempts.append(attempt)
                        if trial_index == 1 or (trial_index == 2 and idx == 0):
                            store.write_attempt(attempt)

        # Resume should schedule the missing attempts before aggregates are refreshed.
        resume_plan = build_resume_plan(campaign, store)
        missing_identities = [
            identity
            for identity in resume_plan
            if identity.trial_index == 2 and identity.fixture_id == "commit_messages/f2"
        ]
        assert len(missing_identities) > 0

        # Write the remaining attempts.
        for attempt in attempts:
            if not store.attempt_exists(attempt.identity):
                store.write_attempt(attempt)

        campaign.raw_attempts = attempts
        refresh_campaign_aggregates(campaign)
        assert campaign.state == CampaignState.COMPLETE
        assert campaign.completed_attempts == 16

        campaign.resource_summary = ResourceSummary(
            total_cost_usd=0.016,
            total_input_tokens=160,
            total_output_tokens=80,
            total_tokens=240,
            total_api_duration_ms=1600.0,
            mean_cost_per_complete_trial_usd=0.008,
            mean_tokens_per_complete_trial=120.0,
            mean_api_duration_per_complete_trial_ms=800.0,
            partial_pricing=False,
        )

        model_summaries = compute_model_aggregates(campaign, campaign.fixture_aggregates)
        benchmark_summaries = compute_benchmark_aggregates(
            campaign, campaign.fixture_aggregates
        )
        assert any(ms.model_id == "model-a" for ms in model_summaries)
        assert any(bs.benchmark == "commit_messages" for bs in benchmark_summaries)

        report = build_campaign_report(campaign)
        assert report.schema_version == 2
        assert report.campaign.campaign_id == "cmp-e2e"
        assert len(report.judge_evidence) > 0

        # Verify a flaky fixture aggregate exists for the mixed-result case.
        flaky = next(
            (fa for fa in campaign.fixture_aggregates if fa.fixture_id == "commit_messages/f2"),
            None,
        )
        assert flaky is not None
        assert flaky.passing_attempts > 0 and flaky.failing_attempts > 0

        # Verify the report contains both output modes and multiple trials.
        raw = [a for a in report.campaign.raw_attempts if a.identity.output_mode == "json_schema"]
        assert len(raw) >= 4
