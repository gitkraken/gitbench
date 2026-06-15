"""Tests for campaign result store persistence."""

from gitbench.harness.campaign import (
    AttemptIdentity,
    AttemptStatus,
    Campaign,
    CampaignState,
    Provenance,
    RawAttempt,
    Trial,
    make_campaign,
)
from gitbench.harness.campaign_store import (
    CampaignStore,
    build_resume_plan,
    review_campaign_safety,
    update_campaign_counts,
)


class TestCampaignStore:
    """Tests for filesystem-backed campaign storage."""

    def _identity(self) -> AttemptIdentity:
        return AttemptIdentity(
            campaign_id="cmp-store-1",
            trial_index=1,
            model_id="m1",
            reasoning_effort="low",
            output_mode="text",
            fixture_id="f1",
        )

    def _attempt(self) -> RawAttempt:
        return RawAttempt(
            identity=self._identity(),
            status=AttemptStatus.VALID_PASS,
            passed=True,
            provenance=Provenance(
                fixture_input_hash="a",
                rendered_prompt_hash="b",
                expected_hash="c",
            ),
        )

    def test_save_and_load_manifest(self, tmp_path):
        store = CampaignStore("cmp-store-1", base_dir=str(tmp_path))
        campaign = make_campaign(
            campaign_id="cmp-store-1",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.trials = [
            Trial(trial_index=1, planned_attempts=1, completed_attempts=0),
        ]
        path = store.save_manifest(campaign)
        loaded = store.load_manifest()
        assert loaded is not None
        assert loaded.campaign_id == campaign.campaign_id
        assert loaded.config_hash == campaign.config_hash
        assert loaded.trials[0].planned_attempts == 1

    def test_write_and_load_attempt(self, tmp_path):
        store = CampaignStore("cmp-store-1", base_dir=str(tmp_path))
        attempt = self._attempt()
        path = store.write_attempt(attempt)
        assert path.exists()
        loaded = store.load_attempt(attempt.identity)
        assert loaded.identity == attempt.identity
        assert loaded.status == AttemptStatus.VALID_PASS

    def test_attempt_exists(self, tmp_path):
        store = CampaignStore("cmp-store-1", base_dir=str(tmp_path))
        attempt = self._attempt()
        assert not store.attempt_exists(attempt.identity)
        store.write_attempt(attempt)
        assert store.attempt_exists(attempt.identity)

    def test_load_all_attempts(self, tmp_path):
        store = CampaignStore("cmp-store-1", base_dir=str(tmp_path))
        store.write_attempt(self._attempt())
        second = RawAttempt(
            identity=AttemptIdentity(
                campaign_id="cmp-store-1",
                trial_index=1,
                model_id="m2",
                reasoning_effort="low",
                output_mode="text",
                fixture_id="f1",
            ),
            status=AttemptStatus.VALID_FAIL,
            passed=False,
        )
        store.write_attempt(second)
        loaded = store.load_all_attempts()
        assert len(loaded) == 2


class TestUpdateCampaignCounts:
    """Tests for atomic campaign count updates."""

    def test_complete_campaign_counts(self):
        campaign = make_campaign(
            campaign_id="cmp-counts",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        identity = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="low",
            output_mode="text",
            fixture_id="f1",
        )
        campaign.trials = [
            Trial(trial_index=1, planned_attempts=1, attempt_identities=[identity]),
        ]
        campaign.raw_attempts = [
            RawAttempt(identity=identity, status=AttemptStatus.VALID_PASS, passed=True),
        ]
        update_campaign_counts(campaign)
        assert campaign.state == CampaignState.COMPLETE
        assert campaign.completed_attempts == 1
        assert campaign.valid_attempts == 1
        assert campaign.passing_attempts == 1
        assert campaign.trials[0].complete

    def test_incomplete_campaign_counts(self):
        campaign = make_campaign(
            campaign_id="cmp-counts-inc",
            fixture_ids=["f1", "f2"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        identity1 = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="low",
            output_mode="text",
            fixture_id="f1",
        )
        campaign.trials = [
            Trial(
                trial_index=1,
                planned_attempts=2,
                attempt_identities=[identity1],
            ),
        ]
        campaign.raw_attempts = [
            RawAttempt(identity=identity1, status=AttemptStatus.VALID_PASS, passed=True),
        ]
        update_campaign_counts(campaign)
        assert campaign.state == CampaignState.INCOMPLETE
        assert campaign.completed_attempts == 1
        assert campaign.planned_attempts == 2

    def test_excluded_attempts(self):
        campaign = make_campaign(
            campaign_id="cmp-excl",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        identity = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="low",
            output_mode="text",
            fixture_id="f1",
        )
        campaign.trials = [
            Trial(trial_index=1, planned_attempts=1, attempt_identities=[identity]),
        ]
        campaign.raw_attempts = [
            RawAttempt(
                identity=identity,
                status=AttemptStatus.INFRASTRUCTURE_FAILURE,
                passed=False,
            ),
        ]
        update_campaign_counts(campaign)
        assert campaign.state == CampaignState.INCOMPLETE
        assert campaign.completed_attempts == 1
        assert campaign.valid_attempts == 0
        assert campaign.excluded_attempts == 1


class TestBuildResumePlan:
    """Tests for exact resume planning."""

    def _make_campaign(self) -> Campaign:
        from gitbench.harness.campaign import FixtureExpectedHashes
        campaign = make_campaign(
            campaign_id="cmp-resume",
            fixture_ids=["f1", "f2"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
            fixture_generation_version="0.3.0",
        )
        campaign.config.expected_fixture_hashes = {
            "f1": FixtureExpectedHashes(fixture_input_hash="f1-input"),
            "f2": FixtureExpectedHashes(fixture_input_hash="f2-input"),
        }
        campaign.refresh_config_hash()
        from gitbench.harness.scheduler import build_schedule
        schedule = build_schedule(
            campaign_id=campaign.campaign_id,
            fixture_ids=campaign.config.fixture_ids,
            models=[(m, "none") for m in campaign.config.model_ids],
            output_modes=campaign.config.output_modes,
            planned_trial_count=campaign.config.planned_trial_count,
            seed=42,
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
        return campaign

    def test_resume_empty_store_schedules_all(self, tmp_path):
        campaign = self._make_campaign()
        store = CampaignStore("cmp-resume", base_dir=str(tmp_path))
        store.save_manifest(campaign)
        needed = build_resume_plan(campaign, store)
        assert len(needed) == campaign._schedule.planned_attempts

    def test_resume_reuses_valid_attempts(self, tmp_path):
        campaign = self._make_campaign()
        store = CampaignStore("cmp-resume", base_dir=str(tmp_path))
        store.save_manifest(campaign)

        identity = campaign._schedule.identities[0]
        expected = campaign.config.expected_fixture_hashes.get(identity.fixture_id)
        provenance = Provenance(
            fixture_input_hash=expected.fixture_input_hash if expected else "a",
            rendered_prompt_hash=expected.rendered_prompt_hash if expected else "b",
            expected_hash=expected.expected_hash if expected else "c",
            fixture_generation_version=campaign.config.fixture_generation_version,
            scheduler_seed=campaign.config.scheduler_seed,
        )
        attempt = RawAttempt(
            identity=identity,
            status=AttemptStatus.VALID_PASS,
            passed=True,
            provenance=provenance,
        )
        store.write_attempt(attempt)

        needed = build_resume_plan(campaign, store)
        assert identity not in needed
        assert len(needed) == campaign._schedule.planned_attempts - 1

    def test_resume_invalidates_hash_mismatch(self, tmp_path):
        campaign = self._make_campaign()
        store = CampaignStore("cmp-resume", base_dir=str(tmp_path))
        store.save_manifest(campaign)

        identity = campaign._schedule.identities[0]
        attempt = RawAttempt(
            identity=identity,
            status=AttemptStatus.VALID_PASS,
            passed=True,
            provenance=Provenance(
                fixture_input_hash="wrong-hash",
                rendered_prompt_hash="b",
                expected_hash="c",
            ),
        )
        store.write_attempt(attempt)

        needed = build_resume_plan(campaign, store)
        assert identity in needed


class TestRepairAttempt:
    """Tests for targeted repair preserving failure history."""

    def test_repair_preserves_history(self, tmp_path):
        store = CampaignStore("cmp-repair", base_dir=str(tmp_path))
        identity = AttemptIdentity(
            campaign_id="cmp-repair",
            trial_index=1,
            model_id="m1",
            reasoning_effort="low",
            output_mode="text",
            fixture_id="f1",
        )
        first = RawAttempt(
            identity=identity,
            status=AttemptStatus.INFRASTRUCTURE_FAILURE,
            passed=False,
            error="timeout",
            request_telemetry={"retries": 3},
        )
        store.write_attempt(first)

        second = RawAttempt(
            identity=identity,
            status=AttemptStatus.VALID_PASS,
            passed=True,
        )
        store.repair_attempt(second)

        loaded = store.load_attempt(identity)
        assert loaded.status == AttemptStatus.VALID_PASS
        assert loaded.retry_history
        assert any(h.get("status") == "infrastructure_failure" for h in loaded.retry_history)
        assert any(h.get("error") == "timeout" for h in loaded.retry_history)


class TestReviewCampaignSafety:
    """Tests for integrating campaign publication with result-safety review."""

    def _attempt_with_output(self, fixture_id: str = "bench/f1", output: str = "safe output") -> RawAttempt:
        return RawAttempt(
            identity=AttemptIdentity(
                campaign_id="cmp-safety",
                trial_index=1,
                model_id="m1",
                reasoning_effort="low",
                output_mode="text",
                fixture_id=fixture_id,
            ),
            status=AttemptStatus.VALID_PASS,
            passed=True,
            model_output=output,
        )

    def test_review_marks_all_attempts_reviewed_when_allowed(self, tmp_path):
        store = CampaignStore("cmp-safety", base_dir=str(tmp_path))
        campaign = make_campaign(
            campaign_id="cmp-safety",
            fixture_ids=["bench/f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.state = CampaignState.COMPLETE
        campaign.raw_attempts = [self._attempt_with_output()]
        store.save_manifest(campaign)
        store.write_attempt(campaign.raw_attempts[0])

        class AllowProcessor:
            def review_payload(self, payload):
                for result in payload.get("results", []):
                    for score in result.get("scores", []):
                        score["safety_review"] = {"status": "allowed"}
                class Result:
                    pass
                r = Result()
                r.payload = payload
                r.redacted_scores = 0
                return r

        review_campaign_safety(campaign, AllowProcessor(), store)
        assert campaign.publication_state.value == "published"
        assert campaign.safety_summary["reviewed"] == 1
        loaded = store.load_attempt(campaign.raw_attempts[0].identity)
        assert loaded.safety_state == "reviewed"

    def test_review_blocks_redacted_attempts_and_stays_draft(self, tmp_path):
        store = CampaignStore("cmp-safety", base_dir=str(tmp_path))
        campaign = make_campaign(
            campaign_id="cmp-safety",
            fixture_ids=["bench/f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.state = CampaignState.COMPLETE
        campaign.raw_attempts = [self._attempt_with_output()]
        store.save_manifest(campaign)
        store.write_attempt(campaign.raw_attempts[0])

        class RedactProcessor:
            def review_payload(self, payload):
                for result in payload.get("results", []):
                    for score in result.get("scores", []):
                        score["safety_review"] = {"status": "redacted"}
                        score["model_output"] = "[Redacted - Reason: Inappropriate NSFW content]"
                class Result:
                    pass
                r = Result()
                r.payload = payload
                r.redacted_scores = 1
                return r

        review_campaign_safety(campaign, RedactProcessor(), store)
        assert campaign.publication_state.value == "draft"
        assert campaign.safety_summary["blocked"] == 1
        loaded = store.load_attempt(campaign.raw_attempts[0].identity)
        assert loaded.safety_state == "blocked"
