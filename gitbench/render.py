"""HTML report renderer for GitBench results."""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gitbench.harness.model import parse_model_name

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent / "web"
REPORT_DB_PATH = WEB_DIR / "data" / "gitbench.db"
REPORT_SCHEMA_PATH = WEB_DIR / "data" / "schema.sql"


def load_runs_from_dir(directory: str) -> list[dict]:
    """Load all run envelope JSON files from a directory.

    Args:
        directory: Path to directory containing JSON run files.

    Returns:
        List of run envelope dicts, sorted by suite version then timestamp.
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    runs = []
    for f in sorted(dir_path.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            if "version" in data and "results" in data:
                runs.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    runs.sort(key=_run_sort_key)
    return runs


def load_runs_from_jsonl(path: str) -> list[dict]:
    """Load run envelopes from a JSONL file.

    Args:
        path: Path to JSONL file.

    Returns:
        List of run envelope dicts, sorted by suite version then timestamp.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    runs = []
    for line in file_path.read_text().strip().split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            if "version" in data and "results" in data:
                runs.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    runs.sort(key=_run_sort_key)
    return runs


def load_runs_from_combined(path: str) -> list[dict]:
    """Load run envelopes from a combined results JSON file.

    The combined format (produced by default from ``gitbench run -a``)
    nests results under profiles → models.  This function extracts each
    model's results into individual run envelope dicts.

    Args:
        path: Path to the combined results JSON file.

    Returns:
        List of run envelope dicts, sorted by suite version then timestamp.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    data = json.loads(file_path.read_text())
    runs: list[dict] = []
    suite_version = data.get("benchmark_suite_version", "")
    # Try to get timestamp from the file's parent directory name (ISO format)
    timestamp = ""
    parent_name = file_path.parent.name
    if parent_name and parent_name[0].isdigit():
        # Directory name like 20260511T220621Z → convert to ISO
        try:
            from datetime import datetime
            dt = datetime.strptime(parent_name, "%Y%m%dT%H%M%SZ")
            timestamp = dt.isoformat() + "Z"
        except ValueError:
            pass

    # Format 1: multi-profile ("profiles" key)
    for profile_entry in data.get("profiles", []):
        profile_name = profile_entry.get("profile", "")
        for model_entry in profile_entry.get("models", []):
            model_name = model_entry.get("model", "")
            model_results = model_entry.get("results", [])
            runs.append({
                "version": "0.1.0",
                "model": model_name,
                "profile": profile_name,
                "benchmark_suite_version": suite_version,
                "timestamp": timestamp,
                "results": model_results,
            })

    # Format 2: single-profile multi-model ("models" key but no "profiles")
    if not runs and "models" in data and "profiles" not in data:
        for model_entry in data["models"]:
            model_name = model_entry.get("model", "")
            model_results = model_entry.get("results", [])
            runs.append({
                "version": "0.1.0",
                "model": model_name,
                "profile": data.get("profile", ""),
                "benchmark_suite_version": suite_version,
                "timestamp": timestamp,
                "results": model_results,
            })

    # Format 3: flat per-benchmark result
    if not runs and "benchmark" in data and "scores" in data:
        runs.append({
            "version": "0.1.0",
            "model": data.get("model", "unknown"),
            "profile": data.get("profile", ""),
            "benchmark_suite_version": suite_version,
            "timestamp": timestamp,
            "results": [data],
        })

    runs.sort(key=_run_sort_key)
    return runs


def _default_output_timestamp() -> str:
    """Return the timestamp fragment used for default run output paths."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _version_sort_key(version: str) -> tuple[int, ...]:
    """Return a numeric-ish sort key for dotted version strings."""
    parts = []
    for part in version.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _run_sort_key(run: dict) -> tuple[tuple[int, ...], str]:
    """Sort runs by benchmark suite version first, then timestamp."""
    return (
        _version_sort_key(str(run.get("benchmark_suite_version", ""))),
        run.get("timestamp", ""),
    )


def _parse_model_parts(model_name: str) -> tuple[str, str, str | None]:
    """Parse a model name into provider, base model, and reasoning level.

    Handles ``provider/base:level`` format (try ``:``, fallback ``#``,
    handle no level).

    Returns:
        Tuple of ``(provider, base_model, reasoning_level)``.
    """
    if "/" not in model_name:
        return (model_name, model_name, None)

    provider, rest = model_name.split("/", 1)

    # Try ``:`` first (OpenRouter format), fall back to ``#``
    if ":" in rest:
        base_model, level = rest.split(":", 1)
    elif "#" in rest:
        base_model, level = rest.split("#", 1)
    else:
        return (provider, rest, None)

    return (provider, base_model, level if level else None)


