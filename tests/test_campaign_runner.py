"""Runner integration tests for campaign execution, resume, and repair."""

from gitbench.benchmarks.reflog import ReflogBenchmark
from gitbench.harness.campaign import (
    AttemptIdentity,
    AttemptStatus,
    Campaign,
    CampaignState,
    Provenance,
    RawAttempt,
    Trial,
)
from gitbench.harness.campaign_orchestrator import plan_campaign
from gitbench.harness.campaign_store import (
    CampaignStore,
    build_resume_plan,
    update_campaign_counts,
)
from gitbench.harness.scheduler import build_schedule
from gitbench.version import BENCHMARK_SUITE_VERSION


def _build_provenance(campaign: Campaign, identity: AttemptIdentity) -> Provenance:
    """Return compatible provenance for an identity."""
    expected = campaign.config.expected_fixture_hashes.get(identity.fixture_id)
    return Provenance(
        fixture_input_hash=expected.fixture_input_hash if expected else "",
        rendered_prompt_hash=expected.rendered_prompt_hash if expected else "",
        expected_hash=expected.expected_hash if expected else "",
        scoring_input_hash=expected.scoring_input_hash if expected else None,
        request_config_hash=expected.request_config_hash if expected else None,
        scorer_config_hash=expected.scorer_config_hash if expected else None,
        fixture_generation_version=campaign.config.fixture_generation_version,
        scheduler_seed=campaign.config.scheduler_seed,
    )


def _execute_identity(
    campaign: Campaign,
    identity: AttemptIdentity,
    *,
    passed: bool = True,
) -> RawAttempt:
    """Simulate a runner producing a raw attempt for an identity."""
    return RawAttempt(
        identity=identity,
        status=AttemptStatus.VALID_PASS if passed else AttemptStatus.VALID_FAIL,
        passed=passed,
        model_output="",
        provenance=_build_provenance(campaign, identity),
    )


def _setup_campaign(tmp_path: str, campaign_id: str) -> tuple[Campaign, CampaignStore]:
    """Plan a campaign with one mock model over the reflog benchmark."""
    benchmark = ReflogBenchmark()
    campaign = plan_campaign(
        campaign_id=campaign_id,
        benchmarks=[("reflog", benchmark)],
        models=[("mock", "none", {})],
        output_modes=["text"],
        planned_trial_count=2,
        fixture_generation_version=BENCHMARK_SUITE_VERSION,
    )
    store = CampaignStore(campaign_id, base_dir=str(tmp_path))
    store.save_manifest(campaign)
    # Ensure schedule-backed resume plan works.
    schedule = build_schedule(
        campaign_id=campaign.campaign_id,
        fixture_ids=campaign.config.fixture_ids,
        models=[(m, "none") for m in campaign.config.model_ids],
        output_modes=campaign.config.output_modes,
        planned_trial_count=campaign.config.planned_trial_count,
        seed=campaign.config.scheduler_seed,
    )
    campaign._schedule = schedule
    campaign.trials = [
        Trial(
            trial_index=trial_index,
            planned_attempts=len(identities),
            attempt_identities=identities,
        )
        for trial_index, identities in schedule.trial_identities.items()
    ]
    store.save_manifest(campaign)
    return campaign, store


class TestCompleteCampaign:
    """A runner can execute every planned attempt and complete a campaign."""

    def test_execute_all_attempts_completes_campaign(self, tmp_path):
        campaign, store = _setup_campaign(tmp_path, "cmp-complete")
        needed = build_resume_plan(campaign, store)
        assert needed

        for identity in needed:
            attempt = _execute_identity(campaign, identity, passed=True)
            store.write_attempt(attempt)

        campaign.raw_attempts = store.load_all_attempts()
        update_campaign_counts(campaign)
        store.save_manifest(campaign)

        loaded = store.load_manifest()
        assert loaded is not None
        assert loaded.state == CampaignState.COMPLETE
        assert loaded.completed_attempts == loaded.planned_attempts
        assert loaded.excluded_attempts == 0


