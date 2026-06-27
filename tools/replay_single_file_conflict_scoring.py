#!/usr/bin/env python
"""Replay stored conflict outputs against candidate single-file file-block scoring."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gitbench.harness.loader import FixtureLoader
from gitbench.harness.scorer import Scorer
from gitbench.harness.types import Fixture


BENCHMARKS = ("merge_conflicts", "cherry_pick", "rebase")
FIXTURE_ROOT = Path("fixtures")
LEGACY_EXACT_MATCH_NO_STRIP_FENCES = {
    ("merge_conflicts", "f009"),
    ("cherry_pick", "f009"),
    ("rebase", "f002"),
    ("rebase", "f003"),
    ("rebase", "f009"),
}
FILENAME_RE = re.compile(
    r"\b[A-Za-z0-9_./-]+\."
    r"(?:cfg|css|html|ini|js|json|md|py|toml|ts|txt|ya?ml)\b"
)


@dataclass
class ChangedOutput:
    run: str
    model: str
    output_mode: str
    before_error: str | None
    after_error: str | None
    output: str


@dataclass
class FixtureReplay:
    benchmark: str
    fixture_id: str
    path: str
    filename: str
    before_expected_passes: bool
    after_raw_expected_passes: bool
    after_block_expected_passes: bool
    prompt_names_filename: bool
    current_scoring: dict[str, Any]
    attempts: int = 0
    before_passes: int = 0
    after_passes: int = 0
    newly_passing: list[ChangedOutput] = field(default_factory=list)
    newly_failing: list[ChangedOutput] = field(default_factory=list)

    @property
    def changed_count(self) -> int:
        return len(self.newly_passing) + len(self.newly_failing)


def main() -> int:
    args = parse_args()
    fixtures = load_candidate_fixtures()
    report = replay(fixtures, [Path(root) for root in args.results_root])

    if args.json_out:
        args.json_out.write_text(json.dumps(to_json(report), indent=2) + "\n")
    if args.markdown_out:
        args.markdown_out.write_text(to_markdown(report))
    if not args.json_out and not args.markdown_out:
        print(to_markdown(report))

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-root",
        action="append",
        default=[],
        help="Stored result root to replay. May be passed more than once.",
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()
    if not args.results_root:
        args.results_root = ["gitbench-results", "gitbench-results-bak"]
    return args


def load_candidate_fixtures() -> dict[tuple[str, str], tuple[Fixture, Fixture, str, Path]]:
    loader = FixtureLoader()
    candidates: dict[tuple[str, str], tuple[Fixture, Fixture, str, Path]] = {}

    for benchmark in BENCHMARKS:
        for path in sorted((FIXTURE_ROOT / benchmark).glob("*.yaml")):
            for fixture in loader.load_file(str(path)):
                candidate = candidate_pair(benchmark, fixture, path)
                if candidate is None:
                    continue
                candidates[(benchmark, fixture.id)] = candidate
    return candidates


def candidate_pair(
    benchmark: str,
    fixture: Fixture,
    path: Path,
) -> tuple[Fixture, Fixture, str, Path] | None:
    scoring_type = fixture.scoring.get("type", "similarity")
    if scoring_type == "exact_match" and not fixture.scoring.get("expected_files"):
        filename = single_prompt_filename(fixture.prompt)
        if filename is None:
            return None
        candidate = clone_fixture(
            fixture,
            scoring={
                "type": "resolved_file_blocks",
                "expected_files": {filename: fixture.expected},
            },
        )
        return fixture, candidate, filename, path

    if scoring_type == "resolved_file_blocks":
        expected_files = fixture.scoring.get("expected_files")
        if not (
            isinstance(expected_files, dict)
            and len(expected_files) == 1
            and all(isinstance(name, str) for name in expected_files)
        ):
            return None
        filename = next(iter(expected_files))
        prompt_filename = single_prompt_filename(fixture.prompt)
        if prompt_filename is not None and prompt_filename != filename:
            return None
        return legacy_exact_fixture(benchmark, fixture), fixture, filename, path

    return None


def clone_fixture(fixture: Fixture, scoring: dict[str, Any]) -> Fixture:
    return Fixture(
        id=fixture.id,
        description=fixture.description,
        setup=list(fixture.setup),
        prompt=fixture.prompt,
        expected=fixture.expected,
        scoring=scoring,
        purpose=fixture.purpose,
        difficulty=fixture.difficulty,
        tags=list(fixture.tags),
        structured_output=fixture.structured_output,
        output_schema=fixture.output_schema,
    )


def legacy_exact_fixture(benchmark: str, fixture: Fixture) -> Fixture:
    scoring: dict[str, Any] = {"type": "exact_match"}
    if (benchmark, fixture.id) not in LEGACY_EXACT_MATCH_NO_STRIP_FENCES:
        scoring["strip_fences"] = True
    return clone_fixture(fixture, scoring=scoring)


def single_prompt_filename(prompt: str) -> str | None:
    filenames = sorted(set(FILENAME_RE.findall(prompt)))
    if len(filenames) != 1:
        return None
    return filenames[0]


def replay(
    fixtures: dict[tuple[str, str], tuple[Fixture, Fixture, str, Path]],
    roots: list[Path],
) -> list[FixtureReplay]:
    scorer = Scorer()
    reports: dict[tuple[str, str], FixtureReplay] = {}

    for (benchmark, fixture_id), (current, candidate, filename, path) in fixtures.items():
        reports[(benchmark, fixture_id)] = FixtureReplay(
            benchmark=benchmark,
            fixture_id=fixture_id,
            path=str(path),
            filename=filename,
            before_expected_passes=scorer.score(current, current.expected).passed,
            after_raw_expected_passes=scorer.score(candidate, current.expected).passed,
            after_block_expected_passes=scorer.score(
                candidate,
                f"{filename}:\n{current.expected}",
            ).passed,
            prompt_names_filename=filename in current.prompt,
            current_scoring=dict(current.scoring),
        )

    for result_file in iter_result_files(roots):
        data = load_result_file(result_file)
        if not data:
            continue
        run_label = str(result_file)
        model = str(data.get("model", ""))
        output_mode = str(data.get("output_mode", ""))

        for benchmark_result in data.get("results", []):
            benchmark = benchmark_result.get("benchmark")
            if benchmark not in BENCHMARKS:
                continue
            for score_data in benchmark_result.get("scores", []):
                fixture_id = score_data.get("fixture_id")
                key = (benchmark, fixture_id)
                if key not in fixtures:
                    continue
                current, candidate, _filename, _path = fixtures[key]
                output = str(score_data.get("model_output", ""))
                before = scorer.score(current, output)
                after = scorer.score(candidate, output)
                item = reports[key]
                item.attempts += 1
                item.before_passes += int(before.passed)
                item.after_passes += int(after.passed)
                if before.passed == after.passed:
                    continue
                changed = ChangedOutput(
                    run=run_label,
                    model=model,
                    output_mode=output_mode,
                    before_error=before.error,
                    after_error=after.error,
                    output=output,
                )
                if after.passed:
                    item.newly_passing.append(changed)
                else:
                    item.newly_failing.append(changed)

    return [reports[key] for key in sorted(reports)]


def iter_result_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(sorted(root.glob("*/*.json")))
    return files


def load_result_file(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data.get("results"), list):
        return None
    return data


def to_json(report: list[FixtureReplay]) -> dict[str, Any]:
    return {
        "summary": aggregate(report),
        "fixtures": [
            {
                "benchmark": item.benchmark,
                "fixture_id": item.fixture_id,
                "path": item.path,
                "filename": item.filename,
                "current_scoring": item.current_scoring,
                "expected_checks": {
                    "before_expected_passes": item.before_expected_passes,
                    "after_raw_expected_passes": item.after_raw_expected_passes,
                    "after_block_expected_passes": item.after_block_expected_passes,
                },
                "attempts": item.attempts,
                "before_passes": item.before_passes,
                "after_passes": item.after_passes,
                "newly_passing": [changed_to_json(c) for c in item.newly_passing],
                "newly_failing": [changed_to_json(c) for c in item.newly_failing],
            }
            for item in report
        ],
    }


def changed_to_json(changed: ChangedOutput) -> dict[str, Any]:
    return {
        "run": changed.run,
        "model": changed.model,
        "output_mode": changed.output_mode,
        "before_error": changed.before_error,
        "after_error": changed.after_error,
        "output": changed.output,
    }


def to_markdown(report: list[FixtureReplay]) -> str:
    summary = aggregate(report)
    lines = [
        "# Single-File Conflict Scoring Replay",
        "",
        "Candidate scorer: `resolved_file_blocks` with one `expected_files` entry. "
        "Single-file unheaded content is treated as that file's content; named "
        "file blocks are also accepted.",
        "",
        "## Summary",
        "",
        f"- Candidate fixtures: {summary['candidate_fixtures']}",
        f"- Stored attempts replayed: {summary['attempts']}",
        f"- Before passes: {summary['before_passes']}",
        f"- After passes: {summary['after_passes']}",
        f"- Newly passing outputs: {summary['newly_passing']}",
        f"- Newly failing outputs: {summary['newly_failing']}",
        "",
        "## Fixture Results",
        "",
        "| Fixture | File | Expected checks | Attempts | Before | After | Delta | Decision evidence |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report:
        expected = "/".join(
            "pass" if check else "fail"
            for check in (
                item.before_expected_passes,
                item.after_raw_expected_passes,
                item.after_block_expected_passes,
            )
        )
        delta = item.after_passes - item.before_passes
        evidence = (
            f"{len(item.newly_passing)} newly passing; "
            f"{len(item.newly_failing)} newly failing"
        )
        lines.append(
            f"| `{item.benchmark}/{item.fixture_id}` | `{item.filename}` | "
            f"{expected} | {item.attempts} | {item.before_passes} | "
            f"{item.after_passes} | {delta:+d} | {evidence} |"
        )

    lines.extend(["", "## Changed Outputs", ""])
    changed_groups = group_changed_outputs(report)
    if not changed_groups:
        lines.append("No stored outputs changed pass/fail outcome.")
    for key, changes in changed_groups.items():
        lines.extend([f"### `{key}`", ""])
        for change in changes[:5]:
            direction = "newly passing" if change.after_error is None else "newly failing"
            lines.extend(
                [
                    f"- {direction}: `{change.model}` `{change.output_mode}` from `{change.run}`",
                    "",
                    "  ```text",
                    indent_snippet(change.output, "  "),
                    "  ```",
                    "",
                ]
            )
        if len(changes) > 5:
            lines.append(f"- {len(changes) - 5} additional changed outputs omitted.")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def aggregate(report: list[FixtureReplay]) -> dict[str, int]:
    return {
        "candidate_fixtures": len(report),
        "attempts": sum(item.attempts for item in report),
        "before_passes": sum(item.before_passes for item in report),
        "after_passes": sum(item.after_passes for item in report),
        "newly_passing": sum(len(item.newly_passing) for item in report),
        "newly_failing": sum(len(item.newly_failing) for item in report),
    }


def group_changed_outputs(report: list[FixtureReplay]) -> dict[str, list[ChangedOutput]]:
    groups: dict[str, list[ChangedOutput]] = defaultdict(list)
    for item in report:
        key = f"{item.benchmark}/{item.fixture_id}"
        groups[key].extend(item.newly_passing)
        groups[key].extend(item.newly_failing)
    return dict(groups)


def indent_snippet(value: str, prefix: str, limit: int = 1000) -> str:
    snippet = value if len(value) <= limit else value[:limit] + "\n..."
    return "\n".join(prefix + line for line in snippet.splitlines())


if __name__ == "__main__":
    raise SystemExit(main())
