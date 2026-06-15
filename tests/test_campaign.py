"""Tests for the campaign-aware result model."""


from gitbench.harness.campaign import (
    AttemptIdentity,
    AttemptStatus,
    BenchmarkCampaignSummary,
    Campaign,
    CampaignReport,
    CampaignState,
    FixtureAggregate,
    FixtureExpectedHashes,
    FixtureReliability,
    JudgeEvidence,
    JudgeMemberResult,
    ModelCampaignSummary,
    Provenance,
    PublicationState,
    RawAttempt,
    ResourceSummary,
    Trial,
    compute_fixture_expected_hashes,
    hash_fixture_input,
    hash_rendered_prompt,
    make_campaign,
)
from gitbench.harness.types import Fixture
from gitbench.utils.git import FixtureGenerationContext


class TestAttemptIdentity:
    """Tests for exact attempt identity."""

    def test_roundtrip(self):
        original = AttemptIdentity(
            campaign_id="cmp-1",
            trial_index=2,
            model_id="gpt-4",
            reasoning_effort="medium",
            output_mode="json_schema",
            fixture_id="reflog/basic",
        )
        reconstructed = AttemptIdentity.from_dict(original.to_dict())
        assert reconstructed == original


class TestAttemptStatus:
    """Tests for attempt status enum."""

    def test_quality_outcomes(self):
        assert AttemptStatus.VALID_PASS.is_quality_outcome()
        assert AttemptStatus.VALID_FAIL.is_quality_outcome()
        assert not AttemptStatus.INFRASTRUCTURE_FAILURE.is_quality_outcome()
        assert not AttemptStatus.UNSCORED.is_quality_outcome()
        assert not AttemptStatus.SAFETY_BLOCKED.is_quality_outcome()
        assert not AttemptStatus.HASH_MISMATCH.is_quality_outcome()

    def test_serialization(self):
        assert AttemptStatus.VALID_FAIL.value == "valid_fail"


class TestProvenance:
    """Tests for attempt provenance."""

    def test_roundtrip(self):
        original = Provenance(
            fixture_input_hash="abc123",
            rendered_prompt_hash="def456",
            expected_hash="ghi789",
            scoring_input_hash="jkl012",
            request_config_hash="mno345",
            scorer_config_hash="pqr678",
            judge_config_hash="stu901",
            fixture_generation_version="0.3.0",
            scheduler_seed=42,
        )
        reconstructed = Provenance.from_dict(original.to_dict())
        assert reconstructed == original


class TestResourceSummary:
    """Tests for resource summaries."""

    def test_roundtrip(self):
        original = ResourceSummary(
            total_cost_usd=1.23,
            total_input_tokens=1000,
            total_output_tokens=500,
            total_api_duration_ms=1200.0,
            mean_cost_per_complete_trial_usd=0.41,
            mean_tokens_per_complete_trial=500.0,
            partial_pricing=True,
        )
        reconstructed = ResourceSummary.from_dict(original.to_dict())
        assert reconstructed == original


class TestJudgeEvidence:
    """Tests for judge evidence round-trips."""

    def test_roundtrip(self):
        original = JudgeEvidence(
            judge_config_hash="jch-1",
            aggregation_method="majority",
            final_passed=True,
            final_score=0.85,
            members=[
                JudgeMemberResult(
                    member_id="judge-1",
                    model_id="gpt-4",
                    passed=True,
                    score=0.9,
                    rationale="Correct",
                    cache_hit=False,
                ),
            ],
            cache_key="ck-1",
        )
        reconstructed = JudgeEvidence.from_dict(original.to_dict())
        assert reconstructed == original


class TestRawAttempt:
    """Tests for raw attempt serialization."""

    def test_roundtrip(self):
        identity = AttemptIdentity(
            campaign_id="cmp-1",
            trial_index=1,
            model_id="claude-3",
            reasoning_effort="high",
            output_mode="text",
            fixture_id="stash/basic",
        )
        provenance = Provenance(
            fixture_input_hash="a",
            rendered_prompt_hash="b",
            expected_hash="c",
        )
        original = RawAttempt(
            identity=identity,
            status=AttemptStatus.VALID_PASS,
            model_output="git stash pop",
            passed=True,
            similarity=0.92,
            input_tokens=120,
            output_tokens=30,
            total_tokens=150,
            cost_usd=0.002,
            api_duration_ms=450.0,
            provenance=provenance,
            created_at="2026-06-13T12:00:00+00:00",
        )
        reconstructed = RawAttempt.from_dict(original.to_dict())
        assert reconstructed == original


