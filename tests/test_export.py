"""Tests for gitbench/export.py."""

import csv
import io
from gitbench.export import (
    export_csv,
    export_artificialanalysis,
    FORMAT_REGISTRY,
    get_available_formats,
)
from gitbench.harness.campaign import AttemptStatus
from gitbench.version import BENCHMARK_SUITE_VERSION


# ── Fixtures ────────────────────────────────────────────────────────────────

ENVELOPE = {
    "version": 1,
    "benchmark_suite_version": BENCHMARK_SUITE_VERSION,
    "timestamp": "2026-05-03T00:00:00+00:00",
    "git_sha": "abc1234",
    "model": "mock",
    "profile": "(inline)",
    "summary": {
        "total_benchmarks": 1,
        "total_fixtures": 2,
        "total_passed": 1,
        "overall_pass_at_k": 0.5,
    },
    "results": [
        {
            "benchmark": "commit_messages",
            "total": 2,
            "passed": 1,
            "pass_at_k": 0.5,
            "scores": [
                {
                    "fixture_id": "f001",
                    "passed": True,
                    "similarity": 0.9,
                    "model_output": "fix: update deps",
                    "error": None,
                },
                {
                    "fixture_id": "f002",
                    "passed": False,
                    "similarity": 0.3,
                    "model_output": "update deps",
                    "error": None,
                },
            ],
            "errors": 0,
        }
    ],
}


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_csv_export_valid_format():
    """export_csv produces parseable CSV with all expected headers."""
    csv_str = export_csv(ENVELOPE)
    reader = csv.DictReader(io.StringIO(csv_str))
    headers = reader.fieldnames
    expected = [
        "benchmark",
        "fixture_id",
        "model",
        "passed",
        "similarity",
        "model_output",
        "error",
        "timestamp",
        "git_sha",
        "profile",
        "benchmark_suite_version",
        "reasoning_level",
    ]
    assert headers == expected, f"Expected {expected}, got {headers}"

    rows = list(reader)
    assert len(rows) == 2, f"Expected 2 rows, got {len(rows)}"

    # Verify values from the first fixture
    assert rows[0]["fixture_id"] == "f001"
    assert rows[0]["passed"] == "1"  # CSV stores as string
    assert rows[0]["similarity"] == "0.9"
    assert rows[0]["model"] == "mock"
    assert rows[0]["git_sha"] == "abc1234"
    assert rows[0]["benchmark_suite_version"] == BENCHMARK_SUITE_VERSION


def test_artificialanalysis_export_fields():
    """export_artificialanalysis includes all expected headers and one row per benchmark."""
    csv_str = export_artificialanalysis(ENVELOPE)
    reader = csv.DictReader(io.StringIO(csv_str))
    headers = reader.fieldnames
    expected = [
        "model",
        "benchmark",
        "score",
        "total",
        "passed",
        "timestamp",
        "git_sha",
        "provider",
        "profile",
        "benchmark_suite_version",
        "reasoning_level",
    ]
    assert headers == expected, f"Expected {expected}, got {headers}"

    rows = list(reader)
    assert len(rows) == 1, f"Expected 1 row (one per benchmark), got {len(rows)}"

    row = rows[0]
    assert row["model"] == "mock"
    assert row["benchmark"] == "commit_messages"
    assert row["score"] == "0.5"  # pass_at_k rounded
    assert row["total"] == "2"
    assert row["passed"] == "1"
    assert row["benchmark_suite_version"] == BENCHMARK_SUITE_VERSION


def test_unknown_format_error():
    """Accessing FORMAT_REGISTRY with an unknown key raises KeyError."""
    unknown = "not_a_format"
    formats = get_available_formats()
    assert unknown not in FORMAT_REGISTRY
    assert unknown not in formats
    try:
        FORMAT_REGISTRY[unknown]
        assert False, "Expected KeyError"
    except KeyError as e:
        # The KeyError references the unknown key that was requested
        assert unknown in str(e), f"Expected KeyError for '{unknown}', got: {e}"
        # Available formats are retrievable via the public API
        assert len(formats) > 0
        assert "csv" in formats
        assert "artificialanalysis" in formats


