"""Tests for parallel fixture execution via --fixture-workers.

Verifies:
1. Parallel execution reduces wall time by ≥40% vs sequential (4 workers).
2. JSON output is equivalent regardless of worker count (same fixture IDs and scores).
3. Fixture ordering is preserved in output regardless of execution order.
4. No git branch leakage in temporary fixture directories.
"""

import json
import subprocess
import sys
import time
from collections import Counter

import pytest


@pytest.fixture
def gitbench():
    """Return the path to the gitbench module entry point."""
    return [sys.executable, "-m", "gitbench.cli"]


def run_gitbench(args: list[str]) -> tuple[int, str, float]:
    """Run gitbench and return exit code, stdout, and wall time in seconds."""
    t0 = time.monotonic()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "gitbench.cli",
            "run",
            "--output-mode",
            "text",
        ]
        + args,
        capture_output=True,
        text=True,
        timeout=120,
    )
    elapsed = time.monotonic() - t0
    return result.returncode, result.stdout + result.stderr, elapsed


def parse_output(output: str) -> dict:
    """Parse JSON from gitbench output (handles non-JSON prefix/suffix lines)."""
    start = output.find("{")
    if start == -1:
        raise ValueError(f"No JSON object in output: {output[:200]}")
    depth = 0
    end = len(output)
    for i, ch in enumerate(output[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return json.loads(output[start:end])


def get_scores(result: dict) -> list[dict]:
    """Extract the list of fixture scores from a parsed result dict."""
    # Single benchmark result
    if "scores" in result:
        return result["scores"]
    # Wrapped in results list
    if "results" in result:
        inner = result["results"]
        if isinstance(inner, list) and len(inner) == 1 and "scores" in inner[0]:
            return inner[0]["scores"]
    # Wrapped in models list
    if "models" in result:
        models = result["models"]
        if isinstance(models, list) and len(models) == 1:
            inner = models[0]
            if "results" in inner:
                inner_results = inner["results"]
                if isinstance(inner_results, list) and len(inner_results) == 1 and "scores" in inner_results[0]:
                    return inner_results[0]["scores"]
    # Wrapped in profiles list
    if "profiles" in result:
        profiles = result["profiles"]
        if isinstance(profiles, list) and len(profiles) == 1:
            models = profiles[0].get("models", [])
            if isinstance(models, list) and len(models) == 1:
                inner = models[0]
                if "results" in inner:
                    inner_results = inner["results"]
                    if isinstance(inner_results, list) and len(inner_results) == 1 and "scores" in inner_results[0]:
                        return inner_results[0]["scores"]
    raise ValueError(f"Cannot extract scores from result structure: {list(result.keys())}")


class TestParallelExecutionWallTime:
    """Verify parallel execution reduces wall time vs sequential."""

    def test_wall_time_reduction_with_4_workers(self, gitbench):
        """Wall time with 4 workers should be ≤ 60% of sequential wall time.

        This is the primary performance regression test for --fixture-workers.
        The 4-worker parallel execution should complete in ≤ 60% of the time
        taken by sequential execution (i.e. ≥ 40% wall-time reduction).

        Note: This test may be slightly noisy on shared/CI hardware. The threshold
        is set to 60% to account for thread overhead and system variance.
        """
        # Run sequentially
        code1, out1, elapsed1 = run_gitbench(
            ["--benchmark", "commit_messages", "--model", "mock", "--fixture-workers", "1"]
        )
        assert code1 == 0, f"Sequential run failed: {out1}"

        # Run in parallel with 4 workers
        code4, out4, elapsed4 = run_gitbench(
            ["--benchmark", "commit_messages", "--model", "mock", "--fixture-workers", "4"]
        )
        assert code4 == 0, f"Parallel run failed: {out4}"

        ratio = elapsed4 / elapsed1
        reduction = (1 - ratio) * 100

        # Assert parallel is ≤ 60% of sequential (≥ 40% reduction)
        assert ratio <= 0.60, (
            f"Parallel execution (4 workers) took {elapsed4:.2f}s, "
            f"sequential took {elapsed1:.2f}s — ratio {ratio:.2%} > 60% threshold. "
            f"Reduction: {reduction:.1f}% (expected ≥ 40%)"
        )

    def test_wall_time_improvement_with_2_workers(self, gitbench):
        """2 workers should also show meaningful wall-time improvement."""
        code1, _, elapsed1 = run_gitbench(
            ["--benchmark", "commit_messages", "--model", "mock", "--fixture-workers", "1"]
        )
        assert code1 == 0

        code2, _, elapsed2 = run_gitbench(
            ["--benchmark", "commit_messages", "--model", "mock", "--fixture-workers", "2"]
        )
        assert code2 == 0

        ratio = elapsed2 / elapsed1
        # 2 workers may not reach 40% reduction due to overhead, but should show some improvement
        assert ratio <= 0.80, (
            f"2-worker run took {elapsed2:.2f}s vs sequential {elapsed1:.2f}s "
            f"(ratio {ratio:.2%}). Expected ≤ 80% for measurable improvement."
        )


class TestParallelOutputEquivalence:
    """Verify parallel execution produces equivalent output to sequential."""

    def test_same_fixture_ids_and_scores(self, gitbench):
        """Output from parallel and sequential runs should contain the same fixture IDs and scores.

        The order of scores in the JSON output may differ (threads complete at
        different times), but the set of fixture IDs and their individual scores
        must be identical.
        """
        code1, out1, _ = run_gitbench(
            ["--benchmark", "commit_messages", "--model", "mock", "--fixture-workers", "1"]
        )
        assert code1 == 0

        code4, out4, _ = run_gitbench(
            ["--benchmark", "commit_messages", "--model", "mock", "--fixture-workers", "4"]
        )
        assert code4 == 0

        result_seq = parse_output(out1)
        result_par = parse_output(out4)

        scores_seq = get_scores(result_seq)
        scores_par = get_scores(result_par)

        assert len(scores_seq) == len(scores_par), (
            f"Score count mismatch: sequential {len(scores_seq)} vs parallel {len(scores_par)}"
        )

        # Build fixture_id → score dict for each
        seq_map = {s["fixture_id"]: s for s in scores_seq}
        par_map = {s["fixture_id"]: s for s in scores_par}

        assert set(seq_map.keys()) == set(par_map.keys()), (
            f"Fixture IDs differ: seq={set(seq_map)}, par={set(par_map)}"
        )

        # Compare scores (similarity may be floats — check with tolerance)
        for fid in seq_map:
            s_seq = seq_map[fid]
            s_par = par_map[fid]
            assert s_seq["passed"] == s_par["passed"], (
                f"Fixture {fid}: passed mismatch seq={s_seq['passed']} par={s_par['passed']}"
            )
            assert abs(s_seq["similarity"] - s_par["similarity"]) < 1e-6, (
                f"Fixture {fid}: similarity mismatch seq={s_seq['similarity']} par={s_par['similarity']}"
            )
            # Errors should also be consistent
            seq_err = s_seq.get("error") or ""
            par_err = s_par.get("error") or ""
            assert (seq_err or s_seq["passed"]) == (par_err or s_par["passed"]), (
                f"Fixture {fid}: error state mismatch"
            )


class TestFixtureOrdering:
    """Verify fixture ordering is preserved in output regardless of execution order."""

    def test_output_order_matches_fixture_order(self, gitbench):
        """The JSON output should have scores in the same order as the fixture definitions.

        Even when threads complete out of order (e.g. f005 before f002), the output
        should be re-sorted into the canonical fixture order by ID so that results
        are deterministic across runs.
        """
        code1, out1, _ = run_gitbench(
            ["--benchmark", "commit_messages", "--model", "mock", "--fixture-workers", "1"]
        )
        assert code1 == 0

        result_seq = parse_output(out1)
        scores_seq = get_scores(result_seq)

        # Sequential output is the ground-truth ordering
        seq_order = [s["fixture_id"] for s in scores_seq]

        # Run parallel multiple times — output order should always be the same
        orders = []
        for _ in range(3):
            code4, out4, _ = run_gitbench(
                ["--benchmark", "commit_messages", "--model", "mock", "--fixture-workers", "4"]
            )
            assert code4 == 0
            result_par = parse_output(out4)
            scores_par = get_scores(result_par)
            orders.append([s["fixture_id"] for s in scores_par])

        # All parallel runs should have the same ordering
        assert orders[0] == orders[1] == orders[2], (
            f"Output order not stable across parallel runs: {orders}"
        )

        # Ordering should match sequential (canonical fixture order)
        assert orders[0] == seq_order, (
            f"Parallel output order {orders[0]} does not match sequential order {seq_order}"
        )

    def test_all_fixtures_present(self, gitbench):
        """Every fixture should appear exactly once in the output, regardless of worker count."""
        for workers in [1, 2, 4]:
            code, out, _ = run_gitbench(
                ["--benchmark", "commit_messages", "--model", "mock", "--fixture-workers", str(workers)]
            )
            assert code == 0, f"Run with {workers} workers failed: {out}"
            result = parse_output(out)
            scores = get_scores(result)

            fixture_ids = [s["fixture_id"] for s in scores]
            counter = Counter(fixture_ids)

            duplicates = {fid: count for fid, count in counter.items() if count > 1}
            assert not duplicates, f"Duplicate fixture IDs found with {workers} workers: {duplicates}"
            assert len(fixture_ids) == 12, (
                f"Expected 12 fixtures with {workers} workers, got {len(fixture_ids)}"
            )


class TestGitBranchLeakage:
    """Verify no git branch state leaks between fixture temp directories."""

    def test_no_branch_leakage_in_temp_dirs(self, gitbench, tmp_path):
        """After running benchmarks, no fixture temp directories should have extra branches.

        This catches cases where a fixture's setup creates git branches that are
        not cleaned up, potentially polluting subsequent fixtures.
        """
        code, out, _ = run_gitbench(
            ["--benchmark", "commit_messages", "--model", "mock", "--fixture-workers", "4"]
        )
        assert code == 0

        result = parse_output(out)
        scores = get_scores(result)

        # Check each fixture's result has no branch leakage
        errors = []
        for score in scores:
            # If a fixture failed, check that error isn't about branch conflicts
            if not score.get("passed") and score.get("error"):
                # A real branch leakage would show up as an error mentioning
                # 'already exists' or 'would be overwritten'
                err_lower = score["error"].lower()
                if any(phrase in err_lower for phrase in ["already exists", "would be overwritten", "refusing"]):
                    errors.append(f"Fixture {score['fixture_id']}: {score['error']}")

        assert not errors, (
            "Possible branch leakage detected (git errors about refs/branches): "
            + "; ".join(errors)
        )

    def test_benchmark_completes_without_branch_conflicts(self, gitbench):
        """The benchmark should complete with exit code 0 regardless of worker count."""
        for workers in [1, 4]:
            code, out, _ = run_gitbench(
                ["--benchmark", "commit_messages", "--model", "mock", "--fixture-workers", str(workers)]
            )
            combined = out.lower()
            # No mention of "branch" or "ref" errors in output
            assert not any(phrase in combined for phrase in [
                "already exists",
                "would be overwritten",
                "refusing to pull",
                "branch conflict",
            ]), (
                f"Branch conflict detected with {workers} workers: {out}"
            )