class TestFixtureAggregate:
    """Tests for fixture aggregates."""

    def test_roundtrip(self):
        original = FixtureAggregate(
            fixture_id="stash/basic",
            benchmark="stash_recovery",
            planned_trials=3,
            completed_trials=3,
            valid_attempts=3,
            passing_attempts=2,
            failing_attempts=1,
            mean_success_rate=0.6667,
            pass_any_at_n={1: True, 3: True},
            reliability_classification=FixtureReliability.FLAKY,
            incomplete=False,
        )
        data = original.to_dict()
        assert data["pass_any_at_n"] == {"1": True, "3": True}
        reconstructed = FixtureAggregate.from_dict(data)
        assert reconstructed == original

    def test_reliability_classification_values(self):
        assert FixtureReliability.STABLE_PASS.value == "stable_pass"
        assert FixtureReliability.FLAKY.value == "flaky"
        assert FixtureReliability.STABLE_FAIL.value == "stable_fail"


class TestTrial:
    """Tests for trial serialization."""

    def test_roundtrip(self):
        identity = AttemptIdentity(
            campaign_id="cmp-1",
            trial_index=1,
            model_id="model-a",
            reasoning_effort="low",
            output_mode="both",
            fixture_id="fixture-a",
        )
        original = Trial(
            trial_index=1,
            planned_attempts=10,
            completed_attempts=10,
            valid_attempts=10,
            complete=True,
            attempt_identities=[identity],
        )
        reconstructed = Trial.from_dict(original.to_dict())
        assert reconstructed == original


