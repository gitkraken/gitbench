"""Tests for the shared report artifact contract."""

import pytest

from gitbench.report_contract import (
    ReportArtifactContractError,
    assert_standard_json_serializable,
    validate_report_contract_coverage,
    validate_report_json_contract,
)


def test_report_json_contract_accepts_required_top_level_shape():
    validate_report_json_contract(_contract_data())


def test_report_json_contract_rejects_missing_required_section():
    data = _contract_data()
    del data["fixture_index"]

    with pytest.raises(ReportArtifactContractError, match="fixture_index"):
        validate_report_json_contract(data)


def test_report_json_contract_rejects_non_standard_json_values():
    with pytest.raises(ReportArtifactContractError, match="standard JSON"):
        assert_standard_json_serializable({"value": float("nan")})


def test_contract_coverage_exercises_campaigns_attempts_and_result_metadata():
    validate_report_contract_coverage(_contract_data())


def test_contract_coverage_rejects_fixture_results_missing_metadata():
    data = _contract_data()
    del data["fixtures"]["openai/gpt-test:high"]["commit_messages"][0]["output_mode"]

    with pytest.raises(ReportArtifactContractError, match="output_mode"):
        validate_report_contract_coverage(data)


def _contract_data():
    return {
        "models": [
            {
                "name": "openai/gpt-test:high",
                "provider": "openai",
                "baseModel": "gpt-test",
                "reasoningLevel": "high",
                "output_mode": "text",
            }
        ],
        "benchmarks": ["commit_messages"],
        "fixtures": {
            "openai/gpt-test:high": {
                "commit_messages": [
                    {
                        "fixture_id": "f001",
                        "passed": True,
                        "similarity": 1.0,
                        "error": None,
                        "model_output": "feat: add contract",
                        "reasoning_level": "high",
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "total_tokens": 15,
                        "reasoning_tokens": 2,
                        "cost_usd": 0.01,
                        "duration_ms": 25.0,
                        "api_duration_ms": 12.5,
                        "purpose": "contract coverage",
                        "difficulty": "easy",
                        "tags": ["contract"],
                        "output_mode": "text",
                        "parsed_payload": None,
                        "raw_structured_output": None,
                        "structured_error": None,
                    }
                ]
            }
        },
        "fixture_index": {
            "commit_messages/f001": {
                "id": "f001",
                "benchmark": "commit_messages",
                "prompt": "prompt",
                "expected": "expected",
                "description": "description",
                "setup": [],
                "purpose": "contract coverage",
                "difficulty": "easy",
                "tags": ["contract"],
            }
        },
        "model_summaries": {
            "openai/gpt-test:high": {
                "total_runs": 1,
                "total_fixtures": 1,
                "total_passed": 1,
                "pass_at_k": 1.0,
                "total_cost_usd": 0.01,
                "avg_cost_usd": 0.01,
            }
        },
        "model_runtimes": {
            "openai/gpt-test:high": {
                "total_ms": 12.5,
                "avg_ms": 12.5,
                "min_ms": 12.5,
                "max_ms": 12.5,
                "fixture_count": 1,
            }
        },
        "matrix": {
            "openai/gpt-test:high": {
                "commit_messages": {
                    "pass_at_k": 1.0,
                    "total": 1,
                    "passed": 1,
                    "avg_similarity": 1.0,
                }
            }
        },
        "runs_meta": [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "model": "openai/gpt-test:high",
                "output_mode": "text",
                "profile": "default",
                "git_sha": "abc123",
                "benchmark_suite_version": "0.1.0",
                "reasoning_level": "high",
            }
        ],
        "base_model_groups": [
            {
                "provider": "openai",
                "baseModel": "gpt-test",
                "levels": [
                    {
                        "level": "high",
                        "modelName": "openai/gpt-test:high",
                        "output_mode": "text",
                        "pass_at_k": 1.0,
                        "total_cost_usd": 0.01,
                    }
                ],
            }
        ],
        "campaigns": [
            {
                "campaign_id": "cmp-contract",
                "created_at": "2026-06-01T00:00:00Z",
                "config_hash": "abc",
                "state": "complete",
                "planned_attempts": 1,
                "completed_attempts": 1,
                "valid_attempts": 1,
                "passing_attempts": 1,
                "excluded_attempts": 0,
                "publication_state": "published",
                "legacy": False,
                "benchmark_ids": ["commit_messages"],
                "model_ids": ["openai/gpt-test:high"],
                "output_modes": ["text"],
                "planned_trial_count": 1,
                "trials": [
                    {
                        "trial_index": 1,
                        "planned_attempts": 1,
                        "completed_attempts": 1,
                        "valid_attempts": 1,
                        "passing_attempts": 1,
                        "excluded_attempts": 0,
                        "complete": True,
                    }
                ],
                "raw_attempts": [
                    {
                        "identity": {
                            "campaign_id": "cmp-contract",
                            "trial_index": 1,
                            "model_id": "openai/gpt-test:high",
                            "reasoning_effort": "high",
                            "output_mode": "text",
                            "benchmark": "commit_messages",
                            "fixture_id": "f001",
                        },
                        "status": "valid_pass",
                        "passed": True,
                        "similarity": 1.0,
                        "error": None,
                        "model_output": "feat: add contract",
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "total_tokens": 15,
                        "reasoning_tokens": 2,
                        "cost_usd": 0.01,
                        "api_duration_ms": 12.5,
                        "safety_state": "reviewed",
                        "safety_cost_usd": 0.001,
                    }
                ],
                "fixture_aggregates": [
                    {
                        "benchmark": "commit_messages",
                        "fixture_id": "f001",
                        "model_id": "openai/gpt-test:high",
                        "reasoning_effort": "high",
                        "output_mode": "text",
                        "planned_trials": 1,
                        "completed_trials": 1,
                        "valid_attempts": 1,
                        "passing_attempts": 1,
                        "failing_attempts": 0,
                        "excluded_attempts": 0,
                        "mean_success_rate": 1.0,
                        "pass_any_at_n": {"1": True},
                        "reliability_classification": "stable_pass",
                        "incomplete": False,
                    }
                ],
                "model_summaries": [],
                "benchmark_summaries": [],
                "resource_summaries": [
                    {
                        "scope": "campaign",
                        "total_cost_usd": 0.01,
                        "total_input_tokens": 10,
                        "total_output_tokens": 5,
                        "total_tokens": 15,
                        "total_reasoning_tokens": 2,
                        "total_api_duration_ms": 12.5,
                        "partial_pricing": False,
                    }
                ],
                "safety_summary": {
                    "reviewed": 1,
                    "sanitized": 0,
                    "blocked": 0,
                    "pending": 0,
                },
            }
        ],
        "safety_review": {"status": "complete", "policy_version": "test"},
    }
