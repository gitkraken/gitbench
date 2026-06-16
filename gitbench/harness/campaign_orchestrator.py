"""Campaign orchestration for the benchmark runner.

This module connects CLI-level campaign inputs to the campaign model and
scheduler, producing a planned campaign manifest without executing attempts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gitbench.harness.benchmark import Benchmark
from gitbench.harness.campaign import (
    Campaign,
    CampaignState,
    FixtureExpectedHashes,
    Trial,
    compute_fixture_expected_hashes,
    hash_request_config,
    hash_scorer_config,
    make_campaign,
)
from gitbench.harness.scheduler import CampaignSchedule, SCHEDULER_VERSION, build_schedule
from gitbench.harness.types import Fixture
from gitbench.utils.git import FixtureGenerationContext


def plan_campaign(
    campaign_id: str,
    benchmarks: list[tuple[str, Benchmark]],
    models: list[tuple[str, str, dict[str, Any]]],
    output_modes: list[str],
    *,
    planned_trial_count: int = 3,
    scheduler_seed: int | None = None,
    scorer_config: dict[str, Any] | None = None,
    judge_config: dict[str, Any] | None = None,
    request_config: dict[str, Any] | None = None,
    fixture_generation_version: str = "",
    safety_review_config: dict[str, Any] | None = None,
) -> Campaign:
    """Plan a new evaluation campaign from resolved CLI inputs.

    Args:
        campaign_id: Unique campaign identifier.
        benchmarks: List of ``(benchmark_name, benchmark_instance)`` pairs.
        models: List of ``(model_id, reasoning_effort, resolved_profile)`` tuples.
        output_modes: Output modes to evaluate.
        planned_trial_count: Number of complete trial rounds.
        scheduler_seed: Optional seed for deterministic scheduling.
        scorer_config: Scorer configuration to persist.
        judge_config: Judge configuration to persist.
        request_config: Normalized request configuration to persist.
        fixture_generation_version: Version string for fixture generation.
        safety_review_config: Optional safety review configuration.

    Returns:
        A planned :class:`Campaign` with fixture hashes and schedule attached
        to its config.
    """
    fixture_ids: list[str] = []
    fixture_specs: list[tuple[str, str]] = []
    benchmark_ids: list[str] = []
    expected_hashes: dict[str, FixtureExpectedHashes] = {}

    # Use a deterministic fixture generation context for all fixtures.
    context = FixtureGenerationContext(
        version=fixture_generation_version,
        seed=scheduler_seed,
    )

    for benchmark_name, benchmark in benchmarks:
        benchmark_ids.append(benchmark_name)
        fixtures = benchmark.load_fixtures()
        for fixture in fixtures:
            qualified_fixture_id = f"{benchmark_name}/{fixture.id}"
            fixture_ids.append(qualified_fixture_id)
            fixture_specs.append((benchmark_name, fixture.id))
            executor, repo_path = benchmark.setup_fixture(
                fixture, fixture_generation_context=context
            )
            try:
                diff = benchmark.get_diff(repo_path)
                rendered_prompt = benchmark.format_prompt(fixture, diff)
                hashes = compute_fixture_expected_hashes(
                    fixture,
                    context,
                    rendered_prompt=rendered_prompt,
                    request_config=request_config,
                    scorer_config=scorer_config,
                )
                expected_hashes[qualified_fixture_id] = hashes
                expected_hashes.setdefault(fixture.id, hashes)
            finally:
                executor.cleanup()

    model_ids = [m[0] for m in models]
    reasoning_efforts = sorted({m[1] for m in models})

    campaign = make_campaign(
        campaign_id=campaign_id,
        benchmark_ids=sorted(set(benchmark_ids)),
        fixture_ids=fixture_ids,
        model_ids=sorted(set(model_ids)),
        reasoning_efforts=reasoning_efforts,
        output_modes=output_modes,
        planned_trial_count=planned_trial_count,
        scheduler_seed=scheduler_seed,
        fixture_generation_version=fixture_generation_version,
        scheduler_version=SCHEDULER_VERSION,
        scorer_config=scorer_config,
        judge_config=judge_config,
        request_config=request_config,
        request_config_hash=hash_request_config(request_config),
        scorer_config_hash=hash_scorer_config(scorer_config),
        safety_review_config=safety_review_config,
    )
    campaign.config.expected_fixture_hashes = expected_hashes
    campaign.refresh_config_hash()
    campaign.state = CampaignState.PLANNED

    # Attach a schedule for consumers that need the exact planned order.
    campaign._schedule = build_schedule(
        campaign_id=campaign_id,
        fixture_ids=[fixture_id for _benchmark, fixture_id in fixture_specs],
        models=[(m[0], m[1]) for m in models],
        output_modes=output_modes,
        planned_trial_count=planned_trial_count,
        seed=scheduler_seed,
        fixture_specs=fixture_specs,
    )
    campaign.trials = [
        Trial(
            trial_index=trial_index,
            planned_attempts=len(identities),
            attempt_identities=identities,
        )
        for trial_index, identities in campaign._schedule.trial_identities.items()
    ]
    campaign.planned_attempts = campaign._schedule.planned_attempts
    return campaign


def write_campaign_manifest(
    campaign: Campaign,
    results_dir: str | Path = "gitbench-results",
) -> Path:
    """Write a campaign's manifest to ``<results_dir>/<campaign-id>/campaign.json``.

    Args:
        campaign: Campaign to persist.
        results_dir: Base results directory.

    Returns:
        Path to the written manifest file.
    """
    results_dir = Path(results_dir)
    from gitbench.harness.campaign_store import CampaignStore

    return CampaignStore(campaign.campaign_id, base_dir=results_dir).save_manifest(
        campaign
    )