class TestCampaign:
    """Tests for campaign serialization and manifest behavior."""

    def test_make_campaign_roundtrip(self):
        campaign = make_campaign(
            campaign_id="cmp-2026-001",
            benchmark_ids=["reflog", "stash_recovery"],
            fixture_ids=["reflog/basic", "stash/basic"],
            model_ids=["gpt-4", "claude-3"],
            reasoning_efforts=["low", "medium"],
            output_modes=["text", "json_schema"],
            planned_trial_count=3,
            scheduler_seed=12345,
            fixture_generation_version="0.3.0",
        )
        campaign.state = CampaignState.COMPLETE
        campaign.publication_state = PublicationState.PUBLISHABLE
        campaign.trials = [
            Trial(trial_index=1, planned_attempts=8, completed_attempts=8, complete=True),
            Trial(trial_index=2, planned_attempts=8, completed_attempts=8, complete=True),
            Trial(trial_index=3, planned_attempts=8, completed_attempts=8, complete=True),
        ]
        campaign.fixture_aggregates = [
            FixtureAggregate(
                fixture_id="reflog/basic",
                planned_trials=3,
                completed_trials=3,
                valid_attempts=6,
                passing_attempts=6,
                mean_success_rate=1.0,
                pass_any_at_n={1: True, 3: True},
                reliability_classification=FixtureReliability.STABLE_PASS,
            ),
        ]
        campaign.resource_summary = ResourceSummary(
            total_cost_usd=5.0,
            mean_cost_per_complete_trial_usd=1.0,
        )

        data = campaign.to_manifest_dict()
        reconstructed = Campaign.from_manifest_dict(data)
        assert reconstructed.campaign_id == campaign.campaign_id
        assert reconstructed.config_hash == campaign.config_hash
        assert reconstructed.config.compute_hash() == campaign.config_hash
        assert reconstructed.state == CampaignState.COMPLETE
        assert reconstructed.publication_state == PublicationState.PUBLISHABLE
        assert len(reconstructed.trials) == 3
        assert reconstructed.trials[0].complete
        assert len(reconstructed.fixture_aggregates) == 1
        assert reconstructed.fixture_aggregates[0].mean_success_rate == 1.0

    def test_incomplete_campaign_roundtrip(self):
        campaign = make_campaign(
            campaign_id="cmp-incomplete",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=3,
        )
        campaign.state = CampaignState.INCOMPLETE
        campaign.trials = [
            Trial(
                trial_index=1,
                planned_attempts=1,
                completed_attempts=0,
                complete=False,
            ),
        ]

        data = campaign.to_dict()
        reconstructed = Campaign.from_dict(data)
        assert reconstructed.state == CampaignState.INCOMPLETE
        assert not reconstructed.trials[0].complete

    def test_one_trial_legacy_campaign_roundtrip(self):
        campaign = make_campaign(
            campaign_id="cmp-legacy-1",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.legacy = True
        campaign.trials = [
            Trial(
                trial_index=1,
                planned_attempts=1,
                completed_attempts=1,
                complete=True,
            ),
        ]
        campaign.fixture_aggregates = [
            FixtureAggregate(
                fixture_id="f1",
                planned_trials=1,
                completed_trials=1,
                valid_attempts=1,
                passing_attempts=1,
                mean_success_rate=1.0,
                pass_any_at_n={1: True},
                reliability_classification=FixtureReliability.STABLE_PASS,
            ),
        ]

        reconstructed = Campaign.from_dict(campaign.to_dict())
        assert reconstructed.legacy is True
        assert reconstructed.config.planned_trial_count == 1
        assert reconstructed.fixture_aggregates[0].pass_any_at_n[1] is True

    def test_safety_gated_campaign_roundtrip(self):
        identity = AttemptIdentity(
            campaign_id="cmp-safety",
            trial_index=1,
            model_id="m1",
            reasoning_effort="low",
            output_mode="text",
            fixture_id="f1",
        )
        campaign = make_campaign(
            campaign_id="cmp-safety",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
            safety_review_config={"enabled": True},
        )
        campaign.raw_attempts = [
            RawAttempt(
                identity=identity,
                status=AttemptStatus.SAFETY_BLOCKED,
                safety_state="blocked",
            ),
        ]
        campaign.publication_state = PublicationState.DRAFT
        campaign.safety_summary = {"blocked": 1, "pending": 0}

        reconstructed = Campaign.from_dict(campaign.to_dict())
        assert reconstructed.publication_state == PublicationState.DRAFT
        assert reconstructed.raw_attempts[0].status == AttemptStatus.SAFETY_BLOCKED
        assert reconstructed.safety_summary["blocked"] == 1

    def test_config_hash_detects_change(self):
        campaign = make_campaign(
            campaign_id="cmp-hash",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
        )
        original_hash = campaign.config_hash
        campaign.config.planned_trial_count = 5
        assert campaign.config.compute_hash() != original_hash


class TestFixtureExpectedHashes:
    """Tests for deterministic fixture provenance hashing."""

    def _make_fixture(self) -> Fixture:
        return Fixture(
            id="stash/basic",
            description="A test fixture",
            setup=["git init", "echo a > file.txt", "git add .", "git commit -m init"],
            prompt="What is the status?",
            expected="clean",
            scoring={"type": "similarity", "threshold": 0.8},
        )

    def _make_context(self) -> FixtureGenerationContext:
        return FixtureGenerationContext(
            version="0.3.0",
            seed=12345,
        )

    def test_fixture_input_hash_stable(self):
        fixture = self._make_fixture()
        context = self._make_context()
        first = hash_fixture_input(fixture, context)
        second = hash_fixture_input(fixture, context)
        assert first == second
        assert len(first) == 64

    def test_fixture_input_hash_sensitive_to_fixture_and_context(self):
        fixture = self._make_fixture()
        context = self._make_context()
        original = hash_fixture_input(fixture, context)

        fixture_changed = Fixture(
            id="stash/basic",
            description="A test fixture",
            setup=fixture.setup + ["echo b > file.txt"],
            prompt=fixture.prompt,
            expected=fixture.expected,
            scoring=fixture.scoring,
        )
        assert hash_fixture_input(fixture_changed, context) != original

        context_changed = FixtureGenerationContext(
            version="0.3.0",
            seed=99999,
        )
        assert hash_fixture_input(fixture, context_changed) != original

    def test_rendered_prompt_hash(self):
        assert hash_rendered_prompt("prompt-a") == hash_rendered_prompt("prompt-a")
        assert hash_rendered_prompt("prompt-a") != hash_rendered_prompt("prompt-b")

    def test_expected_hashes_roundtrip_in_config(self):
        fixture = self._make_fixture()
        context = self._make_context()
        prompt = "rendered prompt text"
        expected = compute_fixture_expected_hashes(
            fixture,
            context,
            rendered_prompt=prompt,
            request_config={"temperature": 0.0},
            scorer_config={"type": "similarity"},
        )

        campaign = make_campaign(
            campaign_id="cmp-hashes",
            fixture_ids=[fixture.id],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=3,
            fixture_generation_version=context.version,
            scheduler_seed=context.seed,
            request_config={"temperature": 0.0},
            scorer_config={"type": "similarity"},
        )
        campaign.config.expected_fixture_hashes = {fixture.id: expected}

        data = campaign.to_manifest_dict()
        reconstructed = Campaign.from_manifest_dict(data)
        assert reconstructed.config.expected_fixture_hashes[fixture.id] == expected
        assert reconstructed.config_hash == campaign.config_hash

    def test_config_hash_includes_expected_hashes(self):
        campaign = make_campaign(
            campaign_id="cmp-hash-change",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
        )
        original_hash = campaign.config_hash
        campaign.config.expected_fixture_hashes = {
            "f1": FixtureExpectedHashes(fixture_input_hash="abc"),
        }
        campaign.refresh_config_hash()
        assert campaign.config_hash != original_hash


class TestAttemptValidation:
    """Tests for campaign-level provenance validation."""

    def _make_campaign_with_expected_hashes(self) -> Campaign:
        fixture = Fixture(
            id="f1",
            description="desc",
            setup=["git init"],
            prompt="prompt",
            expected="expected",
            scoring={"type": "similarity"},
        )
        context = FixtureGenerationContext(version="0.3.0", seed=42)
        expected = compute_fixture_expected_hashes(
            fixture,
            context,
            rendered_prompt="rendered prompt",
            request_config={"temperature": 0.0},
            scorer_config={"type": "similarity"},
        )
        campaign = make_campaign(
            campaign_id="cmp-validate",
            fixture_ids=[fixture.id],
            model_ids=["m1"],
            output_modes=["text"],
            fixture_generation_version=context.version,
            scheduler_seed=context.seed,
            request_config={"temperature": 0.0},
            scorer_config={"type": "similarity"},
        )
        campaign.config.expected_fixture_hashes = {fixture.id: expected}
        campaign.refresh_config_hash()
        return campaign

    def test_validate_matching_attempt_returns_none(self):
        campaign = self._make_campaign_with_expected_hashes()
        expected = campaign.config.expected_fixture_hashes["f1"]
        identity = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="low",
            output_mode="text",
            fixture_id="f1",
        )
        attempt = RawAttempt(
            identity=identity,
            status=AttemptStatus.VALID_PASS,
            provenance=Provenance(
                fixture_input_hash=expected.fixture_input_hash,
                rendered_prompt_hash=expected.rendered_prompt_hash,
                expected_hash=expected.expected_hash,
                scoring_input_hash=expected.scoring_input_hash,
                request_config_hash=expected.request_config_hash,
                scorer_config_hash=expected.scorer_config_hash,
                fixture_generation_version=campaign.config.fixture_generation_version,
                scheduler_seed=campaign.config.scheduler_seed,
            ),
        )
        assert campaign.validate_attempt(attempt) is None

    def test_validate_mismatching_fixture_input(self):
        campaign = self._make_campaign_with_expected_hashes()
        expected = campaign.config.expected_fixture_hashes["f1"]
        identity = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="low",
            output_mode="text",
            fixture_id="f1",
        )
        attempt = RawAttempt(
            identity=identity,
            status=AttemptStatus.VALID_PASS,
            provenance=Provenance(
                fixture_input_hash="wrong-hash",
                rendered_prompt_hash=expected.rendered_prompt_hash,
                expected_hash=expected.expected_hash,
                scoring_input_hash=expected.scoring_input_hash,
                request_config_hash=expected.request_config_hash,
                scorer_config_hash=expected.scorer_config_hash,
                fixture_generation_version=campaign.config.fixture_generation_version,
                scheduler_seed=campaign.config.scheduler_seed,
            ),
        )
        assert campaign.validate_attempt(attempt) == AttemptStatus.HASH_MISMATCH

    def test_validate_missing_provenance(self):
        campaign = self._make_campaign_with_expected_hashes()
        identity = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="low",
            output_mode="text",
            fixture_id="f1",
        )
        attempt = RawAttempt(identity=identity, status=AttemptStatus.VALID_PASS)
        assert campaign.validate_attempt(attempt) == AttemptStatus.HASH_MISMATCH

    def test_classify_attempts_updates_status(self):
        campaign = self._make_campaign_with_expected_hashes()
        identity = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="low",
            output_mode="text",
            fixture_id="f1",
        )
        attempt = RawAttempt(
            identity=identity,
            status=AttemptStatus.VALID_PASS,
            provenance=Provenance(
                fixture_input_hash="wrong-hash",
                rendered_prompt_hash="rendered",
                expected_hash="expected",
            ),
        )
        campaign.raw_attempts.append(attempt)
        campaign.classify_attempts()
        assert attempt.status == AttemptStatus.HASH_MISMATCH


