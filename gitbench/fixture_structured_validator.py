"""Fixture structured-output contract validation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from gitbench.harness.types import Fixture, StructuredOutputContract
from gitbench.structured_output import (
    contract_for_benchmark_fixture,
    fixture_expected_as_payload,
    roundtrip_check,
    validate_contract,
    canonicalize,
)

logger = logging.getLogger(__name__)


@dataclass
class StructuredOutputIssue:
    """A single issue found during contract validation."""

    fixture_id: str
    benchmark: str
    code: str
    message: str


@dataclass
class StructuredOutputValidationReport:
    """Report from validating structured-output contracts across fixtures."""

    total_fixtures: int = 0
    fixtures_with_contract: int = 0
    fixtures_without_contract: int = 0
    issues: list[StructuredOutputIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return len(self.issues) == 0


def validate_fixture_contract(
    fixture: Fixture,
    benchmark_name: str,
) -> list[StructuredOutputIssue]:
    """Validate the structured-output contract for a single fixture.

    Returns a list of issues (empty means valid).
    """
    issues: list[StructuredOutputIssue] = []

    contract = contract_for_benchmark_fixture(fixture, benchmark_name)

    if contract is None:
        issues.append(
            StructuredOutputIssue(
                fixture_id=fixture.id,
                benchmark=benchmark_name,
                code="missing-contract",
                message=(
                    f"Fixture {fixture.id} ({benchmark_name}): "
                    "No structured-output contract could be resolved. "
                    f"Scoring type is '{fixture.scoring.get('type', 'similarity')}'."
                ),
            )
        )
        return issues

    # Validate the contract schema itself
    contract_errors = validate_contract(contract)
    for error in contract_errors:
        issues.append(
            StructuredOutputIssue(
                fixture_id=fixture.id,
                benchmark=benchmark_name,
                code="invalid-contract",
                message=f"Fixture {fixture.id} ({benchmark_name}): {error}",
            )
        )

    # Check roundtrip: expected answer → structured payload → canonical text
    if not roundtrip_check(fixture, contract):
        payload = fixture_expected_as_payload(fixture, contract)
        if payload is not None:
            canonical = canonicalize(payload, contract)
            issues.append(
                StructuredOutputIssue(
                    fixture_id=fixture.id,
                    benchmark=benchmark_name,
                    code="roundtrip-mismatch",
                    message=(
                        f"Fixture {fixture.id} ({benchmark_name}): "
                        f"Expected answer cannot roundtrip through structured output. "
                        f"Expected={fixture.expected!r}, "
                        f"Canonicalized={canonical!r}"
                    ),
                )
            )
        else:
            issues.append(
                StructuredOutputIssue(
                    fixture_id=fixture.id,
                    benchmark=benchmark_name,
                    code="roundtrip-representation-failure",
                    message=(
                        f"Fixture {fixture.id} ({benchmark_name}): "
                        "Expected answer cannot be represented as structured payload."
                    ),
                )
            )

    return issues


def validate_all_fixtures(
    fixtures_by_benchmark: dict[str, list[Fixture]],
) -> StructuredOutputValidationReport:
    """Validate structured-output contracts across all fixtures in all benchmarks.

    Args:
        fixtures_by_benchmark: Mapping of benchmark_name → list of Fixture objects.

    Returns:
        A validation report listing all issues found.
    """
    report = StructuredOutputValidationReport()

    for benchmark_name, fixtures in fixtures_by_benchmark.items():
        report.total_fixtures += len(fixtures)
        for fixture in fixtures:
            fixture_issues = validate_fixture_contract(fixture, benchmark_name)
            if fixture_issues:
                report.issues.extend(fixture_issues)
                if any(i.code == "missing-contract" for i in fixture_issues):
                    report.fixtures_without_contract += 1
                else:
                    report.fixtures_with_contract += 1
            else:
                report.fixtures_with_contract += 1

    report.fixtures_without_contract = (
        report.total_fixtures - report.fixtures_with_contract
    )

    return report
