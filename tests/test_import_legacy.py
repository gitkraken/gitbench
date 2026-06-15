"""Tests for importing historical artifacts as one-trial legacy campaigns."""

from gitbench.harness.campaign import AttemptStatus, CampaignState, FixtureReliability
from gitbench.harness.import_legacy import import_legacy_campaign


class TestImportLegacyCampaign:
    """Historical envelopes become legacy campaigns without stability inference."""

    def _build_envelope(self) -> dict:
        return {
            "version": 1,
            "benchmark_suite_version": "0.3.0",
            "timestamp": "2026-05-01T00:00:00+00:00",
            "model": "mock",
            "output_mode": "text",
            "results": [
                {
                    "benchmark": "commit_messages",
                    "total": 2,
                    "passed": 1,
                    "scores": [
                        {
                            "fixture_id": "commit_messages/f001",
                            "passed": True,
                            "similarity": 0.9,
                            "model_output": "feat: add login",
                        },
                        {
                            "fixture_id": "commit_messages/f002",
                            "passed": False,
                            "similarity": 0.3,
                            "model_output": "bad message",
                            "error": "too short",
                        },
                    ],
                }
            ],
        }

    def test_legacy_flag_set(self):
        envelope = self._build_envelope()
        campaign = import_legacy_campaign(envelope, campaign_id="cmp-legacy")
        assert campaign.legacy is True
        assert campaign.config.planned_trial_count == 1

    def test_state_is_incomplete(self):
        envelope = self._build_envelope()
        campaign = import_legacy_campaign(envelope)
        assert campaign.state == CampaignState.INCOMPLETE

    def test_attempts_are_quality_outcomes(self):
        envelope = self._build_envelope()
        campaign = import_legacy_campaign(envelope)
        assert len(campaign.raw_attempts) == 2
        assert all(a.status.is_quality_outcome() for a in campaign.raw_attempts)
        assert campaign.raw_attempts[0].status == AttemptStatus.VALID_PASS
        assert campaign.raw_attempts[1].status == AttemptStatus.VALID_FAIL

    def test_no_stability_inferred(self):
        envelope = self._build_envelope()
        campaign = import_legacy_campaign(envelope)
        for agg in campaign.fixture_aggregates:
            # Single-trial legacy imports cannot infer stable/flaky.
            assert agg.reliability_classification != FixtureReliability.FLAKY



class TestImportFromAggregate:
    """Legacy aggregate reports map to one-trial legacy campaigns."""

    def test_aggregate_migration(self):
        from gitbench.harness.import_legacy import import_legacy_campaigns_from_aggregate

        data = {
            "runs_meta": [
                {
                    "model_name": "mock",
                    "output_mode": "text",
                    "timestamp": "2026-05-01T00:00:00+00:00",
                }
            ],
            "fixtures": {
                "mock": {
                    "commit_messages": [
                        {
                            "fixture_id": "commit_messages/f001",
                            "passed": True,
                            "similarity": 0.9,
                            "model_output": "feat: add login",
                        },
                        {
                            "fixture_id": "commit_messages/f002",
                            "passed": False,
                            "similarity": 0.3,
                            "model_output": "bad",
                        },
                    ]
                }
            },
        }
        campaigns = import_legacy_campaigns_from_aggregate(data)
        assert len(campaigns) == 1
        campaign = campaigns[0]
        assert campaign.legacy is True
        assert campaign.config.planned_trial_count == 1
        assert len(campaign.raw_attempts) == 2
        assert campaign.state.value == "incomplete"
