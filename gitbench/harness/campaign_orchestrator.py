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
    compute_fixture_expected_hashes,
    make_campaign,
)
from gitbench.harness.scheduler import CampaignSchedule, build_schedule
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
            fixture_ids.append(fixture.id)
            executor, repo_path = benchmark.setup_fixture(
                fixture, fixture_generation_context=context
            )
            try:
                diff = benchmark.get_diff(repo_path)
                rendered_prompt = benchmark.format_prompt(fixture, diff)
                expected_hashes[fixture.id] = compute_fixture_expected_hashes(
                    fixture,
                    context,
                    rendered_prompt=rendered_prompt,
                    request_config=request_config,
                    scorer_config=scorer_config,
                )
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
        scorer_config=scorer_config,
        judge_config=judge_config,
        request_config=request_config,
        safety_review_config=safety_review_config,
    )
    campaign.config.expected_fixture_hashes = expected_hashes
    campaign.refresh_config_hash()
    campaign.state = CampaignState.PLANNED

    # Attach a schedule for consumers that need the exact planned order.
    campaign._schedule = build_schedule(
        campaign_id=campaign_id,
        fixture_ids=fixture_ids,
        models=[(m[0], m[1]) for m in models],
        output_modes=output_modes,
        planned_trial_count=planned_trial_count,
        seed=scheduler_seed,
    )
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
    import json

    results_dir = Path(results_dir)
    campaign_dir = results_dir / campaign.campaign_id
    campaign_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = campaign_dir / "campaign.json"
    manifest_path.write_text(json.dumps(campaign.to_manifest_dict(), indent=2))
    return manifest_path
