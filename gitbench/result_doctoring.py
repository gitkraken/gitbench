"""Utilities for selectively repairing transient failures in result files."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DOCTORABLE_ERROR_PATTERNS = (
    "[Errno 24] Too many open files",
    "Model call timed out after",
    "RateLimitError",
    "APITimeoutError",
    "APIConnectionError",
    "InternalServerError",
)

_HTTP_STATUS_BEFORE = r"(?:api|http|provider|response|returned|server|status)"
_HTTP_STATUS_AFTER = (
    r"(?:bad gateway|error|gateway timeout|rate limit|response|server|"
    r"status|timeout|too many requests|unavailable)"
)

DOCTORABLE_HTTP_STATUS_PATTERNS = tuple(
    (
        status,
        re.compile(
            rf"\b{_HTTP_STATUS_BEFORE}\b[^\n]{{0,80}}\b{status}\b|"
            rf"\b{status}\b[^\n]{{0,80}}\b{_HTTP_STATUS_AFTER}\b",
            re.IGNORECASE,
        ),
    )
    for status in ("429", "500", "502", "503", "504")
)
RESULT_TIMESTAMP_DIR_RE = re.compile(r"^\d{8}T\d{6}Z$")


@dataclass(frozen=True)
class RerunTarget:
    """A grouped set of fixture IDs to rerun for one profile/model/benchmark."""

    profile: str
    model: str
    benchmark: str
    fixture_ids: tuple[str, ...]


@dataclass
class RerunPlan:
    """Doctoring plan derived from a result payload."""

    targets: list[RerunTarget]
    pattern_counts: dict[str, int] = field(default_factory=dict)

    @property
    def doctorable_count(self) -> int:
        return sum(len(target.fixture_ids) for target in self.targets)

    @property
    def affected_models(self) -> set[tuple[str, str]]:
        return {(target.profile, target.model) for target in self.targets}

    @property
    def affected_model_benchmarks(self) -> set[tuple[str, str, str]]:
        return {
            (target.profile, target.model, target.benchmark)
            for target in self.targets
        }


def doctorable_error_pattern(error: str | None) -> str | None:
    """Return the matching doctorable pattern for an error string."""
    if not error:
        return None
    for pattern in DOCTORABLE_ERROR_PATTERNS:
        if pattern in error:
            return pattern
    for pattern, regex in DOCTORABLE_HTTP_STATUS_PATTERNS:
        if regex.search(error):
            return pattern
    return None


def is_doctorable_error(error: str | None) -> bool:
    """Whether an error string represents a transient doctorable failure."""
    return doctorable_error_pattern(error) is not None


def find_latest_result_files(results_root: str | Path = "gitbench-results") -> list[Path]:
    """Find JSON result files under gitbench-results."""
    root = Path(results_root)
    return sorted(path for path in root.glob("**/*.json") if path.is_file())


def load_result_payload(path: str | Path) -> dict[str, Any]:
    """Load a result JSON payload."""
    return json.loads(Path(path).read_text())


def write_result_payload(path: str | Path, payload: dict[str, Any]) -> Path:
    """Write a result JSON payload."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2))
    return output_path


def build_rerun_plan(payload: dict[str, Any]) -> RerunPlan:
    """Scan a result payload for doctorable scores grouped by rerun target."""
    grouped: dict[tuple[str, str, str], list[str]] = {}
    pattern_counts: dict[str, int] = {}

    for profile_name, model_entry, result in _iter_model_results(payload):
        model_name = str(model_entry.get("model", ""))
        benchmark_name = str(result.get("benchmark", ""))
        for score in result.get("scores", []):
            pattern = doctorable_error_pattern(score.get("error"))
            if not pattern:
                continue
            key = (profile_name, model_name, benchmark_name)
            grouped.setdefault(key, []).append(str(score.get("fixture_id", "")))
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

    targets = [
        RerunTarget(profile, model, benchmark, tuple(fixture_ids))
        for (profile, model, benchmark), fixture_ids in sorted(grouped.items())
    ]
    return RerunPlan(targets=targets, pattern_counts=pattern_counts)


def format_dry_run_summary(plan: RerunPlan) -> str:
    """Format a human-readable dry-run summary."""
    lines = [
        "Doctor dry run",
        f"Doctorable failed fixtures: {plan.doctorable_count}",
        f"Affected models: {len(plan.affected_models)}",
        f"Affected model/benchmark pairs: {len(plan.affected_model_benchmarks)}",
        "Error patterns:",
    ]
    if plan.pattern_counts:
        for pattern, count in sorted(plan.pattern_counts.items()):
            lines.append(f"  - {pattern}: {count}")
    else:
        lines.append("  - none: 0")
    return "\n".join(lines)


def replace_scores_and_recompute(
    payload: dict[str, Any],
    target: RerunTarget,
    replacement_result: dict[str, Any],
) -> None:
    """Replace target score objects from a benchmark rerun and recompute summaries."""
    replacements = {
        str(score.get("fixture_id")): score
        for score in replacement_result.get("scores", [])
    }
    expected = set(target.fixture_ids)
    missing = sorted(expected - set(replacements))
    if missing:
        raise ValueError(
            f"Rerun for {target.model}/{target.benchmark} did not return "
            f"fixture id(s): {', '.join(missing)}"
        )

    result = _find_benchmark_result(payload, target)
    for index, score in enumerate(result.get("scores", [])):
        fixture_id = str(score.get("fixture_id"))
        if fixture_id in expected:
            result["scores"][index] = replacements[fixture_id]

    _recompute_benchmark_result(result)
    recompute_summaries(payload)


