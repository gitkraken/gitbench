"""Tests for gitbench/export.py."""

import csv
import io
from gitbench.export import (
    export_csv,
    export_artificialanalysis,
    FORMAT_REGISTRY,
    get_available_formats,
)
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