def test_export_empty_results():
    """Both export functions handle envelopes with zero results gracefully."""
    empty_envelope = {
        "version": 1,
        "timestamp": "2026-05-03T00:00:00+00:00",
        "git_sha": "abc1234",
        "model": "mock",
        "profile": "(inline)",
        "results": [],
    }

    # export_csv
    csv_str = export_csv(empty_envelope)
    reader = csv.DictReader(io.StringIO(csv_str))
    headers = reader.fieldnames
    assert headers is not None
    rows = list(reader)
    assert len(rows) == 0

    # export_artificialanalysis
    aa_str = export_artificialanalysis(empty_envelope)
    reader = csv.DictReader(io.StringIO(aa_str))
    headers = reader.fieldnames
    assert headers is not None
    rows = list(reader)
    assert len(rows) == 0


def test_export_single_fixture():
    """export_csv with one fixture score produces exactly one data row."""
    single_envelope = {
        "version": 1,
        "timestamp": "2026-05-03T00:00:00+00:00",
        "git_sha": "deadbeef",
        "model": "gpt-4",
        "profile": "(inline)",
        "results": [
            {
                "benchmark": "commit_messages",
                "total": 1,
                "passed": 1,
                "pass_at_k": 1.0,
                "scores": [
                    {
                        "fixture_id": "solo",
                        "passed": True,
                        "similarity": 0.95,
                        "model_output": "chore: init",
                        "error": None,
                    },
                ],
                "errors": 0,
            }
        ],
    }

    csv_str = export_csv(single_envelope)
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)

    assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
    row = rows[0]
    assert row["fixture_id"] == "solo"
    assert row["passed"] == "1"
    assert row["similarity"] == "0.95"
    assert row["model_output"] == "chore: init"
    assert row["model"] == "gpt-4"
    assert row["git_sha"] == "deadbeef"


def test_csv_reasoning_level_in_score():
    """CSV row includes reasoning_level from score."""
    envelope = {
        "version": 1,
        "timestamp": "2026-05-03T00:00:00+00:00",
        "git_sha": "abc1234",
        "model": "o3-mini#high",
        "profile": "(inline)",
        "results": [
            {
                "benchmark": "commit_messages",
                "total": 1,
                "passed": 1,
                "pass_at_k": 1.0,
                "scores": [
                    {
                        "fixture_id": "f1",
                        "passed": True,
                        "similarity": 0.9,
                        "model_output": "fix: test",
                        "error": None,
                        "reasoning_level": "high",
                    },
                ],
                "errors": 0,
            }
        ],
    }

    csv_str = export_csv(envelope)
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)
    assert rows[0]["reasoning_level"] == "high"


def test_csv_reasoning_level_absent():
    """CSV reasoning_level is empty string when score has none."""
    envelope = {
        "version": 1,
        "timestamp": "2026-05-03T00:00:00+00:00",
        "git_sha": "abc1234",
        "model": "gpt-4o",
        "profile": "(inline)",
        "results": [
            {
                "benchmark": "commit_messages",
                "total": 1,
                "passed": 1,
                "pass_at_k": 1.0,
                "scores": [
                    {
                        "fixture_id": "f1",
                        "passed": True,
                        "similarity": 0.9,
                        "model_output": "fix: test",
                        "error": None,
                    },
                ],
                "errors": 0,
            }
        ],
    }

    csv_str = export_csv(envelope)
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)
    assert rows[0]["reasoning_level"] == ""


