"""Export GitBench results to various format strings."""

import csv
import io
import json
from typing import Any

from gitbench.harness.aggregation import (
    compute_benchmark_aggregates,
    compute_model_aggregates,
    refresh_campaign_aggregates,
)
from gitbench.harness.campaign import Campaign, CampaignReport


def export_csv(envelope: dict) -> str:
    """Return a CSV string with one row per fixture result.

    Columns: benchmark, fixture_id, model, passed, similarity,
             model_output, error, timestamp, git_sha, profile,
             benchmark_suite_version

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
        "benchmark_suite_version", "reasoning_level",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for result in envelope.get("results", []):
        if "error" in result and result.get("benchmark") is None:
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
                "benchmark_suite_version": envelope.get("benchmark_suite_version", ""),
                "reasoning_level": score.get("reasoning_level", ""),
            })

    return output.getvalue()


def export_artificialanalysis(envelope: dict) -> str:
    """Return a CSV string with one row per benchmark (benchmark-level).

    Columns: model, benchmark, score, total, passed, timestamp,
             git_sha, provider, profile, benchmark_suite_version

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
        "benchmark_suite_version", "reasoning_level",
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
        score = result.get("pass_at_k", round(passed / total, 4) if total > 0 else 0.0)
        scores = result.get("scores", [])
        reasoning_level = scores[0].get("reasoning_level", "") if scores else ""
        writer.writerow({
            "model": envelope.get("model", ""),
            "benchmark": benchmark,
            "score": score,
            "total": total,
            "passed": passed,
            "timestamp": envelope.get("timestamp", ""),
            "git_sha": envelope.get("git_sha", ""),
            "provider": "",
            "profile": envelope.get("profile", ""),
            "benchmark_suite_version": envelope.get("benchmark_suite_version", ""),
            "reasoning_level": reasoning_level,
        })

    return output.getvalue()


def export_json(envelope: dict) -> str:
    """Return the complete run envelope as formatted JSON."""
    return json.dumps(envelope, indent=2)


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


def build_campaign_report(campaign: Campaign) -> CampaignReport:
    """Build a versioned campaign report from a campaign and its raw attempts.

    Recomputes all aggregates from immutable raw attempts and packages
    campaign metadata, trial summaries, fixture aggregates, model/benchmark
    summaries, resource summaries, and judge evidence into the new schema.
    """
    from datetime import datetime, timezone

    refresh_campaign_aggregates(campaign)
    model_summaries = compute_model_aggregates(campaign, campaign.fixture_aggregates)
    benchmark_summaries = compute_benchmark_aggregates(
        campaign, campaign.fixture_aggregates
    )
    judge_evidence = [
        attempt.judge_evidence
        for attempt in campaign.raw_attempts
        if attempt.judge_evidence is not None
    ]
    resource_summaries = []
    if campaign.resource_summary is not None:
        resource_summaries.append(campaign.resource_summary)
    for summary in model_summaries:
        if summary.resource_summary is not None:
            resource_summaries.append(summary.resource_summary)
    for summary in benchmark_summaries:
        if summary.resource_summary is not None:
            resource_summaries.append(summary.resource_summary)

    return CampaignReport(
        version=2,
        schema_version=2,
        generated_at=datetime.now(timezone.utc).isoformat(),
        campaign=campaign,
        model_summaries=model_summaries,
        benchmark_summaries=benchmark_summaries,
        resource_summaries=resource_summaries,
        judge_evidence=judge_evidence,
    )


def export_campaign_report(campaign: Campaign) -> str:
    """Return a campaign report as formatted JSON in the new schema."""
    report = build_campaign_report(campaign)
    return json.dumps(report.to_dict(), indent=2)


def build_compatibility_report(legacy_envelope: dict[str, Any]) -> CampaignReport:
    """Generate a campaign-aware compatibility report from a historical artifact.

    Imports the legacy envelope as a one-trial legacy campaign and builds the
    new schema report.  Legacy campaigns do not infer stability metrics.
    """
    from gitbench.harness.import_legacy import import_legacy_campaign

    campaign = import_legacy_campaign(legacy_envelope)
    return build_campaign_report(campaign)


def export_compatibility_report(legacy_envelope: dict[str, Any]) -> str:
    """Return a compatibility report as formatted JSON in the new schema."""
    return json.dumps(build_compatibility_report(legacy_envelope).to_dict(), indent=2)


# ── Format Registry ──────────────────────────────────────────────────────────

FORMAT_REGISTRY: dict[str, Any] = {
    "csv": export_csv,
    "json": export_json,
    "artificialanalysis": export_artificialanalysis,
}
