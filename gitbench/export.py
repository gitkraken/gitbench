"""Export GitBench results to various format strings."""

import csv
import io
from typing import Any


def export_csv(envelope: dict) -> str:
    """Return a CSV string with one row per fixture result.

    Columns: benchmark, fixture_id, model, passed, similarity,
             model_output, error, timestamp, git_sha, profile

    Args:
        envelope: Run envelope dict with keys: version, timestamp,
                  git_sha, model, profile, summary, results.
                  Each result in results has: benchmark, total, passed,
                  pass_at_k, scores.
                  Each score dict has: fixture_id, passed, similarity,
                  model_output, error.

    Returns:
        CSV string with headers and one row per fixture result.
        Empty results produce headers with zero data rows.
    """
    fieldnames = [
        "benchmark", "fixture_id", "model", "passed", "similarity",
        "model_output", "error", "timestamp", "git_sha", "profile",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for result in envelope.get("results", []):
        if "error" in result and result.get("benchmark") is None:
            # Skip error-only entries with no benchmark
            continue
        benchmark = result.get("benchmark", "")
        for score in result.get("scores", []):
            writer.writerow({
                "benchmark": benchmark,
                "fixture_id": score.get("fixture_id", ""),
                "model": envelope.get("model", ""),
                "passed": 1 if score.get("passed") else 0,
                "similarity": score.get("similarity", ""),
                "model_output": _truncate(score.get("model_output", ""), 500),
                "error": score.get("error", ""),
                "timestamp": envelope.get("timestamp", ""),
                "git_sha": envelope.get("git_sha", ""),
                "profile": envelope.get("profile", ""),
            })

    return output.getvalue()


def export_artificialanalysis(envelope: dict) -> str:
    """Return a CSV string with one row per benchmark (benchmark-level).

    Columns: model, benchmark, score, total, passed, timestamp,
             git_sha, provider, profile

    score is pass_at_k rounded to 4 decimal places.

    Args:
        envelope: Run envelope dict (same structure as export_csv).

    Returns:
        CSV string with headers and one row per benchmark.
        Empty results produce headers with zero data rows.
    """
    fieldnames = [
        "model", "benchmark", "score", "total", "passed",
        "timestamp", "git_sha", "provider", "profile",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for result in envelope.get("results", []):
        if "error" in result and result.get("benchmark") is None:
            continue
        benchmark = result.get("benchmark", "")
        total = result.get("total", 0)
        passed = result.get("passed", 0)
        # pass_at_k is pre-rounded in the envelope; fallback to computed
        score = result.get("pass_at_k", round(passed / total, 4) if total > 0 else 0.0)
        writer.writerow({
            "model": envelope.get("model", ""),
            "benchmark": benchmark,
            "score": score,
            "total": total,
            "passed": passed,
            "timestamp": envelope.get("timestamp", ""),
            "git_sha": envelope.get("git_sha", ""),
            # provider is not in the envelope; leave blank to match the column
            "provider": "",
            "profile": envelope.get("profile", ""),
        })

    return output.getvalue()


def get_available_formats() -> list[str]:
    """Return a sorted list of available export format names."""
    return sorted(FORMAT_REGISTRY.keys())


def _truncate(s: str, max_len: int) -> str:
    """Truncate string to max_len, appending '…' if truncated."""
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def export_csv_stdlib(envelope: dict) -> str:
    """Alias for export_csv — kept for backward compatibility."""
    return export_csv(envelope)


# ── Format Registry ──────────────────────────────────────────────────────────

FORMAT_REGISTRY: dict[str, Any] = {
    "csv": export_csv,
    "artificialanalysis": export_artificialanalysis,
}