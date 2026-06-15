"""Tests for campaign scheduling."""

import pytest

from gitbench.harness.campaign import AttemptIdentity
from gitbench.harness.scheduler import CampaignSchedule, build_schedule


class TestBuildSchedule:
    """Tests for schedule construction."""

    def test_schedule_counts(self):
        schedule = build_schedule(
            campaign_id="cmp-1",
            fixture_ids=["f1", "f2"],
            models=[("m1", "low"), ("m2", "high")],
            output_modes=["text", "json_schema"],
            planned_trial_count=3,
            seed=42,
        )
        assert schedule.campaign_id == "cmp-1"
        assert schedule.planned_trial_count == 3
        assert schedule.planned_attempts == 3 * 2 * 2 * 2
        assert len(schedule.trial_identities) == 3
        for trial_index in range(1, 4):
            assert len(schedule.by_trial(trial_index)) == 2 * 2 * 2

    def test_one_trial_schedule(self):
        schedule = build_schedule(
            campaign_id="cmp-1",
            fixture_ids=["f1"],
            models=[("m1", "low")],
            output_modes=["text"],
            planned_trial_count=1,
            seed=42,
        )
        assert schedule.planned_attempts == 1
        identity = schedule.identities[0]
        assert identity.trial_index == 1
        assert identity.model_id == "m1"
        assert identity.output_mode == "text"
        assert identity.fixture_id == "f1"

    def test_schedule_reproducible(self):
        first = build_schedule(
            campaign_id="cmp-1",
            fixture_ids=["f1", "f2"],
            models=[("m1", "low"), ("m2", "high")],
            output_modes=["text", "json_schema"],
            planned_trial_count=3,
            seed=42,
        )
        second = build_schedule(
            campaign_id="cmp-1",
            fixture_ids=["f1", "f2"],
            models=[("m1", "low"), ("m2", "high")],
            output_modes=["text", "json_schema"],
            planned_trial_count=3,
            seed=42,
        )
        assert [i.to_dict() for i in first.identities] == [
            i.to_dict() for i in second.identities
        ]

    def test_trial_ordering_differs(self):
        schedule = build_schedule(
            campaign_id="cmp-1",
            fixture_ids=["f1", "f2"],
            models=[("m1", "low"), ("m2", "high")],
            output_modes=["text", "json_schema"],
            planned_trial_count=3,
            seed=42,
        )
        first_order = [i.model_id for i in schedule.by_trial(1)]
        second_order = [i.model_id for i in schedule.by_trial(2)]
        assert first_order != second_order

    def test_requires_positive_trials(self):
        with pytest.raises(ValueError):
            build_schedule(
                campaign_id="cmp-1",
                fixture_ids=["f1"],
                models=[("m1", "low")],
                output_modes=["text"],
                planned_trial_count=0,
            )

    def test_requires_inputs(self):
        with pytest.raises(ValueError):
            build_schedule(
                campaign_id="cmp-1",
                fixture_ids=[],
                models=[("m1", "low")],
                output_modes=["text"],
                planned_trial_count=1,
            )
        with pytest.raises(ValueError):
            build_schedule(
                campaign_id="cmp-1",
                fixture_ids=["f1"],
                models=[],
                output_modes=["text"],
                planned_trial_count=1,
            )
        with pytest.raises(ValueError):
            build_schedule(
                campaign_id="cmp-1",
                fixture_ids=["f1"],
                models=[("m1", "low")],
                output_modes=[],
                planned_trial_count=1,
            )

    def test_identity_uniqueness(self):
        schedule = build_schedule(
            campaign_id="cmp-1",
            fixture_ids=["f1", "f2"],
            models=[("m1", "low"), ("m2", "high")],
            output_modes=["text", "json_schema"],
            planned_trial_count=3,
            seed=42,
        )
        keys = {
            (
                i.trial_index,
                i.model_id,
                i.reasoning_effort,
                i.output_mode,
                i.fixture_id,
            )
            for i in schedule.identities
        }
        assert len(keys) == len(schedule.identities)
