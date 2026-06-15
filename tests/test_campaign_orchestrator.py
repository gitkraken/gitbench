"""Tests for campaign orchestration."""

from gitbench.harness.benchmark import Benchmark
from gitbench.harness.campaign import CampaignState, FixtureReliability
from gitbench.harness.campaign_orchestrator import plan_campaign, write_campaign_manifest
from gitbench.version import BENCHMARK_SUITE_VERSION


class TestPlanCampaign:
    """Tests for planning campaigns from resolved CLI inputs."""

    def test_plan_campaign(self):
        from gitbench.benchmarks.reflog import ReflogBenchmark

        benchmark = ReflogBenchmark()
        fixtures = benchmark.load_fixtures()
        assert fixtures

        campaign = plan_campaign(
            campaign_id="cmp-test-1",
            benchmarks=[("reflog", benchmark)],
            models=[("mock", "none", {})],
            output_modes=["text"],
            planned_trial_count=2,
            fixture_generation_version=BENCHMARK_SUITE_VERSION,
        )

        assert campaign.campaign_id == "cmp-test-1"
        assert campaign.state == CampaignState.PLANNED
        assert campaign.config.planned_trial_count == 2
        assert campaign.config.fixture_generation_version == BENCHMARK_SUITE_VERSION
        assert campaign.config.expected_fixture_hashes
        assert campaign.config_hash == campaign.config.compute_hash()
        # Schedule is attached as a private attribute.
        assert campaign._schedule.planned_attempts == 2 * len(fixtures) * 1 * 1

    def test_plan_campaign_hashes_detect_fixture_change(self):
        from gitbench.benchmarks.reflog import ReflogBenchmark

        benchmark = ReflogBenchmark()
        campaign_first = plan_campaign(
            campaign_id="cmp-hashes-1",
            benchmarks=[("reflog", benchmark)],
            models=[("mock", "none", {})],
            output_modes=["text"],
            planned_trial_count=1,
            fixture_generation_version="0.3.0",
        )
        campaign_second = plan_campaign(
            campaign_id="cmp-hashes-1",
            benchmarks=[("reflog", benchmark)],
            models=[("mock", "none", {})],
            output_modes=["text"],
            planned_trial_count=1,
            fixture_generation_version="0.4.0",
        )
        first_hash = campaign_first.config_hash
        second_hash = campaign_second.config_hash
        assert first_hash != second_hash

    def test_write_campaign_manifest(self, tmp_path):
        from gitbench.benchmarks.reflog import ReflogBenchmark

        benchmark = ReflogBenchmark()
        campaign = plan_campaign(
            campaign_id="cmp-write-1",
            benchmarks=[("reflog", benchmark)],
            models=[("mock", "none", {})],
            output_modes=["text"],
            planned_trial_count=1,
            fixture_generation_version=BENCHMARK_SUITE_VERSION,
        )
        manifest_path = write_campaign_manifest(campaign, results_dir=str(tmp_path))
        assert manifest_path.exists()
        assert manifest_path.name == "campaign.json"
        assert (tmp_path / "cmp-write-1" / "campaign.json").exists()