def aggregate_runs(runs: list[dict]) -> dict[str, Any]:
    """Aggregate multiple runs into a structured summary for rendering.

    Args:
        runs: List of run envelope dicts.

    Returns:
        Dict with:
        - models: list of model names
        - benchmarks: list of benchmark names
        - model_summaries: {model: {total_runs, total_fixtures, total_passed, pass_at_k}}
        - model_runtimes: {model: {total_ms, avg_ms, min_ms, max_ms, fixture_count}}
        - matrix: {model: {benchmark: {pass_at_k, total, passed, avg_similarity}}}
        - fixtures: {model: {benchmark: [{fixture_id, passed, similarity, error}]}}
        - runs_meta: [{timestamp, model, profile, git_sha, benchmark_suite_version, reasoning_level}]
    """
    models_set: set[str] = set()
    benchmarks_set: set[str] = set()
    model_data: dict[str, dict] = {}

    for run in runs:
        model = run["model"]
        models_set.add(model)

        if model not in model_data:
            model_data[model] = {
                "total_runs": 0,
                "total_fixtures": 0,
                "total_passed": 0,
                "benchmarks": {},
                "api_durations_ms": [],
            }

        model_data[model]["total_runs"] += 1

        for result in run.get("results", []):
            if "error" in result and "benchmark" not in result:
                continue

            bench = result.get("benchmark", "unknown")
            benchmarks_set.add(bench)

            if bench not in model_data[model]["benchmarks"]:
                model_data[model]["benchmarks"][bench] = {
                    "total": 0,
                    "passed": 0,
                    "scores": [],
                    "fixtures": [],
                }

            bd = model_data[model]["benchmarks"][bench]
            bd["total"] += result.get("total", 0)
            bd["passed"] += result.get("passed", 0)

            for score in result.get("scores", []):
                bd["scores"].append(score.get("similarity", 0))
                bd["fixtures"].append({
                    "fixture_id": score.get("fixture_id", "?"),
                    "passed": score.get("passed", False),
                    "similarity": score.get("similarity", 0),
                    "error": score.get("error"),
                    "model_output": score.get("model_output", ""),
                    "reasoning_level": score.get("reasoning_level"),
                    "input_tokens": score.get("input_tokens"),
                    "output_tokens": score.get("output_tokens"),
                    "total_tokens": score.get("total_tokens"),
                    "cost_usd": score.get("cost_usd"),
                    "purpose": score.get("purpose"),
                    "difficulty": score.get("difficulty"),
                    "tags": score.get("tags"),
                    "duration_ms": score.get("duration_ms"),
                    "api_duration_ms": score.get("api_duration_ms"),
                })
                # Report runtime is successful API call latency, not fixture wall time.
                if score.get("api_duration_ms") is not None:
                    model_data[model]["api_durations_ms"].append(
                        score["api_duration_ms"]
                    )

    # Build summaries and matrix
    model_summaries = {}
    matrix = {}
    fixtures = {}

    for model, data in model_data.items():
        model_summaries[model] = {
            "total_runs": data["total_runs"],
            "total_fixtures": data["total_fixtures"],
            "total_passed": data["total_passed"],
            "pass_at_k": round(
                data["total_passed"] / data["total_fixtures"], 4
            ) if data["total_fixtures"] > 0 else 0.0,
            "total_cost_usd": None,
            "avg_cost_usd": None,
        }

        matrix[model] = {}
        fixtures[model] = {}

        model_cost_sum = 0.0
        model_cost_count = 0

        for bench, bd in data["benchmarks"].items():
            avg_sim = round(sum(bd["scores"]) / len(bd["scores"]), 4) if bd["scores"] else 0.0
            matrix[model][bench] = {
                "pass_at_k": round(bd["passed"] / bd["total"], 4) if bd["total"] > 0 else 0.0,
                "total": bd["total"],
                "passed": bd["passed"],
                "avg_similarity": avg_sim,
            }
            fixtures[model][bench] = bd["fixtures"]

            # Collect cost data for this model
            for fx in bd["fixtures"]:
                if fx.get("cost_usd") is not None:
                    model_cost_sum += fx["cost_usd"]
                    model_cost_count += 1

            # Roll up to model summary
            model_summaries[model]["total_fixtures"] += bd["total"]
            model_summaries[model]["total_passed"] += bd["passed"]

        # Recompute pass_at_k after rollup
        sf = model_summaries[model]
        sf["pass_at_k"] = round(
            sf["total_passed"] / sf["total_fixtures"], 4
        ) if sf["total_fixtures"] > 0 else 0.0

        if model_cost_count > 0:
            sf["total_cost_usd"] = round(model_cost_sum, 10)
            sf["avg_cost_usd"] = round(model_cost_sum / model_cost_count, 10)

    # Build model runtime summaries
    model_runtimes: dict[str, dict] = {}
    for model, data in model_data.items():
        durations = data.get("api_durations_ms", [])
        if durations:
            model_runtimes[model] = {
                "total_ms": round(sum(durations), 2),
                "avg_ms": round(sum(durations) / len(durations), 2),
                "min_ms": round(min(durations), 2),
                "max_ms": round(max(durations), 2),
                "fixture_count": len(durations),
            }

    # Build model list with parsed provider + base model + reasoning level
    model_list = []
    for m in sorted(models_set):
        provider, base, rl = _parse_model_parts(m)
        model_list.append({
            "name": m,
            "provider": provider,
            "baseModel": base,
            "reasoningLevel": rl,
        })

    # Build base_model_groups: group by (provider, baseModel)
    groups: dict[tuple[str, str], list[str]] = {}
    for m_data in model_list:
        key = (m_data["provider"], m_data["baseModel"])
        if key not in groups:
            groups[key] = []
        groups[key].append(m_data["name"])

    base_model_groups = []
    for (provider, base), model_names in groups.items():
        levels = []
        for mn in sorted(model_names):
            _, _, level = _parse_model_parts(mn)
            ms = model_summaries.get(mn, {})
            levels.append({
                "level": level,
                "modelName": mn,
                "pass_at_k": ms.get("pass_at_k", 0),
                "total_cost_usd": ms.get("total_cost_usd"),
            })
        levels.sort(key=lambda l: (l["level"] or ""))
        base_model_groups.append({
            "provider": provider,
            "baseModel": base,
            "levels": levels,
        })

    runs_meta = []
    for run in runs:
        model_name = run.get("model", "")
        _, rl = parse_model_name(model_name)
        runs_meta.append({
            "timestamp": run.get("timestamp", ""),
            "model": run.get("model", ""),
            "profile": run.get("profile", ""),
            "git_sha": run.get("git_sha", ""),
            "benchmark_suite_version": run.get("benchmark_suite_version", ""),
            "reasoning_level": rl or "",
        })

    # Build fixture index: "benchmark/fixture_id" → metadata
    # Fixture IDs are only unique within their benchmark
    fixture_index: dict[str, dict] = {}
    for run in runs:
        for result in run.get("results", []):
            bench = result.get("benchmark", "")
            for score in result.get("scores", []):
                fid = score.get("fixture_id", "")
                key = f"{bench}/{fid}"
                if fid and key not in fixture_index:
                    fixture_index[key] = {
                        "id": fid,
                        "benchmark": bench,
                        "prompt": score.get("prompt") or "",
                        "expected": score.get("expected") or "",
                        "description": score.get("description") or "",
                        "setup": score.get("setup") or [],
                        "purpose": score.get("purpose") or "",
                        "difficulty": score.get("difficulty") or "",
                        "tags": score.get("tags") or [],
                    }

    # Fall back: load any missing fixture metadata from YAML files
    _supplement_fixture_index_from_yaml(fixture_index)

    # Filter out the "unknown" model from all collections
    model_summaries.pop("unknown", None)
    model_runtimes.pop("unknown", None)
    matrix.pop("unknown", None)
    fixtures.pop("unknown", None)
    model_list = [m for m in model_list if m["name"] != "unknown"]
    runs_meta = [r for r in runs_meta if r["model"] != "unknown"]
    base_model_groups = [
        group
        for group in base_model_groups
        if group["provider"] != "unknown"
        and group["baseModel"] != "unknown"
        and all(level["modelName"] != "unknown" for level in group["levels"])
    ]

    return {
        "models": model_list,
        "benchmarks": sorted(benchmarks_set),
        "model_summaries": model_summaries,
        "model_runtimes": model_runtimes,
        "matrix": matrix,
        "fixtures": fixtures,
        "fixture_index": fixture_index,
        "runs_meta": runs_meta,
        "base_model_groups": base_model_groups,
    }