class TestCampaignReport:
    """Tests for the versioned campaign report schema."""

    def test_roundtrip(self):
        from gitbench.harness.campaign import CAMPAIGN_REPORT_SCHEMA_VERSION

        campaign = make_campaign(
            campaign_id="cmp-report",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=3,
        )
        report = CampaignReport(
            version=CAMPAIGN_REPORT_SCHEMA_VERSION,
            schema_version=CAMPAIGN_REPORT_SCHEMA_VERSION,
            generated_at="2026-06-13T12:00:00+00:00",
            campaign=campaign,
            model_summaries=[
                ModelCampaignSummary(
                    model_id="m1",
                    planned_trials=3,
                    completed_trials=3,
                    valid_attempts=3,
                    passing_attempts=3,
                    mean_success_rate=1.0,
                    pass_any_at_n={1: True, 3: True},
                ),
            ],
            benchmark_summaries=[
                BenchmarkCampaignSummary(
                    benchmark="default",
                    planned_trials=3,
                    completed_trials=3,
                    valid_attempts=3,
                    passing_attempts=3,
                    mean_success_rate=1.0,
                    pass_any_at_n={1: True, 3: True},
                ),
            ],
        )

        data = report.to_dict()
        assert data["version"] == CAMPAIGN_REPORT_SCHEMA_VERSION
        assert data["campaign"]["campaign_id"] == "cmp-report"
        assert "mean_success_rate" in data["model_summaries"][0]
        assert "pass_any_at_n" in data["model_summaries"][0]
        assert "pass_at_k" not in data["model_summaries"][0]

        reconstructed = CampaignReport.from_dict(data)
        assert reconstructed.campaign.campaign_id == "cmp-report"
        assert reconstructed.model_summaries[0].mean_success_rate == 1.0


