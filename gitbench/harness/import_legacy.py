"""Import historical result artifacts as one-trial legacy campaigns."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from gitbench.harness.aggregation import refresh_campaign_aggregates
from gitbench.harness.campaign import (
    AttemptIdentity,
    AttemptStatus,
    BenchmarkCampaignSummary,
    Campaign,
    CampaignConfig,
    CampaignState,
    FixtureAggregate,
    ModelCampaignSummary,
    Provenance,
    RawAttempt,
    ResourceSummary,
)
from gitbench.version import BENCHMARK_SUITE_VERSION


def _attempt_status_from_score(score: dict[str, Any]) -> AttemptStatus:
    """Map a historical score to an attempt status without inferring cause."""
    passed = score.get("passed")
    error = score.get("error")
    if error:
        return AttemptStatus.VALID_FAIL
    return AttemptStatus.VALID_PASS if passed else AttemptStatus.VALID_FAIL


def import_legacy_campaign(
    envelope: dict[str, Any],
    *,
    campaign_id: str | None = None,
) -> Campaign:
    """Convert a historical result envelope into a one-trial legacy campaign.

    Legacy campaigns retain the original evidence but do not infer stability
    metrics.  Each fixture/model/output-mode combination becomes a single
    attempt in trial 1.
    """
    model_id = envelope.get("model", "unknown")
    output_mode = envelope.get("output_mode", "text")
    timestamp = envelope.get("timestamp", datetime.now(timezone.utc).isoformat())

    benchmark_ids: set[str] = set()
    fixture_ids: list[str] = []
    raw_attempts: list[RawAttempt] = []

    for result in envelope.get("results", []):
        benchmark = result.get("benchmark")
        if benchmark:
            benchmark_ids.add(benchmark)
        for score in result.get("scores", []):
            fixture_id = score.get("fixture_id")
            if not fixture_id:
                continue
            if fixture_id not in fixture_ids:
                fixture_ids.append(fixture_id)
            status = _attempt_status_from_score(score)
            attempt = RawAttempt(
                identity=AttemptIdentity(
                    campaign_id=campaign_id or f"legacy-{model_id}-{output_mode}",
                    trial_index=1,
                    model_id=model_id,
                    reasoning_effort=score.get("reasoning_level") or "none",
                    output_mode=output_mode,
                    fixture_id=fixture_id,
                ),
                status=status,
                passed=score.get("passed") if status.is_quality_outcome() else None,
                model_output=score.get("model_output", ""),
                similarity=score.get("similarity"),
                error=score.get("error"),
                input_tokens=score.get("input_tokens"),
                output_tokens=score.get("output_tokens"),
                total_tokens=score.get("total_tokens"),
                reasoning_tokens=score.get("reasoning_tokens"),
                cost_usd=score.get("cost_usd"),
                api_duration_ms=score.get("api_duration_ms"),
                duration_ms=score.get("duration_ms"),
                request_telemetry=score.get("request_telemetry"),
                judge_evidence=score.get("judge_evidence"),
                provenance=Provenance(
                    fixture_input_hash="",
                    rendered_prompt_hash="",
                    expected_hash="",
                    fixture_generation_version=BENCHMARK_SUITE_VERSION,
                ),
                created_at=timestamp,
            )
            raw_attempts.append(attempt)

    config = CampaignConfig(
        campaign_id=campaign_id or f"legacy-{model_id}-{output_mode}",
        created_at=timestamp,
        benchmark_ids=sorted(benchmark_ids),
        fixture_ids=fixture_ids,
        model_ids=[model_id],
        reasoning_efforts=["none"],
        output_modes=[output_mode],
        planned_trial_count=1,
        fixture_generation_version=BENCHMARK_SUITE_VERSION,
    )

    campaign = Campaign(
        campaign_id=config.campaign_id,
        config=config,
        config_hash=config.compute_hash(),
        state=CampaignState.INCOMPLETE,
        planned_attempts=len(raw_attempts),
        completed_attempts=len(raw_attempts),
        raw_attempts=raw_attempts,
        legacy=True,
        created_at=timestamp,
    )
    refresh_campaign_aggregates(campaign)
    return campaign



def import_legacy_campaigns_from_aggregate(
    data: dict[str, Any],
) -> list[Campaign]:
    """Build one-trial legacy campaigns from a legacy aggregate report.

    Uses the ``runs_meta`` and ``fixtures`` sections of an old aggregate to
    reconstruct campaigns without inferring stability metrics.
    """
    campaigns: list[Campaign] = []
    runs_meta = data.get("runs_meta", [])
    fixtures_by_model = data.get("fixtures", {})

    for meta in runs_meta:
        model_name = meta.get("model_name", meta.get("model", "unknown"))
        output_mode = meta.get("output_mode", "text")
        timestamp = meta.get("timestamp", datetime.now(timezone.utc).isoformat())
        campaign_id = f"legacy-{model_name}-{output_mode}-{timestamp}"

        benchmark_ids: set[str] = set()
        fixture_ids: list[str] = []
        raw_attempts: list[RawAttempt] = []

        for benchmark, fixtures_list in fixtures_by_model.get(model_name, {}).items():
            benchmark_ids.add(benchmark)
            for result in fixtures_list:
                fixture_id = result.get("fixture_id", "")
                if not fixture_id:
                    continue
                if fixture_id not in fixture_ids:
                    fixture_ids.append(fixture_id)
                status = _attempt_status_from_score(result)
                attempt = RawAttempt(
                    identity=AttemptIdentity(
                        campaign_id=campaign_id,
                        trial_index=1,
                        model_id=model_name,
                        reasoning_effort=result.get("reasoning_level") or "none",
                        output_mode=output_mode,
                        fixture_id=fixture_id,
                    ),
                    status=status,
                    passed=result.get("passed") if status.is_quality_outcome() else None,
                    model_output=result.get("model_output", ""),
                    similarity=result.get("similarity"),
                    error=result.get("error"),
                    input_tokens=result.get("input_tokens"),
                    output_tokens=result.get("output_tokens"),
                    total_tokens=result.get("total_tokens"),
                    reasoning_tokens=result.get("reasoning_tokens"),
                    cost_usd=result.get("cost_usd"),
                    api_duration_ms=result.get("api_duration_ms"),
                    duration_ms=result.get("duration_ms"),
                    request_telemetry=result.get("request_telemetry"),
                    judge_evidence=result.get("judge_evidence"),
                    provenance=Provenance(
                        fixture_input_hash="",
                        rendered_prompt_hash="",
                        expected_hash="",
                        fixture_generation_version=BENCHMARK_SUITE_VERSION,
                    ),
                    created_at=timestamp,
                )
                raw_attempts.append(attempt)

        if not raw_attempts:
            continue

        config = CampaignConfig(
            campaign_id=campaign_id,
            created_at=timestamp,
            benchmark_ids=sorted(benchmark_ids),
            fixture_ids=fixture_ids,
            model_ids=[model_name],
            reasoning_efforts=["none"],
            output_modes=[output_mode],
            planned_trial_count=1,
            fixture_generation_version=BENCHMARK_SUITE_VERSION,
        )

        campaign = Campaign(
            campaign_id=campaign_id,
            config=config,
            config_hash=config.compute_hash(),
            state=CampaignState.INCOMPLETE,
            planned_attempts=len(raw_attempts),
            completed_attempts=len(raw_attempts),
            raw_attempts=raw_attempts,
            legacy=True,
            created_at=timestamp,
        )
        refresh_campaign_aggregates(campaign)
        campaigns.append(campaign)

    return campaigns