def render_json(data: dict[str, Any], output_path: str) -> None:
    """Write aggregated data as JSON for the Astro UI.

    Args:
        data: Aggregated data from aggregate_runs().
        output_path: Path to write the JSON file to.
    """
    import json as _json

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(data, indent=2, default=str))


def write_sqlite_report_db(
    data: dict[str, Any],
    output_path: str | Path = REPORT_DB_PATH,
    schema_path: str | Path = REPORT_SCHEMA_PATH,
) -> None:
    """Rebuild the generated SQLite report database from aggregate data."""
    db_path = Path(output_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    schema = Path(schema_path).read_text()
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema)
        _insert_report_data(conn, data)
        conn.execute("ANALYZE")


def _json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else [], separators=(",", ":"))


def _insert_report_data(conn: sqlite3.Connection, data: dict[str, Any]) -> None:
    models = data.get("models", [])
    benchmarks = data.get("benchmarks", [])

    conn.executemany(
        """
        INSERT INTO models (name, provider, base_model, reasoning_level)
        VALUES (:name, :provider, :baseModel, :reasoningLevel)
        """,
        models,
    )
    conn.executemany(
        "INSERT INTO benchmarks (name) VALUES (?)",
        [(name,) for name in benchmarks],
    )

    conn.executemany(
        """
        INSERT INTO model_summaries (
          model_name, total_runs, total_fixtures, total_passed, pass_at_k,
          total_cost_usd, avg_cost_usd
        )
        VALUES (
          :model_name, :total_runs, :total_fixtures, :total_passed, :pass_at_k,
          :total_cost_usd, :avg_cost_usd
        )
        """,
        [
            {"model_name": model_name, **summary}
            for model_name, summary in data.get("model_summaries", {}).items()
        ],
    )

    conn.executemany(
        """
        INSERT INTO model_runtimes (
          model_name, total_ms, avg_ms, min_ms, max_ms, fixture_count
        )
        VALUES (:model_name, :total_ms, :avg_ms, :min_ms, :max_ms, :fixture_count)
        """,
        [
            {"model_name": model_name, **runtime}
            for model_name, runtime in data.get("model_runtimes", {}).items()
        ],
    )

    conn.executemany(
        """
        INSERT INTO benchmark_summaries (
          model_name, benchmark_name, pass_at_k, total, passed, avg_similarity
        )
        VALUES (
          :model_name, :benchmark_name, :pass_at_k, :total, :passed, :avg_similarity
        )
        """,
        [
            {"model_name": model_name, "benchmark_name": benchmark, **cell}
            for model_name, by_benchmark in data.get("matrix", {}).items()
            for benchmark, cell in by_benchmark.items()
        ],
    )

    fixture_rows = []
    tag_rows = []
    for fixture in data.get("fixture_index", {}).values():
        benchmark = fixture.get("benchmark", "")
        fixture_id = fixture.get("id", "")
        fixture_rows.append(
            {
                "benchmark_name": benchmark,
                "fixture_id": fixture_id,
                "prompt": fixture.get("prompt") or "",
                "expected": fixture.get("expected") or "",
                "description": fixture.get("description") or "",
                "setup_json": _json_dumps(fixture.get("setup")),
                "purpose": fixture.get("purpose") or "",
                "difficulty": fixture.get("difficulty") or "",
            }
        )
        for tag in fixture.get("tags") or []:
            tag_rows.append((benchmark, fixture_id, tag))

    conn.executemany(
        """
        INSERT INTO fixtures (
          benchmark_name, fixture_id, prompt, expected, description, setup_json,
          purpose, difficulty
        )
        VALUES (
          :benchmark_name, :fixture_id, :prompt, :expected, :description,
          :setup_json, :purpose, :difficulty
        )
        """,
        fixture_rows,
    )
    conn.executemany(
        """
        INSERT INTO fixture_tags (benchmark_name, fixture_id, tag)
        VALUES (?, ?, ?)
        """,
        tag_rows,
    )

    result_rows = []
    for model_name, by_benchmark in data.get("fixtures", {}).items():
        for benchmark, fixtures in by_benchmark.items():
            for result in fixtures:
                result_rows.append(
                    {
                        "model_name": model_name,
                        "benchmark_name": benchmark,
                        "fixture_id": result.get("fixture_id", ""),
                        "passed": 1 if result.get("passed") else 0,
                        "similarity": result.get("similarity") or 0,
                        "error": result.get("error"),
                        "model_output": result.get("model_output") or "",
                        "reasoning_level": result.get("reasoning_level"),
                        "input_tokens": result.get("input_tokens"),
                        "output_tokens": result.get("output_tokens"),
                        "total_tokens": result.get("total_tokens"),
                        "cost_usd": result.get("cost_usd"),
                        "duration_ms": result.get("duration_ms"),
                        "api_duration_ms": result.get("api_duration_ms"),
                        "purpose": result.get("purpose"),
                        "difficulty": result.get("difficulty"),
                        "tags_json": _json_dumps(result.get("tags")),
                    }
                )

    conn.executemany(
        """
        INSERT INTO fixture_results (
          model_name, benchmark_name, fixture_id, passed, similarity, error,
          model_output, reasoning_level, input_tokens, output_tokens, total_tokens,
          cost_usd, duration_ms, api_duration_ms, purpose, difficulty, tags_json
        )
        VALUES (
          :model_name, :benchmark_name, :fixture_id, :passed, :similarity, :error,
          :model_output, :reasoning_level, :input_tokens, :output_tokens,
          :total_tokens, :cost_usd, :duration_ms, :api_duration_ms, :purpose,
          :difficulty, :tags_json
        )
        """,
        result_rows,
    )

    conn.executemany(
        """
        INSERT INTO runs (
          timestamp, model_name, profile, git_sha, benchmark_suite_version,
          reasoning_level
        )
        VALUES (
          :timestamp, :model, :profile, :git_sha, :benchmark_suite_version,
          :reasoning_level
        )
        """,
        data.get("runs_meta", []),
    )

    for group in data.get("base_model_groups", []):
        cursor = conn.execute(
            """
            INSERT INTO base_model_groups (provider, base_model)
            VALUES (?, ?)
            """,
            (group.get("provider", ""), group.get("baseModel", "")),
        )
        group_id = cursor.lastrowid
        conn.executemany(
            """
            INSERT INTO base_model_group_levels (
              group_id, level, model_name, pass_at_k, total_cost_usd
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    group_id,
                    level.get("level"),
                    level.get("modelName", ""),
                    level.get("pass_at_k", 0),
                    level.get("total_cost_usd"),
                )
                for level in group.get("levels", [])
            ],
        )


def _supplement_fixture_index_from_yaml(fixture_index: dict[str, dict]) -> None:
    """Fill in missing fixture metadata by loading YAML fixture files.

    Only fills fields that are missing in the index.
    """
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    if not fixtures_dir.exists():
        return

    for key, entry in fixture_index.items():
        fid = entry.get("id", "")
        bench = entry.get("benchmark", "")
        if not fid or not bench:
            continue

        needs_yaml = (
            not entry.get("prompt")
            or not entry.get("expected")
            or not entry.get("description")
            or not entry.get("setup")
            or not entry.get("purpose")
            or not entry.get("difficulty")
            or not entry.get("tags")
        )
        if not needs_yaml:
            continue

        # Try to find the fixture YAML file
        yaml_path = fixtures_dir / bench / f"{fid}.yaml"
        if not yaml_path.exists():
            continue

        try:
            import yaml
            data = yaml.safe_load(yaml_path.read_text())
            if isinstance(data, dict):
                entry["prompt"] = entry.get("prompt") or data.get("prompt", "")
                entry["expected"] = entry.get("expected") or data.get("expected", "")
                entry["description"] = entry.get("description") or data.get("description", "")
                entry["setup"] = entry.get("setup") or data.get("setup", [])
                entry["purpose"] = entry["purpose"] or data.get("purpose", "")
                entry["difficulty"] = entry["difficulty"] or data.get("difficulty", "")
                entry["tags"] = entry["tags"] or data.get("tags", [])
        except Exception as exc:
            logger.debug("Failed to load YAML for fixture %s: %s", fid, exc)