class TestComputeFixtureAggregates:
    """Fixture-level reliability aggregate computation."""

    def _make_attempt(
        self,
        fixture_id: str,
        trial_index: int,
        passed: bool,
        status=None,
    ):
        from gitbench.harness.campaign import AttemptIdentity, RawAttempt
        if status is None:
            from gitbench.harness.campaign import AttemptStatus
            status = AttemptStatus.VALID_PASS if passed else AttemptStatus.VALID_FAIL
        identity = AttemptIdentity(
            campaign_id="cmp-agg",
            trial_index=trial_index,
            model_id="m1",
            reasoning_effort="none",
            output_mode="text",
            fixture_id=fixture_id,
        )
        return RawAttempt(
            identity=identity,
            status=status,
            passed=passed,
        )

    def test_stable_pass(self):
        from gitbench.harness.campaign import (
            FixtureReliability,
            compute_fixture_aggregates,
            make_campaign,
        )
        campaign = make_campaign(
            campaign_id="cmp-agg",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=3,
        )
        campaign.raw_attempts = [
            self._make_attempt("f1", 1, True),
            self._make_attempt("f1", 2, True),
            self._make_attempt("f1", 3, True),
        ]
        aggregates = compute_fixture_aggregates(campaign)
        assert len(aggregates) == 1
        agg = aggregates[0]
        assert agg.reliability_classification == FixtureReliability.STABLE_PASS
        assert agg.mean_success_rate == 1.0
        assert agg.pass_any_at_n[3] is True

    def test_flaky(self):
        from gitbench.harness.campaign import (
            FixtureReliability,
            compute_fixture_aggregates,
            make_campaign,
        )
        campaign = make_campaign(
            campaign_id="cmp-agg",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=3,
        )
        campaign.raw_attempts = [
            self._make_attempt("f1", 1, True),
            self._make_attempt("f1", 2, False),
            self._make_attempt("f1", 3, True),
        ]
        aggregates = compute_fixture_aggregates(campaign)
        agg = aggregates[0]
        assert agg.reliability_classification == FixtureReliability.FLAKY
        assert agg.mean_success_rate == round(2 / 3, 4)

    def test_operational_exclusion(self):
        from gitbench.harness.campaign import (
            AttemptStatus,
            compute_fixture_aggregates,
            make_campaign,
        )
        campaign = make_campaign(
            campaign_id="cmp-agg",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        campaign.raw_attempts = [
            self._make_attempt("f1", 1, False, AttemptStatus.INFRASTRUCTURE_FAILURE),
            self._make_attempt("f1", 2, True),
        ]
        aggregates = compute_fixture_aggregates(campaign)
        agg = aggregates[0]
        assert agg.valid_attempts == 1
        assert agg.excluded_attempts == 1
        assert agg.mean_success_rate == 1.0
        assert agg.incomplete is True
