"""Executable checks for the GitBench report artifact contract."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any


REQUIRED_TOP_LEVEL_SECTIONS: dict[str, type] = {
    "models": list,
    "benchmarks": list,
    "fixtures": dict,
    "fixture_index": dict,
    "model_summaries": dict,
    "model_runtimes": dict,
    "matrix": dict,
    "runs_meta": list,
    "base_model_groups": list,
    "campaigns": list,
}

OPTIONAL_TOP_LEVEL_SECTIONS: dict[str, type] = {
    "model_token_summaries": dict,
    "safety_review": dict,
}

FIXTURE_RESULT_CONTRACT_FIELDS = {
    "output_mode",
    "reasoning_level",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "reasoning_tokens",
    "cost_usd",
    "duration_ms",
    "api_duration_ms",
    "parsed_payload",
    "raw_structured_output",
    "structured_error",
}

CAMPAIGN_CONTRACT_FIELDS = {
    "trials",
    "raw_attempts",
    "fixture_aggregates",
    "model_summaries",
    "benchmark_summaries",
    "resource_summaries",
    "output_modes",
    "safety_summary",
}

RAW_ATTEMPT_CONTRACT_FIELDS = {
    "identity",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "reasoning_tokens",
    "cost_usd",
    "api_duration_ms",
    "safety_state",
    "safety_cost_usd",
}


class ReportArtifactContractError(ValueError):
    """Raised when report data violates the artifact contract."""


def assert_standard_json_serializable(data: Any) -> None:
    """Ensure the report can be written as browser-compatible JSON."""
    try:
        json.dumps(data, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ReportArtifactContractError(
            f"Report artifact is not standard JSON serializable: {exc}"
        ) from exc


def validate_report_json_contract(data: Any) -> None:
    """Validate the canonical compatibility JSON top-level contract."""
    if not isinstance(data, Mapping):
        raise ReportArtifactContractError("Report artifact must be a JSON object.")

    missing = [key for key in REQUIRED_TOP_LEVEL_SECTIONS if key not in data]
    if missing:
        raise ReportArtifactContractError(
            "Report artifact is missing required top-level section(s): "
            + ", ".join(sorted(missing))
        )

    expected_types = {**REQUIRED_TOP_LEVEL_SECTIONS, **OPTIONAL_TOP_LEVEL_SECTIONS}
    for key, expected_type in expected_types.items():
        if key in data and not isinstance(data[key], expected_type):
            raise ReportArtifactContractError(
                f"Report artifact section {key!r} must be {expected_type.__name__}."
            )

    assert_standard_json_serializable(data)


def validate_report_contract_coverage(data: Mapping[str, Any]) -> None:
    """Validate that a contract fixture covers the important report surfaces."""
    validate_report_json_contract(data)
    _validate_fixture_result_coverage(data)
    _validate_campaign_coverage(data)


def _validate_fixture_result_coverage(data: Mapping[str, Any]) -> None:
    for by_benchmark in _mapping_values(data.get("fixtures", {})):
        for results in _mapping_values(by_benchmark):
            for result in _sequence_values(results):
                if not isinstance(result, Mapping):
                    continue
                missing = FIXTURE_RESULT_CONTRACT_FIELDS - set(result)
                if missing:
                    raise ReportArtifactContractError(
                        "Fixture result is missing contract field(s): "
                        + ", ".join(sorted(missing))
                    )
                return
    raise ReportArtifactContractError("Contract coverage requires at least one fixture result.")


def _validate_campaign_coverage(data: Mapping[str, Any]) -> None:
    campaigns = data.get("campaigns", [])
    if not campaigns:
        raise ReportArtifactContractError("Contract coverage requires at least one campaign.")

    campaign = campaigns[0]
    if not isinstance(campaign, Mapping):
        raise ReportArtifactContractError("Campaign entries must be objects.")

    missing = CAMPAIGN_CONTRACT_FIELDS - set(campaign)
    if missing:
        raise ReportArtifactContractError(
            "Campaign is missing contract field(s): " + ", ".join(sorted(missing))
        )

    if not campaign.get("trials"):
        raise ReportArtifactContractError("Campaign coverage requires at least one trial.")
    if not campaign.get("fixture_aggregates"):
        raise ReportArtifactContractError(
            "Campaign coverage requires at least one fixture aggregate."
        )

    raw_attempts = campaign.get("raw_attempts")
    if not raw_attempts:
        raise ReportArtifactContractError("Campaign coverage requires at least one raw attempt.")
    raw_attempt = raw_attempts[0]
    if not isinstance(raw_attempt, Mapping):
        raise ReportArtifactContractError("Raw attempt entries must be objects.")

    missing = RAW_ATTEMPT_CONTRACT_FIELDS - set(raw_attempt)
    if missing:
        raise ReportArtifactContractError(
            "Raw attempt is missing contract field(s): " + ", ".join(sorted(missing))
        )

    identity = raw_attempt.get("identity")
    if not isinstance(identity, Mapping):
        raise ReportArtifactContractError("Raw attempt identity must be an object.")
    for key in ("output_mode", "reasoning_effort"):
        if key not in identity:
            raise ReportArtifactContractError(
                f"Raw attempt identity is missing contract field {key!r}."
            )


def _mapping_values(value: Any) -> Sequence[Any]:
    if isinstance(value, Mapping):
        return list(value.values())
    return []


def _sequence_values(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return []
