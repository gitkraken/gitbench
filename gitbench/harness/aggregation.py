"""Campaign aggregation from immutable raw attempts.

This module produces trial, fixture, model, benchmark, and campaign-level
summaries from a :class:`Campaign` and its raw attempts.  It is intentionally
separate from execution so that aggregation can be recomputed after resume,
repair, or import without re-running model calls.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from gitbench.harness.campaign import (
    AttemptStatus,
    BenchmarkCampaignSummary,
    Campaign,
    CampaignState,
    FixtureAggregate,
    FixtureReliability,
    ModelCampaignSummary,
    ResourceSummary,
    Trial,
    compute_fixture_aggregates,
    _identity_benchmark,
)


def compute_trial_aggregates(campaign: Campaign) -> list[Trial]:
    """Return per-trial summaries from raw attempts.

    Attempts that fail the provenance check or are otherwise non-quality
    outcomes are counted as excluded and prevent the trial from being
    considered complete.
    """
    planned_by_trial: dict[int, set[tuple[str, str, str, str, str]]] = defaultdict(set)
    identities_by_trial: dict[int, list] = defaultdict(list)
    for trial in campaign.trials:
        for identity in trial.attempt_identities:
            identities_by_trial[trial.trial_index].append(identity)
            planned_by_trial[trial.trial_index].add(
                (
                    identity.model_id,
                    identity.reasoning_effort,
                    identity.output_mode,
                    _identity_benchmark(identity),
                    identity.fixture_id,
                )
            )

    attempts_by_trial: dict[int, list[Any]] = defaultdict(list)
    for attempt in campaign.raw_attempts:
        attempts_by_trial.setdefault(attempt.identity.trial_index, []).append(
            attempt
        )

    trials: list[Trial] = []
    for trial_index in sorted(planned_by_trial.keys()):
        planned = planned_by_trial[trial_index]
        attempts = attempts_by_trial.get(trial_index, [])
        # Only count attempts whose identity belongs to this trial's plan.
        completed = [
            a
            for a in attempts
            if (
                a.identity.model_id,
                a.identity.reasoning_effort,
                a.identity.output_mode,
                _identity_benchmark(a.identity),
                a.identity.fixture_id,
            )
            in planned
        ]
        valid = [a for a in completed if a.status.is_quality_outcome()]
        passing = [a for a in valid if a.passed]
        excluded = len(completed) - len(valid)
        trial = Trial(
            trial_index=trial_index,
            planned_attempts=len(planned),
            completed_attempts=len(completed),
            valid_attempts=len(valid),
            passing_attempts=len(passing),
            excluded_attempts=excluded,
            complete=(len(completed) == len(planned) and excluded == 0),
            attempt_identities=identities_by_trial.get(trial_index, []),
        )
        trials.append(trial)

    return trials


def _resource_summary_from_attempts(
    attempts: list[Any],
) -> ResourceSummary:
    """Compute a resource summary from a collection of raw attempts.

    Includes target-call costs, retry costs, judge costs, and safety-review
    costs when available.  Marks totals partial when any quality attempt is
    missing pricing.
    """
    total_cost: float | None = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    total_tokens = 0
    total_reasoning_tokens = 0
    total_api_duration_ms = 0.0
    partial_pricing = False

    for attempt in attempts:
        # Target and retry costs.
        if attempt.cost_usd is not None:
            total_cost += attempt.cost_usd
        elif attempt.status.is_quality_outcome():
            partial_pricing = True

        # Judge costs from member evidence.
        judge_cost = 0.0
        if attempt.judge_evidence is not None:
            for member in attempt.judge_evidence.members or []:
                if member.cost_usd is not None:
                    judge_cost += member.cost_usd
        if judge_cost:
            total_cost += judge_cost

        # Safety-review costs.
        if attempt.safety_cost_usd is not None:
            total_cost += attempt.safety_cost_usd

        if attempt.input_tokens is not None:
            total_input_tokens += attempt.input_tokens
        if attempt.output_tokens is not None:
            total_output_tokens += attempt.output_tokens
        if attempt.total_tokens is not None:
            total_tokens += attempt.total_tokens
        if attempt.reasoning_tokens is not None:
            total_reasoning_tokens += attempt.reasoning_tokens
        if attempt.api_duration_ms is not None:
            total_api_duration_ms += attempt.api_duration_ms

    if total_cost == 0.0 and not any(
        a.cost_usd is not None or
        (a.judge_evidence is not None and any(
            m.cost_usd is not None for m in (a.judge_evidence.members or [])
        )) or
        a.safety_cost_usd is not None
        for a in attempts
    ):
        total_cost = None
    else:
        total_cost = round(total_cost, 6) if total_cost is not None else None

    return ResourceSummary(
        total_cost_usd=total_cost,
        total_input_tokens=total_input_tokens or None,
        total_output_tokens=total_output_tokens or None,
        total_tokens=total_tokens or None,
        total_reasoning_tokens=total_reasoning_tokens or None,
        total_api_duration_ms=round(total_api_duration_ms, 4)
        if total_api_duration_ms
        else None,
        partial_pricing=partial_pricing,
    )


def _mean_success_rate(
    valid_attempts: list[Any],
) -> float | None:
    """Return the mean success rate for a set of valid attempts."""
    passing = [a for a in valid_attempts if a.passed]
    if not valid_attempts:
        return None
    return round(len(passing) / len(valid_attempts), 4)


def compute_model_aggregates(
    campaign: Campaign,
    fixture_aggregates: list[FixtureAggregate] | None = None,
) -> list[ModelCampaignSummary]:
    """Return per-model campaign summaries from raw attempts."""
    if fixture_aggregates is None:
        fixture_aggregates = compute_fixture_aggregates(campaign)

    attempts_by_model: dict[tuple[str, str, str], list[Any]] = defaultdict(list)
    for attempt in campaign.raw_attempts:
        attempts_by_model[
            (
                attempt.identity.model_id,
                attempt.identity.reasoning_effort,
                attempt.identity.output_mode,
            )
        ].append(attempt)

    summaries: list[ModelCampaignSummary] = []
    for model_id in sorted(campaign.config.model_ids):
        model_keys = [key for key in attempts_by_model if key[0] == model_id]
        reasoning_efforts = (
            sorted(campaign.config.reasoning_efforts)
            if campaign.config.reasoning_efforts
            else sorted({key[1] for key in model_keys} or {"none"})
        )
        output_modes = (
            sorted(campaign.config.output_modes)
            if campaign.config.output_modes
            else sorted({key[2] for key in model_keys} or {"text"})
        )
        for reasoning_effort in reasoning_efforts:
            for output_mode in output_modes:
                attempts = attempts_by_model.get((model_id, reasoning_effort, output_mode), [])
                valid = [a for a in attempts if a.status.is_quality_outcome()]
                passing = [a for a in valid if a.passed]
                excluded = [a for a in attempts if not a.status.is_quality_outcome()]

                # Completed trials for this exact variant.
                trial_indices = {a.identity.trial_index for a in attempts}
                incomplete = (
                    len(trial_indices) < campaign.config.planned_trial_count
                    or bool(excluded)
                )

                summaries.append(
                    ModelCampaignSummary(
                        model_id=model_id,
                        reasoning_effort=reasoning_effort or None,
                        output_mode=output_mode,
                        planned_trials=campaign.config.planned_trial_count,
                        completed_trials=len(trial_indices),
                        valid_attempts=len(valid),
                        passing_attempts=len(passing),
                        excluded_attempts=len(excluded),
                        mean_success_rate=_mean_success_rate(valid),
                        resource_summary=_resource_summary_from_attempts(attempts),
                        incomplete=incomplete,
                    )
                )

    return summaries


def compute_benchmark_aggregates(
    campaign: Campaign,
    fixture_aggregates: list[FixtureAggregate] | None = None,
) -> list[BenchmarkCampaignSummary]:
    """Return per-benchmark campaign summaries from raw attempts.

    For now each campaign is tied to a single benchmark, but the schema
    supports multiple benchmarks per campaign for future expansion.
    """
    if fixture_aggregates is None:
        fixture_aggregates = compute_fixture_aggregates(campaign)

    summaries: list[BenchmarkCampaignSummary] = []
    for benchmark_id in sorted(campaign.config.benchmark_ids):
        attempts = [
            a
            for a in campaign.raw_attempts
            if _identity_benchmark(a.identity) == benchmark_id
        ]
        valid = [a for a in attempts if a.status.is_quality_outcome()]
        passing = [a for a in valid if a.passed]
        excluded = [a for a in attempts if not a.status.is_quality_outcome()]
        trial_indices = {a.identity.trial_index for a in attempts}

        # Completeness requires every planned trial to have all fixtures.
        fixture_count = len(
            [
                f
                for f in campaign.config.fixture_ids
                if f.startswith(f"{benchmark_id}/")
            ]
        )
        if fixture_count == 0:
            fixture_count = len(campaign.config.fixture_ids)
        expected_attempts = (
            campaign.config.planned_trial_count
            * fixture_count
            * len(campaign.config.model_ids)
            * len(campaign.config.output_modes)
        )
        incomplete = (
            len(attempts) < expected_attempts
            or bool(excluded)
        )

        summaries.append(
            BenchmarkCampaignSummary(
                benchmark=benchmark_id,
                planned_trials=campaign.config.planned_trial_count,
                completed_trials=len(trial_indices),
                valid_attempts=len(valid),
                passing_attempts=len(passing),
                excluded_attempts=len(excluded),
                mean_success_rate=_mean_success_rate(valid),
                resource_summary=_resource_summary_from_attempts(attempts),
                incomplete=incomplete,
            )
        )

    return summaries


def compute_campaign_resource_summary(
    campaign: Campaign,
) -> ResourceSummary:
    """Return a campaign-level resource summary from all raw attempts.

    Totals include consumption from every recorded attempt, including failed
    calls.  Mean per complete trial is computed over trials that finished
    without operational exclusions.  Wall-clock duration is tracked separately
    from summed API time.
    """
    summary = _resource_summary_from_attempts(list(campaign.raw_attempts))
    complete_trial_indices = {
        t.trial_index for t in campaign.trials if t.complete
    }
    if complete_trial_indices:
        complete_attempts = [
            a
            for a in campaign.raw_attempts
            if a.identity.trial_index in complete_trial_indices
        ]
        complete_count = len(complete_trial_indices)

        total_cost = 0.0
        total_tokens = 0
        total_api_duration = 0.0
        partial = False
        for attempt in complete_attempts:
            if attempt.cost_usd is not None:
                total_cost += attempt.cost_usd
            else:
                partial = True
            if attempt.total_tokens is not None:
                total_tokens += attempt.total_tokens
            if attempt.api_duration_ms is not None:
                total_api_duration += attempt.api_duration_ms

        if total_cost > 0:
            summary.mean_cost_per_complete_trial_usd = round(
                total_cost / complete_count, 6
            )
        if total_tokens > 0:
            summary.mean_tokens_per_complete_trial = round(
                total_tokens / complete_count, 2
            )
        if total_api_duration > 0:
            summary.mean_api_duration_per_complete_trial_ms = round(
                total_api_duration / complete_count, 4
            )
        summary.partial_pricing = summary.partial_pricing or partial

    # Wall-clock duration is separate from summed API time.
    if campaign.updated_at and campaign.created_at:
        from datetime import datetime
        try:
            created = datetime.fromisoformat(campaign.created_at)
            updated = datetime.fromisoformat(campaign.updated_at)
            delta_ms = (updated - created).total_seconds() * 1000
            if delta_ms >= 0:
                summary.total_wall_duration_ms = round(delta_ms, 2)
        except Exception:
            pass

    return summary


def is_ranking_eligible(campaign: Campaign) -> bool:
    """Return True when a campaign may be used for default rankings.

    Rankings require a complete, balanced campaign: every planned attempt
    executed and no operational/invalid exclusions.
    """
    return (
        campaign.planned_attempts > 0
        and campaign.completed_attempts == campaign.planned_attempts
        and campaign.excluded_attempts == 0
        and not campaign.legacy
    )


def filter_ranking_eligible(
    summaries: list[ModelCampaignSummary],
) -> list[ModelCampaignSummary]:
    """Return only complete, balanced model summaries for default rankings."""
    return [s for s in summaries if not s.incomplete]


def refresh_campaign_aggregates(campaign: Campaign) -> Campaign:
    """Recompute every aggregate on a campaign from its raw attempts.

    Mutates ``campaign`` in place and returns it.
    """
    from gitbench.harness.campaign import _now_iso

    campaign.trials = compute_trial_aggregates(campaign)
    campaign.fixture_aggregates = compute_fixture_aggregates(campaign)
    campaign.updated_at = _now_iso()
    campaign.resource_summary = compute_campaign_resource_summary(campaign)

    # Update top-level counts using the trial aggregates.
    campaign.planned_attempts = sum(t.planned_attempts for t in campaign.trials)
    campaign.completed_attempts = sum(t.completed_attempts for t in campaign.trials)
    campaign.valid_attempts = sum(t.valid_attempts for t in campaign.trials)
    campaign.passing_attempts = sum(t.passing_attempts for t in campaign.trials)
    campaign.excluded_attempts = sum(t.excluded_attempts for t in campaign.trials)

    campaign.state = (
        CampaignState.COMPLETE
        if (
            campaign.planned_attempts > 0
            and campaign.completed_attempts == campaign.planned_attempts
            and campaign.excluded_attempts == 0
        )
        else CampaignState.INCOMPLETE
    )

    return campaign