class TestInterruptedCampaign:
    """Interrupted campaigns resume only missing attempts."""

    def test_resume_after_partial_run(self, tmp_path):
        campaign, store = _setup_campaign(tmp_path, "cmp-resume")
        needed = build_resume_plan(campaign, store)
        total = len(needed)
        assert total > 1

        # Execute roughly half the attempts, then stop (interruption).
        first_batch = needed[: total // 2]
        for identity in first_batch:
            store.write_attempt(_execute_identity(campaign, identity))

        # Reload and resume.
        campaign = store.load_manifest()
        assert not hasattr(campaign, "_schedule")
        needed_after = build_resume_plan(campaign, store)
        assert len(needed_after) == total - len(first_batch)
        assert not any(i in needed_after for i in first_batch)

        for identity in needed_after:
            store.write_attempt(_execute_identity(campaign, identity))

        campaign.raw_attempts = store.load_all_attempts()
        update_campaign_counts(campaign)
        store.save_manifest(campaign)

        loaded = store.load_manifest()
        assert loaded.state == CampaignState.COMPLETE
        assert loaded.completed_attempts == total


class TestDuplicatePrevention:
    """Valid existing attempts are not duplicated by ordinary resume."""

    def test_resume_does_not_reschedule_valid_attempts(self, tmp_path):
        campaign, store = _setup_campaign(tmp_path, "cmp-dup")
        needed = build_resume_plan(campaign, store)
        total = len(needed)

        # Complete the campaign once.
        for identity in needed:
            store.write_attempt(_execute_identity(campaign, identity))
        campaign.raw_attempts = store.load_all_attempts()
        update_campaign_counts(campaign)
        store.save_manifest(campaign)

        # A fresh resume sees nothing to do.
        reloaded = store.load_manifest()
        needed_after = build_resume_plan(reloaded, store)
        assert len(needed_after) == 0
        assert reloaded.completed_attempts == total


class TestConfigurationMismatch:
    """Attempts with incompatible provenance are rejected during resume."""

    def test_hash_mismatch_is_rescheduled(self, tmp_path):
        campaign, store = _setup_campaign(tmp_path, "cmp-mismatch")
        needed = build_resume_plan(campaign, store)
        identity = needed[0]

        # Write an attempt with a mismatched fixture hash.
        bad_attempt = RawAttempt(
            identity=identity,
            status=AttemptStatus.VALID_PASS,
            passed=True,
            provenance=Provenance(
                fixture_input_hash="wrong-hash",
                rendered_prompt_hash="b",
                expected_hash="c",
                fixture_generation_version=campaign.config.fixture_generation_version,
                scheduler_seed=campaign.config.scheduler_seed,
            ),
        )
        store.write_attempt(bad_attempt)

        reloaded = store.load_manifest()
        needed_after = build_resume_plan(reloaded, store)
        assert identity in needed_after
        assert len(needed_after) == len(needed)

    def test_fixture_generation_version_mismatch_is_rescheduled(self, tmp_path):
        campaign, store = _setup_campaign(tmp_path, "cmp-version")
        needed = build_resume_plan(campaign, store)
        identity = needed[0]

        provenance = _build_provenance(campaign, identity)
        provenance.fixture_generation_version = "0.0.0"
        bad_attempt = RawAttempt(
            identity=identity,
            status=AttemptStatus.VALID_PASS,
            passed=True,
            provenance=provenance,
        )
        store.write_attempt(bad_attempt)

        reloaded = store.load_manifest()
        needed_after = build_resume_plan(reloaded, store)
        assert identity in needed_after


class TestTargetedRepair:
    """Explicit repair targets an exact identity while preserving history."""

    def test_repair_retries_exact_identity(self, tmp_path):
        campaign, store = _setup_campaign(tmp_path, "cmp-repair")
        needed = build_resume_plan(campaign, store)
        identity = needed[0]

        # Original attempt failed with infrastructure error.
        original = RawAttempt(
            identity=identity,
            status=AttemptStatus.INFRASTRUCTURE_FAILURE,
            passed=False,
            error="timeout",
            provenance=_build_provenance(campaign, identity),
        )
        store.write_attempt(original)

        # Repair replaces the attempt with a passing result.
        repair = RawAttempt(
            identity=identity,
            status=AttemptStatus.VALID_PASS,
            passed=True,
            provenance=_build_provenance(campaign, identity),
        )
        store.repair_attempt(repair)

        loaded = store.load_attempt(identity)
        assert loaded.status == AttemptStatus.VALID_PASS
        assert loaded.passed is True
        assert any(
            h.get("status") == "infrastructure_failure"
            and h.get("error") == "timeout"
            for h in loaded.retry_history
        )

    def test_repair_does_not_create_duplicate_envelopes(self, tmp_path):
        campaign, store = _setup_campaign(tmp_path, "cmp-repair-dedup")
        needed = build_resume_plan(campaign, store)
        identity = needed[0]

        original = RawAttempt(
            identity=identity,
            status=AttemptStatus.INFRASTRUCTURE_FAILURE,
            passed=False,
            provenance=_build_provenance(campaign, identity),
        )
        store.write_attempt(original)

        repair = RawAttempt(
            identity=identity,
            status=AttemptStatus.VALID_PASS,
            passed=True,
            provenance=_build_provenance(campaign, identity),
        )
        store.repair_attempt(repair)

        # Only one envelope should exist for the identity.
        envelopes = store.list_attempt_envelopes()
        matching = [
            p for p in envelopes
            if f"trial-{identity.trial_index:04d}" in p.name
            and identity.fixture_id.replace("/", "_") in p.name
        ]
        assert len(matching) == 1