def recompute_summaries(payload: dict[str, Any]) -> None:
    """Recompute benchmark, model, profile, and top-level summaries in-place."""
    for _profile_name, _model_entry, result in _iter_model_results(payload):
        _recompute_benchmark_result(result)

    profiles = payload.get("profiles")
    if isinstance(profiles, list):
        for profile_entry in profiles:
            for model_entry in profile_entry.get("models", []):
                _recompute_model_summary(model_entry)
            _recompute_profile_summary(profile_entry)
        _recompute_top_summary(payload)
        return

    if isinstance(payload.get("models"), list):
        for model_entry in payload["models"]:
            _recompute_model_summary(model_entry)
        _recompute_models_top_summary(payload)
        return

    if isinstance(payload.get("results"), list):
        _recompute_model_summary(payload)
        return

    if "scores" in payload:
        _recompute_benchmark_result(payload)


def _iter_model_results(payload: dict[str, Any]):
    profiles = payload.get("profiles")
    if isinstance(profiles, list):
        for profile_entry in profiles:
            profile_name = str(profile_entry.get("profile", ""))
            for model_entry in profile_entry.get("models", []):
                for result in model_entry.get("results", []):
                    yield profile_name, model_entry, result
        return

    models = payload.get("models")
    if isinstance(models, list):
        profile_name = str(payload.get("profile", ""))
        for model_entry in models:
            for result in model_entry.get("results", []):
                yield profile_name, model_entry, result
        return

    if isinstance(payload.get("results"), list):
        model_entry = payload
        profile_name = str(payload.get("profile", ""))
        for result in payload.get("results", []):
            yield profile_name, model_entry, result
        return

    if "scores" in payload:
        yield str(payload.get("profile", "")), payload, payload


def _find_benchmark_result(payload: dict[str, Any], target: RerunTarget) -> dict[str, Any]:
    for profile_name, model_entry, result in _iter_model_results(payload):
        if (
            profile_name == target.profile
            and str(model_entry.get("model", "")) == target.model
            and str(result.get("benchmark", "")) == target.benchmark
        ):
            return result
    raise ValueError(
        f"Could not find result for profile={target.profile!r}, "
        f"model={target.model!r}, benchmark={target.benchmark!r}"
    )


def _recompute_benchmark_result(result: dict[str, Any]) -> None:
    scores = result.get("scores", [])
    total = len(scores)
    passed = sum(1 for score in scores if score.get("passed"))
    errors = sum(1 for score in scores if score.get("error"))
    result["total"] = total
    result["passed"] = passed
    result["errors"] = errors
    result["pass_at_k"] = round(passed / total, 4) if total else 0.0

    durations = [
        score.get("duration_ms")
        for score in scores
        if score.get("duration_ms") is not None
    ]
    if durations or "total_duration_ms" in result:
        result["total_duration_ms"] = round(sum(durations), 2)


def _recompute_model_summary(model_entry: dict[str, Any]) -> None:
    results = model_entry.get("results", [])
    total_fixtures = sum(result.get("total", 0) for result in results)
    total_passed = sum(result.get("passed", 0) for result in results)
    summary = model_entry.setdefault("summary", {})
    summary["total_benchmarks"] = len(results)
    summary["total_fixtures"] = total_fixtures
    summary["total_passed"] = total_passed
    summary["overall_pass_at_k"] = (
        round(total_passed / total_fixtures, 4)
        if total_fixtures
        else 0.0
    )


def _recompute_profile_summary(profile_entry: dict[str, Any]) -> None:
    models = profile_entry.get("models", [])
    total_fixtures = sum(
        model.get("summary", {}).get("total_fixtures", 0)
        for model in models
    )
    total_passed = sum(
        model.get("summary", {}).get("total_passed", 0)
        for model in models
    )
    summary = profile_entry.setdefault("summary", {})
    summary["total_models"] = len(models)
    summary["total_fixtures"] = total_fixtures
    summary["total_passed"] = total_passed
    summary["overall_pass_at_k"] = (
        round(total_passed / total_fixtures, 4)
        if total_fixtures
        else 0.0
    )


def _recompute_top_summary(payload: dict[str, Any]) -> None:
    profiles = payload.get("profiles", [])
    total_models = sum(
        profile.get("summary", {}).get("total_models", 0)
        for profile in profiles
    )
    total_fixtures = sum(
        profile.get("summary", {}).get("total_fixtures", 0)
        for profile in profiles
    )
    total_passed = sum(
        profile.get("summary", {}).get("total_passed", 0)
        for profile in profiles
    )
    summary = payload.setdefault("summary", {})
    summary["total_profiles"] = len(profiles)
    summary["total_models"] = total_models
    summary["total_fixtures"] = total_fixtures
    summary["total_passed"] = total_passed
    summary["overall_pass_at_k"] = (
        round(total_passed / total_fixtures, 4)
        if total_fixtures
        else 0.0
    )


def _recompute_models_top_summary(payload: dict[str, Any]) -> None:
    models = payload.get("models", [])
    total_fixtures = sum(
        model.get("summary", {}).get("total_fixtures", 0)
        for model in models
    )
    total_passed = sum(
        model.get("summary", {}).get("total_passed", 0)
        for model in models
    )
    summary = payload.setdefault("summary", {})
    summary["total_models"] = len(models)
    summary["total_fixtures"] = total_fixtures
    summary["total_passed"] = total_passed
    summary["overall_pass_at_k"] = (
        round(total_passed / total_fixtures, 4)
        if total_fixtures
        else 0.0
    )
