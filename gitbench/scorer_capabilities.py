"""Effective scorer behavior metadata for validation and tooling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScorerCapabilities:
    """Behavior exposed by a scorer after benchmark-specific dispatch."""

    known: bool = True
    order_sensitive: bool = True
    dynamic_expected: bool = False
    selection_parser: str | None = None


UNKNOWN_CAPABILITIES = ScorerCapabilities(known=False)
_MISSING_BENCHMARK_NAME = object()


GENERIC_CAPABILITIES: dict[str, ScorerCapabilities] = {
    "similarity": ScorerCapabilities(),
    "exact_match": ScorerCapabilities(),
    "llm_judge": ScorerCapabilities(),
    "structured": ScorerCapabilities(),
    "state_assertions": ScorerCapabilities(order_sensitive=False),
    "unordered_line_set": ScorerCapabilities(
        order_sensitive=False,
        selection_parser="nonempty_line_set",
    ),
    "command_equivalence": ScorerCapabilities(selection_parser="command_sequence"),
    "numeric_exact": ScorerCapabilities(),
    "commit_hash_by_subject": ScorerCapabilities(dynamic_expected=True),
    "json_semantic_equal": ScorerCapabilities(order_sensitive=False),
    "resolved_file_blocks": ScorerCapabilities(
        order_sensitive=False,
        selection_parser="filename_to_content",
    ),
    "commit_selection": ScorerCapabilities(
        order_sensitive=False,
        selection_parser="commit_subject_lines",
    ),
    "reflog_recovery": ScorerCapabilities(dynamic_expected=True),
    "bisect_regression": ScorerCapabilities(dynamic_expected=True),
}


BENCHMARK_SCORER_CAPABILITIES: dict[tuple[str, str], ScorerCapabilities] = {
    ("branch_cleanup", "exact_match"): ScorerCapabilities(
        order_sensitive=False,
        selection_parser="branch_line_set",
    ),
    ("commit_squash", "commit_selection"): GENERIC_CAPABILITIES["commit_selection"],
    ("git_bisect", "bisect_regression"): GENERIC_CAPABILITIES["bisect_regression"],
    ("reflog", "reflog_recovery"): GENERIC_CAPABILITIES["reflog_recovery"],
}


def capabilities_for_scorer(
    scoring_type: str,
    *,
    benchmark_name: str | object = _MISSING_BENCHMARK_NAME,
) -> ScorerCapabilities:
    """Return effective scorer capabilities for a benchmark/scoring pair."""
    if benchmark_name is _MISSING_BENCHMARK_NAME or benchmark_name is None:
        raise ValueError(
            "capabilities_for_scorer() requires benchmark_name for effective "
            "benchmark scoring behavior; use generic_capabilities_for_scorer() "
            "for explicit generic fixture-only checks."
        )
    if not isinstance(benchmark_name, str) or not benchmark_name.strip():
        raise ValueError("benchmark_name must be a non-empty string")

    benchmark_key = (benchmark_name, scoring_type)
    if benchmark_key in BENCHMARK_SCORER_CAPABILITIES:
        return BENCHMARK_SCORER_CAPABILITIES[benchmark_key]
    return GENERIC_CAPABILITIES.get(scoring_type, UNKNOWN_CAPABILITIES)


def generic_capabilities_for_scorer(scoring_type: str) -> ScorerCapabilities:
    """Return scorer capabilities without benchmark-local behavior."""
    return GENERIC_CAPABILITIES.get(scoring_type, UNKNOWN_CAPABILITIES)
