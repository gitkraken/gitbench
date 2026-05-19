"""Tests for result doctoring utilities."""

from gitbench.result_doctoring import (
    build_rerun_plan,
    find_timestamped_result_files,
    format_dry_run_summary,
    is_doctorable_error,
    replace_scores_and_recompute,
)


def _combined_payload():
    return {
        "benchmark_suite_version": "0.1.0",
        "summary": {
            "total_profiles": 1,
            "total_models": 1,
            "total_fixtures": 3,
            "total_passed": 1,
            "overall_pass_at_k": 0.3333,
        },
        "profiles": [
            {
                "profile": "local",
                "summary": {
                    "total_models": 1,
                    "total_fixtures": 3,
                    "total_passed": 1,
                    "overall_pass_at_k": 0.3333,
                },
                "models": [
                    {
                        "model": "mock",
                        "summary": {
                            "total_benchmarks": 1,
                            "total_fixtures": 3,
                            "total_passed": 1,
                            "overall_pass_at_k": 0.3333,
                        },
                        "results": [
                            {
                                "benchmark": "commit_messages",
                                "total": 3,
                                "passed": 1,
                                "pass_at_k": 0.3333,
                                "errors": 2,
                                "total_duration_ms": 30,
                                "scores": [
                                    {
                                        "fixture_id": "f001",
                                        "passed": True,
                                        "similarity": 1.0,
                                        "model_output": "ok",
                                        "error": None,
                                        "duration_ms": 10,
                                    },
                                    {
                                        "fixture_id": "f002",
                                        "passed": False,
                                        "similarity": 0.0,
                                        "model_output": "",
                                        "error": "Model call timed out after 30s",
                                        "duration_ms": 10,
                                    },
                                    {
                                        "fixture_id": "f003",
                                        "passed": False,
                                        "similarity": 0.0,
                                        "model_output": "bad",
                                        "error": "expected got mismatch",
                                        "duration_ms": 10,
                                    },
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }


def test_doctorable_and_non_doctorable_errors():
    doctorable = [
        "[Errno 24] Too many open files",
        "Model call timed out after 30s",
        "RateLimitError: slow down",
        "APITimeoutError",
        "APIConnectionError",
        "InternalServerError",
        "provider returned 429",
        "provider returned HTTP 429",
        "500 server error",
        "HTTP 500 server error",
        "502 bad gateway",
        "503 unavailable",
        "504 gateway timeout",
    ]
    for error in doctorable:
        assert is_doctorable_error(error)

    assert not is_doctorable_error("expected 'foo' got 'bar'")
    assert not is_doctorable_error("expected score 500 but got 400")
    assert not is_doctorable_error("validated fixture_500 incorrectly")
    assert not is_doctorable_error("extra selected commit messages")
    assert not is_doctorable_error("command-equivalence failure")
    assert not is_doctorable_error(None)


def test_rerun_plan_groups_by_profile_model_benchmark_and_summarizes():
    payload = _combined_payload()
    payload["profiles"][0]["models"][0]["results"][0]["scores"].append(
        {
            "fixture_id": "f004",
            "passed": False,
            "similarity": 0.0,
            "model_output": "",
            "error": "[Errno 24] Too many open files",
        }
    )

    plan = build_rerun_plan(payload)

    assert plan.doctorable_count == 2
    assert len(plan.targets) == 1
    assert plan.targets[0].profile == "local"
    assert plan.targets[0].model == "mock"
    assert plan.targets[0].benchmark == "commit_messages"
    assert plan.targets[0].fixture_ids == ("f002", "f004")

    summary = format_dry_run_summary(plan)
    assert "Doctorable failed fixtures: 2" in summary
    assert "Affected models: 1" in summary
    assert "Affected model/benchmark pairs: 1" in summary
    assert "Too many open files: 1" in summary


def test_replace_scores_preserves_non_targets_and_recomputes_summaries():
    payload = _combined_payload()
    plan = build_rerun_plan(payload)
    original_f001 = dict(
        payload["profiles"][0]["models"][0]["results"][0]["scores"][0]
    )
    original_f003 = dict(
        payload["profiles"][0]["models"][0]["results"][0]["scores"][2]
    )

    replace_scores_and_recompute(
        payload,
        plan.targets[0],
        {
            "benchmark": "commit_messages",
            "total": 1,
            "passed": 1,
            "pass_at_k": 1.0,
            "errors": 0,
            "scores": [
                {
                    "fixture_id": "f002",
                    "passed": True,
                    "similarity": 1.0,
                    "model_output": "fixed",
                    "error": None,
                    "duration_ms": 5,
                }
            ],
        },
    )

    result = payload["profiles"][0]["models"][0]["results"][0]
    assert result["scores"][0] == original_f001
    assert result["scores"][2] == original_f003
    assert result["scores"][1]["model_output"] == "fixed"
    assert result["passed"] == 2
    assert result["errors"] == 1
    assert result["pass_at_k"] == 0.6667
    assert result["total_duration_ms"] == 25
    assert payload["summary"]["total_passed"] == 2
    assert payload["summary"]["overall_pass_at_k"] == 0.6667


def test_find_timestamped_result_files_returns_all_timestamped_results(tmp_path):
    ignored = tmp_path / "gitbench-results/a/results-v0.1.0.json"
    ignored_z = tmp_path / "gitbench-results/scratchZ/results-v0.1.0.json"
    older = tmp_path / "gitbench-results/20260101T000000Z/results-v0.1.0.json"
    latest = tmp_path / "gitbench-results/20260102T000000Z/results-v0.1.0.json"
    ignored.parent.mkdir(parents=True)
    ignored_z.parent.mkdir(parents=True)
    older.parent.mkdir(parents=True)
    latest.parent.mkdir(parents=True)
    ignored.write_text("{}")
    ignored_z.write_text("{}")
    older.write_text("{}")
    latest.write_text("{}")

    assert find_timestamped_result_files(tmp_path / "gitbench-results") == [
        older,
        latest,
    ]