def test_artificialanalysis_reasoning_level():
    """artificialanalyanalysis CSV includes reasoning_level from first score."""
    envelope = {
        "version": 1,
        "timestamp": "2026-05-03T00:00:00+00:00",
        "git_sha": "abc1234",
        "model": "o3-mini#medium",
        "profile": "(inline)",
        "results": [
            {
                "benchmark": "commit_messages",
                "total": 1,
                "passed": 1,
                "pass_at_k": 1.0,
                "scores": [
                    {
                        "fixture_id": "f1",
                        "passed": True,
                        "similarity": 0.9,
                        "model_output": "fix: test",
                        "error": None,
                        "reasoning_level": "medium",
                    },
                ],
                "errors": 0,
            }
        ],
    }

    csv_str = export_artificialanalysis(envelope)
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)
    assert rows[0]["reasoning_level"] == "medium"



class TestCampaignReportExport:
    """Export campaign reports in the new JSON schema."""

    def test_export_campaign_report_structure(self):
        from gitbench.harness.campaign import (
            AttemptIdentity,
            RawAttempt,
            Trial,
            make_campaign,
        )
        from gitbench.export import build_campaign_report

        campaign = make_campaign(
            campaign_id="cmp-export",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=2,
        )
        campaign.trials = [
            Trial(
                trial_index=1,
                planned_attempts=1,
                attempt_identities=[
                    AttemptIdentity(
                        campaign_id=campaign.campaign_id,
                        trial_index=1,
                        model_id="m1",
                        reasoning_effort="none",
                        output_mode="text",
                        fixture_id="f1",
                    )
                ],
            ),
            Trial(
                trial_index=2,
                planned_attempts=1,
                attempt_identities=[
                    AttemptIdentity(
                        campaign_id=campaign.campaign_id,
                        trial_index=2,
                        model_id="m1",
                        reasoning_effort="none",
                        output_mode="text",
                        fixture_id="f1",
                    )
                ],
            ),
        ]
        campaign.raw_attempts = [
            RawAttempt(
                identity=campaign.trials[0].attempt_identities[0],
                status=AttemptStatus.VALID_PASS,
                passed=True,
            ),
            RawAttempt(
                identity=campaign.trials[1].attempt_identities[0],
                status=AttemptStatus.VALID_PASS,
                passed=True,
            ),
        ]
        report = build_campaign_report(campaign)
        assert report.version == 2
        assert report.schema_version == 2
        assert report.campaign.state.value == "complete"
        assert report.model_summaries
        assert report.campaign.fixture_aggregates

    def test_export_campaign_report_json(self):
        import json
        from gitbench.harness.campaign import (
            AttemptIdentity,
            RawAttempt,
            Trial,
            make_campaign,
        )
        from gitbench.export import export_campaign_report

        campaign = make_campaign(
            campaign_id="cmp-export-json",
            fixture_ids=["f1"],
            model_ids=["m1"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        id1 = AttemptIdentity(
            campaign_id=campaign.campaign_id,
            trial_index=1,
            model_id="m1",
            reasoning_effort="none",
            output_mode="text",
            fixture_id="f1",
        )
        campaign.trials = [Trial(trial_index=1, planned_attempts=1, attempt_identities=[id1])]
        campaign.raw_attempts = [
            RawAttempt(identity=id1, status=AttemptStatus.VALID_PASS, passed=True),
        ]
        json_str = export_campaign_report(campaign)
        data = json.loads(json_str)
        assert data["version"] == 2
        assert data["campaign"]["campaign_id"] == "cmp-export-json"


def test_compatibility_report_from_legacy_envelope():
    """A legacy artifact produces a campaign report marked legacy without stability."""
    from gitbench.export import build_compatibility_report
    from gitbench.harness.campaign import FixtureReliability

    envelope = {
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
                    },
                ],
            }
        ],
    }
    report = build_compatibility_report(envelope)
    assert report.campaign.legacy is True
    assert report.campaign.config.planned_trial_count == 1
    assert all(
        agg.reliability_classification == FixtureReliability.UNKNOWN
        for agg in report.campaign.fixture_aggregates
    )
    assert any(ms.model_id == "mock" for ms in report.model_summaries)
