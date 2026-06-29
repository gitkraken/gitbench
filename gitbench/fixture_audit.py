"""Fixture calibration audit report for stored GitBench results."""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from gitbench.harness.loader import FixtureLoader


@dataclass
class FixtureMetadata:
    scoring_type: str
    difficulty: str


def load_fixture_metadata(fixtures_root: Path) -> dict[tuple[str, str], FixtureMetadata]:
    loader = FixtureLoader()
    metadata = {}
    for benchmark_dir in sorted(path for path in fixtures_root.iterdir() if path.is_dir()):
        for fixture in loader.load_dir(str(benchmark_dir)):
            metadata[(benchmark_dir.name, fixture.id)] = FixtureMetadata(
                scoring_type=fixture.scoring.get("type", "similarity"),
                difficulty=fixture.difficulty,
            )
    return metadata


def representative_failures(
    conn: sqlite3.Connection,
    benchmark_name: str,
    fixture_id: str,
    limit: int,
) -> list[str]:
    rows = conn.execute(
        """
        SELECT model_output, COUNT(*) AS occurrences
        FROM fixture_results
        WHERE benchmark_name = ?
          AND fixture_id = ?
          AND passed = 0
          AND TRIM(model_output) <> ''
        GROUP BY model_output
        ORDER BY occurrences DESC, model_output
        LIMIT ?
        """,
        (benchmark_name, fixture_id, limit),
    ).fetchall()
    return [
        f"{output.strip().replace(chr(10), ' / ')} ({count})"
        for output, count in rows
    ]


def build_report(
    db_path: Path,
    fixtures_root: Path,
    threshold: float,
    representative_limit: int,
) -> str:
    metadata = load_fixture_metadata(fixtures_root)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT benchmark_name,
                   fixture_id,
                   COUNT(*) AS total,
                   SUM(passed) AS passed,
                   AVG(passed) AS pass_rate
            FROM fixture_results
            GROUP BY benchmark_name, fixture_id
            HAVING pass_rate <= ?
            ORDER BY pass_rate ASC, benchmark_name, fixture_id
            """,
            (threshold,),
        ).fetchall()

        lines = [
            "| Benchmark | Fixture | Scoring | Difficulty | Pass Rate | Passed/Total | Representative Failed Outputs |",
            "| --- | --- | --- | --- | ---: | ---: | --- |",
        ]
        for benchmark_name, fixture_id, total, passed, pass_rate in rows:
            meta = metadata.get(
                (benchmark_name, fixture_id),
                FixtureMetadata(scoring_type="unknown", difficulty=""),
            )
            failures = representative_failures(
                conn, benchmark_name, fixture_id, representative_limit
            )
            lines.append(
                "| {benchmark} | {fixture} | {scoring} | {difficulty} | {rate:.1%} | "
                "{passed}/{total} | {failures} |".format(
                    benchmark=benchmark_name,
                    fixture=fixture_id,
                    scoring=meta.scoring_type,
                    difficulty=meta.difficulty or "-",
                    rate=pass_rate or 0.0,
                    passed=passed or 0,
                    total=total,
                    failures="<br>".join(failures) if failures else "-",
                )
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rank zero-pass and low-pass fixtures for calibration audit."
    )
    parser.add_argument("--db", type=Path, default=Path("web/data/gitbench.db"))
    parser.add_argument("--fixtures", type=Path, default=Path("fixtures"))
    parser.add_argument("--threshold", type=float, default=0.50)
    parser.add_argument("--representative-failures", type=int, default=3)
    args = parser.parse_args()

    print(
        build_report(
            args.db,
            args.fixtures,
            args.threshold,
            args.representative_failures,
        )
    )


if __name__ == "__main__":
    main()
