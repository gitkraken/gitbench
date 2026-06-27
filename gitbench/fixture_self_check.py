"""Self-checks for fixture expectations that can be validated cheaply."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from gitbench.harness.types import Fixture
from gitbench.scorer_capabilities import (
    ScorerCapabilities,
    capabilities_for_scorer,
    generic_capabilities_for_scorer,
)


_HASH_RE = re.compile(r"\b[0-9a-fA-F]{7,40}\b")
_MISSING_BENCHMARK_NAME = object()


@dataclass
class FixtureSelfCheckIssue:
    fixture_id: str
    code: str
    message: str


def check_fixture(
    fixture: Fixture,
    repo_path: str | None = None,
    *,
    benchmark_name: str | object = _MISSING_BENCHMARK_NAME,
) -> list[FixtureSelfCheckIssue]:
    """Run benchmark-aware self-checks for a concrete benchmark fixture."""
    if benchmark_name is _MISSING_BENCHMARK_NAME or benchmark_name is None:
        raise ValueError(
            "check_fixture() requires benchmark_name for benchmark-aware suite "
            "validation; use check_fixture_generically() for explicit generic "
            "fixture-only checks."
        )
    if not isinstance(benchmark_name, str) or not benchmark_name.strip():
        raise ValueError("benchmark_name must be a non-empty string")
    issues: list[FixtureSelfCheckIssue] = []
    capabilities = capabilities_for_scorer(
        fixture.scoring.get("type", "similarity"),
        benchmark_name=benchmark_name,
    )
    issues.extend(_check_fixture_with_capabilities(fixture, capabilities, repo_path))
    return issues


def check_fixture_generically(
    fixture: Fixture,
    repo_path: str | None = None,
) -> list[FixtureSelfCheckIssue]:
    """Run generic fixture-only checks without benchmark-local scorer behavior."""
    capabilities = generic_capabilities_for_scorer(
        fixture.scoring.get("type", "similarity")
    )
    return _check_fixture_with_capabilities(fixture, capabilities, repo_path)


def _check_fixture_with_capabilities(
    fixture: Fixture,
    capabilities: ScorerCapabilities,
    repo_path: str | None,
) -> list[FixtureSelfCheckIssue]:
    issues: list[FixtureSelfCheckIssue] = []
    issues.extend(_check_hash_answer_shape(fixture, capabilities.dynamic_expected))
    issues.extend(_check_multiline_exact_order(fixture, capabilities.order_sensitive))
    if repo_path is not None:
        issues.extend(_check_derived_expected(fixture, repo_path))
    return issues


def _check_hash_answer_shape(
    fixture: Fixture,
    dynamic_expected: bool,
) -> list[FixtureSelfCheckIssue]:
    prompt = fixture.prompt.lower()
    asks_for_hash = "hash" in prompt
    if asks_for_hash and not dynamic_expected and not _HASH_RE.fullmatch(fixture.expected.strip()):
        return [
            FixtureSelfCheckIssue(
                fixture.id,
                "static-non-hash-expected",
                "Fixture asks for a hash but expected is not a hash or dynamic hash scorer",
            )
        ]
    return []


def _check_multiline_exact_order(
    fixture: Fixture,
    order_sensitive: bool,
) -> list[FixtureSelfCheckIssue]:
    if fixture.scoring.get("type") != "exact_match":
        return []
    lines = [line for line in fixture.expected.splitlines() if line.strip()]
    if (
        len(lines) <= 1
        or fixture.scoring.get("order_matters") is True
        or not order_sensitive
    ):
        return []
    return [
        FixtureSelfCheckIssue(
            fixture.id,
            "multiline-exact-order-review",
            "Multi-line exact_match fixture must set scoring.order_matters or use set scoring",
        )
    ]


def _check_derived_expected(
    fixture: Fixture,
    repo_path: str,
) -> list[FixtureSelfCheckIssue]:
    config = fixture.scoring.get("self_check", {})
    command = config.get("command")
    if not command:
        return []

    result = subprocess.run(
        command,
        shell=True,
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [
            FixtureSelfCheckIssue(
                fixture.id,
                "derived-command-failed",
                f"Self-check command failed: {result.stderr.strip()}",
            )
        ]

    actual = _transform_output(result.stdout, config.get("transform", "strip"))
    expected = fixture.expected.strip()
    if actual != expected:
        return [
            FixtureSelfCheckIssue(
                fixture.id,
                "derived-expected-mismatch",
                f"Expected {expected!r}, derived {actual!r}",
            )
        ]
    return []


def _transform_output(output: str, transform: str) -> str:
    if transform == "count_nonempty_lines":
        return str(len([line for line in output.splitlines() if line.strip()]))
    if transform == "short_hash":
        return output.strip()[:7]
    return output.strip()
