"""Tests for fixture self-check validation."""

import subprocess

import pytest

from gitbench.benchmarks.blame_forensics import BlameForensicsBenchmark
from gitbench.fixture_self_check import check_fixture, check_fixture_generically
from gitbench.harness.types import Fixture
from gitbench.scorer_capabilities import (
    capabilities_for_scorer,
    generic_capabilities_for_scorer,
)


def test_self_check_flags_non_hash_expected_for_hash_prompt():
    fixture = Fixture(
        id="hash_bad",
        description="Bad hash fixture",
        setup=[],
        prompt="What is the short hash for Fix null pointer bug?",
        expected="Fix null pointer bug",
        scoring={"type": "exact_match"},
    )

    issues = check_fixture_generically(fixture)

    assert [issue.code for issue in issues] == ["static-non-hash-expected"]


def test_self_check_allows_dynamic_hash_scorer_for_hash_prompt():
    fixture = Fixture(
        id="hash_ok",
        description="Dynamic hash fixture",
        setup=[],
        prompt="What is the short hash for Fix null pointer bug?",
        expected="",
        scoring={"type": "commit_hash_by_subject", "subject": "Fix null pointer bug"},
    )

    assert check_fixture_generically(fixture) == []


def test_self_check_flags_multiline_exact_match_without_order_contract():
    fixture = Fixture(
        id="lines_bad",
        description="Line list fixture",
        setup=[],
        prompt="List matching messages",
        expected="A\nB",
        scoring={"type": "exact_match"},
    )

    issues = check_fixture_generically(fixture)

    assert [issue.code for issue in issues] == ["multiline-exact-order-review"]


def test_self_check_allows_multiline_exact_match_with_order_contract():
    fixture = Fixture(
        id="lines_ok",
        description="Ordered line list fixture",
        setup=[],
        prompt="List matching messages in reverse chronological order",
        expected="B\nA",
        scoring={"type": "exact_match", "order_matters": True},
    )

    assert check_fixture_generically(fixture) == []


def test_capability_lookup_uses_benchmark_context_before_generic_fallback():
    branch_caps = capabilities_for_scorer("exact_match", benchmark_name="branch_cleanup")
    generic_caps = generic_capabilities_for_scorer("exact_match")

    assert branch_caps.order_sensitive is False
    assert branch_caps.selection_parser == "branch_line_set"
    assert generic_caps.order_sensitive is True


def test_capability_lookup_requires_benchmark_context_for_effective_behavior():
    with pytest.raises(ValueError, match="requires benchmark_name"):
        capabilities_for_scorer("exact_match")


def test_suite_level_self_check_requires_benchmark_context():
    fixture = Fixture(
        id="missing_context",
        description="Suite-level fixture",
        setup=[],
        prompt="List branches to delete, one per line",
        expected="fix-typo\nold-feature",
        scoring={"type": "exact_match"},
    )

    with pytest.raises(ValueError, match="requires benchmark_name"):
        check_fixture(fixture)


def test_self_check_allows_branch_cleanup_exact_match_set_scoring():
    fixture = Fixture(
        id="branch_set",
        description="Branch cleanup fixture",
        setup=[],
        prompt="List branches to delete, one per line",
        expected="fix-typo\nold-feature",
        scoring={"type": "exact_match"},
    )

    assert check_fixture(fixture, benchmark_name="branch_cleanup") == []


def test_generic_fixture_only_check_remains_explicit():
    fixture = Fixture(
        id="branch_set",
        description="Branch-like fixture checked without benchmark context",
        setup=[],
        prompt="List branches to delete, one per line",
        expected="fix-typo\nold-feature",
        scoring={"type": "exact_match"},
    )

    issues = check_fixture_generically(fixture)

    assert [issue.code for issue in issues] == ["multiline-exact-order-review"]


def test_self_check_allows_reflog_dynamic_lookup_key_for_hash_prompt():
    fixture = Fixture(
        id="reflog_dynamic",
        description="Reflog fixture",
        setup=[],
        prompt="Provide ONLY the 40-character commit hash recovered from reflog.",
        expected="Add third version - important changes",
        scoring={"type": "reflog_recovery"},
    )

    assert check_fixture(fixture, benchmark_name="reflog") == []


def test_self_check_allows_git_bisect_subject_or_hash_behavior():
    fixture = Fixture(
        id="bisect_dynamic",
        description="Bisect fixture",
        setup=[],
        prompt="Identify the bad commit hash or commit subject line.",
        expected="change add operation",
        scoring={"type": "bisect_regression"},
    )

    assert check_fixture(fixture, benchmark_name="git_bisect") == []


def test_self_check_validates_git_derived_expected_value(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    fixture = Fixture(
        id="derived_ok",
        description="Derived fixture",
        setup=[],
        prompt="How many tracked files exist?",
        expected="0",
        scoring={
            "type": "numeric_exact",
            "self_check": {
                "command": "git ls-files",
                "transform": "count_nonempty_lines",
            },
        },
    )

    assert check_fixture_generically(fixture, repo_path=str(repo)) == []


def test_self_check_reports_git_derived_expected_mismatch(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    fixture = Fixture(
        id="derived_bad",
        description="Derived fixture",
        setup=[],
        prompt="How many tracked files exist?",
        expected="1",
        scoring={
            "type": "numeric_exact",
            "self_check": {
                "command": "git ls-files",
                "transform": "count_nonempty_lines",
            },
        },
    )

    issues = check_fixture_generically(fixture, repo_path=str(repo))

    assert [issue.code for issue in issues] == ["derived-expected-mismatch"]


def test_blame_f010_has_one_broken_import_and_preserves_introducing_blame():
    benchmark = BlameForensicsBenchmark()
    fixture = next(
        fixture
        for fixture in benchmark.load_fixtures()
        if fixture.id == "f010"
    )
    executor, repo_path = benchmark.setup_fixture(fixture)

    try:
        assert (
            check_fixture(
                fixture,
                repo_path=repo_path,
                benchmark_name=BlameForensicsBenchmark.name,
            )
            == []
        )

        broken_additions = subprocess.run(
            [
                "git",
                "log",
                "--format=",
                "-p",
                "--",
                "src/main.py",
            ],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.count("+from helpers import")
        blame = subprocess.run(
            [
                "git",
                "blame",
                "--line-porcelain",
                "-L",
                "1,1",
                "--",
                "src/main.py",
            ],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

        assert broken_additions == 1
        assert "summary Update import path" in blame
    finally:
        executor.cleanup()
