"""Exact-identity campaign execution helpers."""

from __future__ import annotations

from collections.abc import Callable

from gitbench.harness.aggregation import refresh_campaign_aggregates
from gitbench.harness.campaign import (
    AttemptIdentity,
    AttemptStatus,
    Campaign,
    FixtureExpectedHashes,
    JudgeEvidence,
    Provenance,
    RawAttempt,
    _now_iso,
)
from gitbench.harness.campaign_store import CampaignStore, build_resume_plan
from gitbench.harness.runner import BenchmarkRunner
from gitbench.harness.types import Score
from gitbench.utils.git import FixtureGenerationContext


class CampaignExecutionProgress:
    """Optional progress sink used by campaign execution."""

    def campaign_attempt_reused(self, count: int = 1) -> None: ...

    def campaign_attempt_completed(self, count: int = 1) -> None: ...

    def campaign_attempt_failed(self, count: int = 1) -> None: ...

    def campaign_attempt_recorded(
        self,
        status: str,
        *,
        safety_state: str | None = None,
        count: int = 1,
    ) -> None: ...


def identity_benchmark(identity: AttemptIdentity) -> str:
    """Return the benchmark name for an identity."""
    if identity.benchmark:
        return identity.benchmark
    if "/" in identity.fixture_id:
        return identity.fixture_id.split("/", 1)[0]
    return ""


def identity_fixture_id(identity: AttemptIdentity) -> str:
    """Return the fixture-local ID for an identity."""
    benchmark = identity_benchmark(identity)
    prefix = f"{benchmark}/" if benchmark else ""
    if prefix and identity.fixture_id.startswith(prefix):
        return identity.fixture_id[len(prefix) :]
    return identity.fixture_id


def expected_hashes_for_identity(
    campaign: Campaign,
    identity: AttemptIdentity,
) -> FixtureExpectedHashes | None:
    """Find expected fixture hashes for an exact identity."""
    keys = [
        f"{identity_benchmark(identity)}/{identity_fixture_id(identity)}",
        identity.fixture_id,
        identity_fixture_id(identity),
    ]
    for key in keys:
        expected = campaign.config.expected_fixture_hashes.get(key)
        if expected is not None:
            return expected
    return None


def raw_attempt_from_score(
    campaign: Campaign,
    identity: AttemptIdentity,
    score: Score,
) -> RawAttempt:
    """Convert a runner ``Score`` into a persisted campaign attempt envelope."""
    if score.unscored:
        status = AttemptStatus.UNSCORED
    elif score.operational_failure:
        status = AttemptStatus.INFRASTRUCTURE_FAILURE
    elif score.passed:
        status = AttemptStatus.VALID_PASS
    else:
        status = AttemptStatus.VALID_FAIL

    expected = expected_hashes_for_identity(campaign, identity)
    provenance = None
    if expected is not None:
        provenance = Provenance(
            fixture_input_hash=expected.fixture_input_hash,
            rendered_prompt_hash=expected.rendered_prompt_hash or "",
            expected_hash=expected.expected_hash or "",
            scoring_input_hash=expected.scoring_input_hash,
            request_config_hash=expected.request_config_hash,
            scorer_config_hash=expected.scorer_config_hash,
            judge_config_hash=campaign.config.scorer_config_hash,
            fixture_generation_version=campaign.config.fixture_generation_version,
            scheduler_seed=campaign.config.scheduler_seed,
        )

    judge_evidence = None
    if score.judge_evidence:
        judge_evidence = JudgeEvidence.from_dict(score.judge_evidence)

    now = _now_iso()
    return RawAttempt(
        identity=identity,
        status=status,
        model_output=score.model_output,
        parsed_payload=getattr(score, "_parsed_payload", None),
        raw_structured_output=getattr(score, "_raw_structured_output", None),
        structured_error=getattr(score, "_structured_error", None),
        passed=score.passed,
        similarity=score.similarity,
        error=score.error,
        input_tokens=score.input_tokens,
        output_tokens=score.output_tokens,
        total_tokens=score.total_tokens,
        reasoning_tokens=score.reasoning_tokens,
        cost_usd=score.cost_usd,
        provider_cost_usd=score.provider_cost_usd,
        api_duration_ms=score.api_duration_ms,
        duration_ms=score.duration_ms,
        request_telemetry=score.request_telemetry,
        provider_route_metadata=score.provider_route_metadata,
        provenance=provenance,
        judge_evidence=judge_evidence,
        created_at=now,
        updated_at=now,
    )


def execute_campaign(
    campaign: Campaign,
    store: CampaignStore,
    runner_for_identity: Callable[[AttemptIdentity], BenchmarkRunner],
    *,
    progress: CampaignExecutionProgress | None = None,
) -> Campaign:
    """Execute every missing exact identity and persist attempts atomically."""
    needed = build_resume_plan(campaign, store)
    planned = sum(len(trial.attempt_identities) for trial in campaign.trials)
    reused = max(0, planned - len(needed))
    if progress is not None and reused:
        progress.campaign_attempt_reused(reused)

    fixture_context = FixtureGenerationContext(
        version=campaign.config.fixture_generation_version,
        seed=campaign.config.scheduler_seed,
    )

    for identity in needed:
        expected = expected_hashes_for_identity(campaign, identity)
        scoring_context = None
        if expected is not None:
            scoring_context = {"fixture_input_hash": expected.fixture_input_hash}

        runner = runner_for_identity(identity)
        score = runner.run_fixture_identity(
            identity_benchmark(identity),
            identity_fixture_id(identity),
            fixture_generation_context=fixture_context,
            campaign_scoring_context=scoring_context,
        )
        attempt = raw_attempt_from_score(campaign, identity, score)
        store.write_attempt(attempt)

        campaign.raw_attempts = store.load_all_attempts()
        refresh_campaign_aggregates(campaign)
        store.save_manifest(campaign)

        if progress is not None:
            if hasattr(progress, "campaign_attempt_recorded"):
                progress.campaign_attempt_recorded(
                    attempt.status.value,
                    safety_state=attempt.safety_state,
                )
            elif attempt.status.is_quality_outcome():
                progress.campaign_attempt_completed()
            else:
                progress.campaign_attempt_failed()

    campaign.raw_attempts = store.load_all_attempts()
    refresh_campaign_aggregates(campaign)
    store.save_manifest(campaign)
    return campaign
