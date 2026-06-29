"""Tests for GitBench render module."""

import json
import sqlite3

import pytest

from gitbench.render import (
    REPORT_SCHEMA_PATH,
    aggregate_runs,
    load_campaign_reports_from_dir,
    load_runs_from_combined,
    load_runs_from_dir,
    load_runs_from_jsonl,
    render_json,
    write_sqlite_report_db,
)

from gitbench.version import BENCHMARK_SUITE_VERSION


def _make_envelope(
    model="mock",
    bench="commit_messages",
    total=12,
    passed=10,
    timestamp="2026-04-25T13:00:00+00:00",
    suite_version=BENCHMARK_SUITE_VERSION,
):
    """Build a minimal run envelope for testing."""
    scores = [
        {
            "fixture_id": f"f{i:03d}",
            "passed": i < passed,
            "similarity": 0.9 if i < passed else 0.3,
            "model_output": "test output",
            "error": None,
        }
        for i in range(total)
    ]
    return {
        "version": 1,
        "benchmark_suite_version": suite_version,
        "timestamp": timestamp,
        "git_sha": "abc123",
        "model": model,
        "profile": "(inline)",
        "summary": {
            "total_benchmarks": 1,
            "total_fixtures": total,
            "total_passed": passed,
            "overall_pass_at_k": round(passed / total, 4),
        },
        "results": [
            {
                "benchmark": bench,
                "total": total,
                "passed": passed,
                "pass_at_k": round(passed / total, 4),
                "scores": scores,
                "errors": 0,
            }
        ],
    }


def _make_envelope_with_scores(
    scores,
    model="mock",
    bench="commit_messages",
    timestamp="2026-04-25T13:00:00+00:00",
):
    """Build a run envelope using explicit fixture scores."""
    total = len(scores)
    passed = sum(1 for score in scores if score.get("passed"))
    envelope = _make_envelope(
        model=model,
        bench=bench,
        total=total,
        passed=passed,
        timestamp=timestamp,
    )
    envelope["results"][0]["scores"] = scores
    return envelope


class TestLoadRunsFromDir:
    """Tests for load_runs_from_dir."""

    def test_loads_json_files(self, tmp_path):
        """Test that JSON files are loaded from directory."""
        run = _make_envelope()
        (tmp_path / "run1.json").write_text(json.dumps(run))

        runs = load_runs_from_dir(str(tmp_path))
        assert len(runs) == 1
        assert runs[0]["model"] == "mock"

    def test_skips_invalid_json(self, tmp_path):
        """Test that invalid JSON files are skipped."""
        (tmp_path / "bad.json").write_text("not json")
        (tmp_path / "good.json").write_text(json.dumps(_make_envelope()))

        runs = load_runs_from_dir(str(tmp_path))
        assert len(runs) == 1

    def test_skips_non_envelope_json(self, tmp_path):
        """Test that JSON without version/results keys is skipped."""
        (tmp_path / "other.json").write_text(json.dumps({"foo": "bar"}))

        runs = load_runs_from_dir(str(tmp_path))
        assert len(runs) == 0

    def test_raises_on_missing_dir(self):
        """Test that missing directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_runs_from_dir("/nonexistent/path")

    def test_sorted_by_version_then_timestamp(self, tmp_path):
        """Test that runs are sorted by suite version before timestamp."""
        r1 = _make_envelope(
            timestamp="2026-04-25T15:00:00+00:00",
            suite_version="0.1.0",
        )
        r2 = _make_envelope(
            timestamp="2026-04-25T13:00:00+00:00",
            suite_version="0.1.0",
        )
        r3 = _make_envelope(
            timestamp="2026-04-25T12:00:00+00:00",
            suite_version="0.2.0",
        )
        (tmp_path / "later.json").write_text(json.dumps(r1))
        (tmp_path / "earlier.json").write_text(json.dumps(r2))
        (tmp_path / "newer-version.json").write_text(json.dumps(r3))

        runs = load_runs_from_dir(str(tmp_path))
        assert [r["benchmark_suite_version"] for r in runs] == ["0.1.0", "0.1.0", "0.2.0"]
        assert runs[0]["timestamp"] < runs[1]["timestamp"]


class TestLoadRunsFromCombined:
    """Tests for loading legacy combined and raw report input files."""

    def test_loads_raw_run_envelope(self, tmp_path):
        run = _make_envelope(model="openai/gpt-test:high")
        path = tmp_path / f"results-v{BENCHMARK_SUITE_VERSION}.json"
        path.write_text(json.dumps(run))

        runs = load_runs_from_combined(str(path))

        assert len(runs) == 1
        assert runs[0]["model"] == "openai/gpt-test:high"
        assert runs[0]["results"][0]["benchmark"] == "commit_messages"

    def test_ignores_aggregate_report_json(self, tmp_path):
        aggregate = aggregate_runs([_make_envelope(model="openai/gpt-test:high")])
        path = tmp_path / f"results-v{BENCHMARK_SUITE_VERSION}.json"
        path.write_text(json.dumps(aggregate))

        runs = load_runs_from_combined(str(path))

        assert runs == []

    def test_loads_same_timestamp_modes_without_empty_model_identity(self, tmp_path):
        combined = {
            "benchmark_suite_version": BENCHMARK_SUITE_VERSION,
            "profile": "(inline)",
            "models": [
                {
                    "model": "openai/gpt-test:high",
                    "results": _make_envelope(
                        model="openai/gpt-test:high",
                        passed=1,
                    )["results"],
                },
                {
                    "model": "openai/gpt-test:high",
                    "output_mode": "json_schema",
                    "results": _make_envelope(
                        model="openai/gpt-test:high",
                        passed=0,
                    )["results"],
                },
            ],
        }
        path = tmp_path / f"results-v{BENCHMARK_SUITE_VERSION}.json"
        path.write_text(json.dumps(combined))

        runs = load_runs_from_combined(str(path))

        assert len(runs) == 2
        assert {run["model"] for run in runs} == {"openai/gpt-test:high"}
        assert {run["output_mode"] for run in runs} == {"text", "json_schema"}
        assert "" not in {run["model"] for run in runs}


class TestLoadRunsFromJsonl:
    """Tests for load_runs_from_jsonl."""

    def test_loads_jsonl(self, tmp_path):
        """Test that JSONL lines are loaded."""
        p = tmp_path / "runs.jsonl"
        lines = [json.dumps(_make_envelope()), json.dumps(_make_envelope(model="gpt-4o"))]
        p.write_text("\n".join(lines))

        runs = load_runs_from_jsonl(str(p))
        assert len(runs) == 2

    def test_skips_blank_lines(self, tmp_path):
        """Test that blank lines are skipped."""
        p = tmp_path / "runs.jsonl"
        p.write_text(json.dumps(_make_envelope()) + "\n\n\n")

        runs = load_runs_from_jsonl(str(p))
        assert len(runs) == 1

    def test_raises_on_missing_file(self):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_runs_from_jsonl("/nonexistent/file.jsonl")


class TestAggregateRuns:
    """Tests for aggregate_runs."""

    def test_single_run(self):
        """Test aggregation of a single run."""
        runs = [_make_envelope(passed=10)]
        data = aggregate_runs(runs)

        assert any(m["name"] == "mock" for m in data["models"])
        assert "commit_messages" in data["benchmarks"]
        assert data["model_summaries"]["mock"]["total_passed"] == 10
        assert data["matrix"]["mock"]["commit_messages"]["pass_at_k"] == round(10 / 12, 4)

    def test_multiple_models(self):
        """Test aggregation across multiple models."""
        runs = [
            _make_envelope(model="mock", passed=10),
            _make_envelope(model="gpt-4o", passed=12),
        ]
        data = aggregate_runs(runs)

        assert len(data["models"]) == 2
        assert any(m["name"] == "mock" for m in data["models"])
        assert any(m["name"] == "gpt-4o" for m in data["models"])

        assert data["model_summaries"]["mock"]["total_passed"] == 10
        assert data["model_summaries"]["gpt-4o"]["total_passed"] == 12

    def test_multiple_benchmarks(self):
        """Test aggregation across multiple benchmarks."""
        runs = [
            _make_envelope(bench="commit_messages", passed=10),
            _make_envelope(bench="rebase", passed=8, timestamp="2026-04-25T14:00:00+00:00"),
        ]
        # Both runs are for the same model, different benchmarks
        data = aggregate_runs(runs)

        assert len(data["benchmarks"]) == 2
        assert "commit_messages" in data["benchmarks"]
        assert "rebase" in data["benchmarks"]

    def test_fixtures_populated(self):
        """Test that per-fixture data is populated."""
        runs = [_make_envelope(passed=5)]
        data = aggregate_runs(runs)

        fixtures = data["fixtures"]["mock"]["commit_messages"]
        assert len(fixtures) == 12
        assert fixtures[0]["fixture_id"] == "f000"
        assert fixtures[0]["passed"] is True
        assert fixtures[4]["passed"] is True
        assert fixtures[5]["passed"] is False

    def test_runs_meta(self):
        """Test that run metadata is extracted."""
        runs = [_make_envelope(model="llama3.1:8b")]
        data = aggregate_runs(runs)

        assert len(data["runs_meta"]) == 1
        assert data["runs_meta"][0]["model"] == "llama3.1:8b"
        assert data["runs_meta"][0]["git_sha"] == "abc123"
        assert data["runs_meta"][0]["benchmark_suite_version"] == BENCHMARK_SUITE_VERSION

    def test_unknown_model_filtered_from_base_model_groups(self):
        """Test that the placeholder unknown model is filtered everywhere."""
        runs = [
            _make_envelope(model="unknown"),
            _make_envelope(model="openai/gpt-5.4:medium"),
        ]

        data = aggregate_runs(runs)

        assert all(model["name"] != "unknown" for model in data["models"])
        assert "unknown" not in data["model_summaries"]
        assert "unknown" not in data["matrix"]
        assert "unknown" not in data["fixtures"]
        assert all(meta["model"] != "unknown" for meta in data["runs_meta"])
        assert all(group["provider"] != "unknown" for group in data["base_model_groups"])
        assert all(group["baseModel"] != "unknown" for group in data["base_model_groups"])
        assert all(
            level["modelName"] != "unknown"
            for group in data["base_model_groups"]
            for level in group["levels"]
        )

    def test_model_runtimes_use_api_duration_ms(self):
        """Test that model runtime totals are aggregated from API durations."""
        runs = [
            _make_envelope_with_scores(
                [
                    {
                        "fixture_id": "f001",
                        "passed": True,
                        "similarity": 1,
                        "duration_ms": 1000,
                        "api_duration_ms": 100,
                    },
                    {
                        "fixture_id": "f002",
                        "passed": True,
                        "similarity": 1,
                        "duration_ms": 2000,
                        "api_duration_ms": 200,
                    },
                    {
                        "fixture_id": "f003",
                        "passed": True,
                        "similarity": 1,
                        "duration_ms": 3000,
                        "api_duration_ms": 300,
                    },
                ]
            )
        ]

        data = aggregate_runs(runs)

        assert data["model_runtimes"]["mock"] == {
            "total_ms": 600,
            "avg_ms": 200,
            "min_ms": 100,
            "max_ms": 300,
            "fixture_count": 3,
        }
        assert (
            data["fixtures"]["mock"]["commit_messages"][0]["api_duration_ms"]
            == 100
        )

    def test_model_runtimes_exclude_null_api_duration_ms(self):
        """Test that null and missing API durations do not count."""
        runs = [
            _make_envelope_with_scores(
                [
                    {
                        "fixture_id": "f001",
                        "passed": True,
                        "similarity": 1,
                        "duration_ms": 1000,
                        "api_duration_ms": 100,
                    },
                    {
                        "fixture_id": "f002",
                        "passed": True,
                        "similarity": 1,
                        "duration_ms": 2000,
                        "api_duration_ms": None,
                    },
                    {
                        "fixture_id": "f003",
                        "passed": True,
                        "similarity": 1,
                        "duration_ms": 3000,
                    },
                    {
                        "fixture_id": "f004",
                        "passed": True,
                        "similarity": 1,
                        "duration_ms": 4000,
                        "api_duration_ms": 500,
                    },
                ]
            )
        ]

        data = aggregate_runs(runs)

        assert data["model_runtimes"]["mock"]["total_ms"] == 600
        assert data["model_runtimes"]["mock"]["avg_ms"] == 300
        assert data["model_runtimes"]["mock"]["fixture_count"] == 2

    def test_model_runtimes_never_fall_back_to_duration_ms(self):
        """Test that wall-clock durations are not used as runtime fallback."""
        runs = [
            _make_envelope_with_scores(
                [
                    {
                        "fixture_id": "f001",
                        "passed": True,
                        "similarity": 1,
                        "duration_ms": 1000,
                    },
                    {
                        "fixture_id": "f002",
                        "passed": True,
                        "similarity": 1,
                        "duration_ms": 2000,
                        "api_duration_ms": None,
                    },
                ]
            )
        ]

        data = aggregate_runs(runs)

        assert "mock" not in data["model_runtimes"]


    def test_output_mode_defaults_to_text(self):
        """Test that missing output_mode defaults to 'text'."""
        runs = [_make_envelope(model="gpt-4o")]
        data = aggregate_runs(runs)

        model = next(m for m in data["models"] if m["name"] == "gpt-4o")
        assert model["output_mode"] == "text"

    def test_text_and_json_schema_remain_separate_variants(self):
        """Test that text and json_schema runs for same model are separate variants."""
        text_env = _make_envelope(model="gpt-4o", passed=10, timestamp="2026-04-25T13:00:00+00:00")
        text_env["output_mode"] = "text"
        json_env = _make_envelope(model="gpt-4o", passed=8, timestamp="2026-04-25T14:00:00+00:00")
        json_env["output_mode"] = "json_schema"

        data = aggregate_runs([text_env, json_env])

        # Two model entries for the same base model
        model_names = [m["name"] for m in data["models"]]
        assert "gpt-4o" in model_names  # text mode keeps original name
        assert "gpt-4o__json_schema" in model_names  # json_schema gets suffix

        # Different pass rates
        assert data["model_summaries"]["gpt-4o"]["total_passed"] == 10
        assert data["model_summaries"]["gpt-4o__json_schema"]["total_passed"] == 8

        # Separate matrix entries
        assert data["matrix"]["gpt-4o"]["commit_messages"]["passed"] == 10
        assert data["matrix"]["gpt-4o__json_schema"]["commit_messages"]["passed"] == 8

    def test_output_mode_text_and_json_schema_have_separate_model_summaries(self):
        """Test that model summaries don't merge across output modes."""
        text_env = _make_envelope(model="gpt-4o", passed=12, total=12)
        text_env["output_mode"] = "text"
        json_env = _make_envelope(model="gpt-4o", passed=6, total=12)
        json_env["output_mode"] = "json_schema"

        data = aggregate_runs([text_env, json_env])

        assert "gpt-4o" in data["model_summaries"]
        assert "gpt-4o__json_schema" in data["model_summaries"]
        assert data["model_summaries"]["gpt-4o"]["pass_at_k"] == 1.0
        assert data["model_summaries"]["gpt-4o__json_schema"]["pass_at_k"] == 0.5

    def test_output_mode_in_runs_meta(self):
        """Test that runs_meta includes output_mode for each run."""
        text_env = _make_envelope(model="gpt-4o", timestamp="2026-04-25T13:00:00+00:00")
        text_env["output_mode"] = "text"
        json_env = _make_envelope(model="gpt-4o", timestamp="2026-04-25T14:00:00+00:00")
        json_env["output_mode"] = "json_schema"

        data = aggregate_runs([text_env, json_env])

        modes = {r["output_mode"] for r in data["runs_meta"]}
        assert modes == {"text", "json_schema"}

    def test_output_mode_base_model_groups_preserve_variants(self):
        """Test that base model groups contain both output mode variants."""
        text_env = _make_envelope(model="openai/gpt-5:medium", passed=10)
        text_env["output_mode"] = "text"
        json_env = _make_envelope(model="openai/gpt-5:medium", passed=7)
        json_env["output_mode"] = "json_schema"

        data = aggregate_runs([text_env, json_env])

        groups = [g for g in data["base_model_groups"] if g["provider"] == "openai"]
        assert len(groups) == 1
        levels = groups[0]["levels"]
        model_names = {l["modelName"] for l in levels}
        assert "openai/gpt-5:medium" in model_names
        assert "openai/gpt-5:medium__json_schema" in model_names

    def test_text_mode_excludes_suffix_in_model_name(self):
        """Test that text mode models use the original name without '__text' suffix."""
        text_env = _make_envelope(model="gpt-4o", passed=10)
        text_env["output_mode"] = "text"

        data = aggregate_runs([text_env])

        model_names = [m["name"] for m in data["models"]]
        assert "gpt-4o" in model_names
        assert "gpt-4o__text" not in model_names


class TestRenderJson:
    """Tests for render_json."""

    def test_writes_json_file(self, tmp_path):
        """Test that render_json writes a valid JSON file."""
        runs = [_make_envelope()]
        data = aggregate_runs(runs)
        output = tmp_path / "results.json"

        render_json(data, str(output))

        assert output.exists()
        written = json.loads(output.read_text())
        assert "models" in written
        assert "benchmarks" in written
        assert "model_summaries" in written

    def test_creates_parent_directories(self, tmp_path):
        """Test that render_json creates parent directories."""
        runs = [_make_envelope()]
        data = aggregate_runs(runs)
        output = tmp_path / "nested" / "deep" / "results.json"

        render_json(data, str(output))

        assert output.exists()

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_rejects_non_finite_values(self, tmp_path, value):
        output = tmp_path / "results.json"

        with pytest.raises(ValueError, match="Out of range float values"):
            render_json({"value": value}, str(output))

        assert not output.exists()

    def test_output_uses_browser_compatible_json(self, tmp_path):
        output = tmp_path / "results.json"
        render_json({"nested": {"values": [1, 2.5, None]}}, str(output))

        parsed = json.loads(
            output.read_text(),
            parse_constant=lambda value: pytest.fail(
                f"browser-incompatible JSON constant: {value}"
            ),
        )
        assert parsed == {"nested": {"values": [1, 2.5, None]}}

    def test_invalid_structured_result_drops_parsed_payload(self, tmp_path):
        raw_output = '{"unexpected":"value"}'
        envelope = _make_envelope_with_scores(
            [
                {
                    "fixture_id": "f001",
                    "passed": False,
                    "similarity": 0,
                    "model_output": raw_output,
                    "output_mode": "json_schema",
                    "parsed_payload": {"unexpected": "value"},
                    "raw_structured_output": raw_output,
                    "structured_error": "Structured output schema validation failed",
                }
            ]
        )
        data = aggregate_runs([envelope])
        output = tmp_path / "results.json"

        render_json(data, str(output))

        fixture = json.loads(output.read_text())["fixtures"]["mock"][
            "commit_messages"
        ][0]
        assert fixture["parsed_payload"] is None
        assert fixture["model_output"] == raw_output
        assert fixture["raw_structured_output"] == raw_output
        assert fixture["structured_error"].startswith("Structured output schema")

    def test_writes_models_as_objects(self, tmp_path):
        """Test that models are written as objects with name, baseModel, reasoningLevel."""
        runs = [_make_envelope(model="openai/o3-mini:high")]
        data = aggregate_runs(runs)
        output = tmp_path / "results.json"

        render_json(data, str(output))

        written = json.loads(output.read_text())
        models = written["models"]
        assert len(models) == 1
        assert models[0]["name"] == "openai/o3-mini:high"
        assert models[0]["baseModel"] == "o3-mini"
        assert models[0]["reasoningLevel"] == "high"

    def test_model_without_reasoning_level_has_null(self, tmp_path):
        """Test that a model without #suffix has reasoningLevel null."""
        runs = [_make_envelope(model="claude-sonnet")]
        data = aggregate_runs(runs)
        output = tmp_path / "results.json"

        render_json(data, str(output))

        written = json.loads(output.read_text())
        models = written["models"]
        assert models[0]["name"] == "claude-sonnet"
        assert models[0]["baseModel"] == "claude-sonnet"
        assert models[0]["reasoningLevel"] is None

    def test_model_outputs_not_truncated(self, tmp_path):
        """Test that long model outputs are included in full, not truncated."""
        long_output = "x" * 500
        scores = [
            {
                "fixture_id": "f000",
                "passed": True,
                "similarity": 0.9,
                "model_output": long_output,
                "error": None,
            }
        ]
        env = {
            "version": 1,
            "benchmark_suite_version": BENCHMARK_SUITE_VERSION,
            "timestamp": "2026-04-25T13:00:00+00:00",
            "git_sha": "abc123",
            "model": "gpt-4o",
            "profile": "(inline)",
            "summary": {"total_benchmarks": 1, "total_fixtures": 1, "total_passed": 1, "overall_pass_at_k": 1.0},
            "results": [
                {
                    "benchmark": "commit_messages",
                    "total": 1,
                    "passed": 1,
                    "pass_at_k": 1.0,
                    "scores": scores,
                    "errors": 0,
                }
            ],
        }
        data = aggregate_runs([env])
        output = tmp_path / "results.json"

        render_json(data, str(output))

        written = json.loads(output.read_text())
        fixture = written["fixtures"]["gpt-4o"]["commit_messages"][0]
        assert fixture["model_output"] == long_output
        assert len(fixture["model_output"]) == 500

    def test_multiple_runs_same_model_kept_separate(self, tmp_path):
        """Test that multiple runs of the same model produce distinct runs_meta entries."""
        runs = [
            _make_envelope(model="gpt-4o", timestamp="2026-04-25T13:00:00+00:00"),
            _make_envelope(model="gpt-4o", timestamp="2026-04-25T15:00:00+00:00"),
        ]
        data = aggregate_runs(runs)
        output = tmp_path / "results.json"

        render_json(data, str(output))

        written = json.loads(output.read_text())
        assert len(written["runs_meta"]) == 2
        assert written["runs_meta"][0]["timestamp"] != written["runs_meta"][1]["timestamp"]

    def test_writes_fixture_api_duration_ms(self, tmp_path):
        """Test that render_json includes fixture API duration values."""
        runs = [
            _make_envelope_with_scores(
                [
                    {
                        "fixture_id": "f001",
                        "passed": True,
                        "similarity": 1,
                        "duration_ms": 1000,
                        "api_duration_ms": 350.2,
                    },
                    {
                        "fixture_id": "f002",
                        "passed": True,
                        "similarity": 1,
                        "duration_ms": 2000,
                    },
                ]
            )
        ]
        data = aggregate_runs(runs)
        output = tmp_path / "results.json"

        render_json(data, str(output))

        written = json.loads(output.read_text())
        fixtures = written["fixtures"]["mock"]["commit_messages"]
        assert fixtures[0]["api_duration_ms"] == 350.2
        assert fixtures[1]["api_duration_ms"] is None
        assert written["model_runtimes"]["mock"]["total_ms"] == 350.2


class TestAggregateRunsFixtureIndex:
    """Tests for fixture_index in aggregate_runs."""

    def test_fixture_index_has_metadata(self):
        """Test that fixture_index contains prompt, expected, description fields."""
        scores = [
            {
                "fixture_id": "f001",
                "passed": True,
                "similarity": 0.95,
                "model_output": "git commit -m 'fix'",
                "error": None,
                "prompt": "Write a commit message for this diff",
                "expected": "fix: resolve null pointer in parser",
                "description": "Test commit message generation",
                "setup": ["git init", "touch parser.py", "git add parser.py"],
                "purpose": "Tests the model's ability to generate concise commit messages",
                "difficulty": "easy",
                "tags": ["commit", "basic"],
                "reasoning_level": None,
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            }
        ]
        envelope = {
            "version": 1,
            "benchmark_suite_version": BENCHMARK_SUITE_VERSION,
            "timestamp": "2026-04-25T13:00:00+00:00",
            "git_sha": "abc123",
            "model": "gpt-4o",
            "profile": "(inline)",
            "summary": {"total_benchmarks": 1, "total_fixtures": 1, "total_passed": 1, "overall_pass_at_k": 1.0},
            "results": [
                {
                    "benchmark": "commit_messages",
                    "total": 1,
                    "passed": 1,
                    "pass_at_k": 1.0,
                    "scores": scores,
                    "errors": 0,
                }
            ],
        }
        data = aggregate_runs([envelope])

        assert "commit_messages/f001" in data["fixture_index"]
        fi = data["fixture_index"]["commit_messages/f001"]
        assert fi["prompt"] == "Write a commit message for this diff"
        assert fi["expected"] == "fix: resolve null pointer in parser"
        assert fi["description"] == "Test commit message generation"
        assert fi["setup"] == ["git init", "touch parser.py", "git add parser.py"]
        assert fi["purpose"] == "Tests the model's ability to generate concise commit messages"
        assert fi["difficulty"] == "easy"
        assert fi["tags"] == ["commit", "basic"]
        assert fi["id"] == "f001"
        assert fi["benchmark"] == "commit_messages"

    def test_fixtures_include_metadata_fields(self):
        """Test that per-fixture data includes purpose, difficulty, tags."""
        scores = [
            {
                "fixture_id": "f001",
                "passed": True,
                "similarity": 0.9,
                "model_output": "output",
                "error": None,
                "purpose": "Test purpose",
                "difficulty": "medium",
                "tags": ["rebase", "conflict"],
                "reasoning_level": "high",
                "input_tokens": 200,
                "output_tokens": 100,
                "total_tokens": 300,
            }
        ]
        envelope = {
            "version": 1,
            "benchmark_suite_version": BENCHMARK_SUITE_VERSION,
            "timestamp": "2026-04-25T13:00:00+00:00",
            "git_sha": "abc123",
            "model": "gpt-4o",
            "profile": "(inline)",
            "summary": {"total_benchmarks": 1, "total_fixtures": 1, "total_passed": 1, "overall_pass_at_k": 1.0},
            "results": [
                {
                    "benchmark": "rebase",
                    "total": 1,
                    "passed": 1,
                    "pass_at_k": 1.0,
                    "scores": scores,
                    "errors": 0,
                }
            ],
        }
        data = aggregate_runs([envelope])

        fixture = data["fixtures"]["gpt-4o"]["rebase"][0]
        assert fixture["purpose"] == "Test purpose"
        assert fixture["difficulty"] == "medium"
        assert fixture["tags"] == ["rebase", "conflict"]
        assert fixture["reasoning_level"] == "high"
        assert fixture["input_tokens"] == 200
        assert fixture["output_tokens"] == 100
        assert fixture["total_tokens"] == 300


class TestLegacySqliteReportDbHelper:
    """Parity tests for the legacy Python SQLite helper."""

    def test_schema_includes_expected_indexes(self):
        """Test that common report access path indexes are checked in."""
        schema = REPORT_SCHEMA_PATH.read_text()

        for index_name in [
            "idx_fixture_results_model_benchmark",
            "idx_fixture_results_model_difficulty",
            "idx_fixture_results_benchmark_fixture",
            "idx_fixture_results_benchmark_model_fixture",
            "idx_fixtures_benchmark",
            "idx_fixture_tags_tag_fixture",
            "idx_fixture_tags_benchmark_tag",
            "idx_runs_model_timestamp",
            "idx_runs_version_timestamp",
            "idx_models_grouping",
            "idx_benchmark_summaries_model_benchmark",
            "idx_benchmark_summaries_leaderboard",
            "idx_base_model_group_levels_group_level",
        ]:
            assert index_name in schema

    def test_writes_database_with_aggregate_counts(self, tmp_path):
        """Test that aggregate JSON counts are preserved in SQLite tables."""
        data = aggregate_runs([
            _make_envelope(model="openai/gpt-5:medium", passed=10),
            _make_envelope(model="anthropic/claude", passed=8),
        ])
        db_path = tmp_path / "gitbench.db"

        write_sqlite_report_db(data, db_path)

        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM models").fetchone()[0] == len(data["models"])
            assert conn.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0] == len(data["benchmarks"])
            assert conn.execute("SELECT COUNT(*) FROM fixture_results").fetchone()[0] == 24
            assert (
                conn.execute(
                    """
                    SELECT total_passed
                    FROM model_summaries
                    WHERE model_name = 'openai/gpt-5:medium'
                    """
                ).fetchone()[0]
                == data["model_summaries"]["openai/gpt-5:medium"]["total_passed"]
            )

    def test_writes_fixture_api_duration_to_database(self, tmp_path):
        """Test that SQLite stores API duration without wall-time fallback."""
        data = aggregate_runs(
            [
                _make_envelope_with_scores(
                    [
                        {
                            "fixture_id": "f001",
                            "passed": True,
                            "similarity": 1,
                            "duration_ms": 1000,
                            "api_duration_ms": 123.4,
                        },
                        {
                            "fixture_id": "f002",
                            "passed": True,
                            "similarity": 1,
                            "duration_ms": 2000,
                        },
                    ]
                )
            ]
        )
        db_path = tmp_path / "gitbench.db"

        write_sqlite_report_db(data, db_path)

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                """
                SELECT fixture_id, duration_ms, api_duration_ms
                FROM fixture_results
                ORDER BY fixture_id
                """
            ).fetchall()
            runtime_total = conn.execute(
                "SELECT total_ms FROM model_runtimes WHERE model_name = 'mock'"
            ).fetchone()[0]

        assert rows == [("f001", 1000, 123.4), ("f002", 2000, None)]
        assert runtime_total == 123.4

    def test_invalid_structured_result_stores_raw_output_not_payload(self, tmp_path):
        raw_output = '{"commit":42}'
        data = aggregate_runs(
            [
                _make_envelope_with_scores(
                    [
                        {
                            "fixture_id": "f001",
                            "passed": False,
                            "similarity": 0,
                            "model_output": raw_output,
                            "output_mode": "json_schema",
                            "parsed_payload": {"commit": 42},
                            "raw_structured_output": raw_output,
                            "structured_error": "Structured output schema validation failed",
                        }
                    ]
                )
            ]
        )
        db_path = tmp_path / "gitbench.db"

        write_sqlite_report_db(data, db_path)

        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT model_output, parsed_payload, raw_structured_output, structured_error
                FROM fixture_results
                """
            ).fetchone()
        assert row == (
            raw_output,
            None,
            raw_output,
            "Structured output schema validation failed",
        )

    def test_rebuild_replaces_stale_data(self, tmp_path):
        """Test that an existing database is deleted and rebuilt."""
        db_path = tmp_path / "gitbench.db"
        first = aggregate_runs([_make_envelope(model="openai/gpt-5:medium")])
        second = aggregate_runs([_make_envelope(model="anthropic/claude")])

        write_sqlite_report_db(first, db_path)
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE stale_marker (value TEXT)")

        write_sqlite_report_db(second, db_path)

        with sqlite3.connect(db_path) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            models = {row[0] for row in conn.execute("SELECT name FROM models")}

        assert "stale_marker" not in tables
        assert models == {"anthropic/claude"}



class TestCampaignSQLiteSchema:
    """Campaign-aware SQLite schema extensions."""

    def test_campaign_tables_exist(self, tmp_path):
        db_path = tmp_path / "gitbench.db"
        write_sqlite_report_db({"models": [], "benchmarks": [], "runs_meta": []}, str(db_path))
        with sqlite3.connect(str(db_path)) as conn:
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            names = {t[0] for t in tables}
            assert "campaigns" in names
            assert "trials" in names
            assert "raw_attempts" in names
            assert "fixture_aggregates" in names

    def test_campaign_insertion(self, tmp_path):
        db_path = tmp_path / "gitbench.db"
        data = {
            "models": [],
            "benchmarks": ["commit_messages"],
            "runs_meta": [],
            "campaigns": [
                {
                    "campaign_id": "cmp-db",
                    "created_at": "2026-06-01T00:00:00+00:00",
                    "config_hash": "abc",
                    "state": "complete",
                    "planned_attempts": 2,
                    "completed_attempts": 2,
                    "valid_attempts": 2,
                    "passing_attempts": 1,
                    "excluded_attempts": 0,
                    "publication_state": "draft",
                    "legacy": False,
                    "benchmark_ids": ["commit_messages"],
                    "model_ids": ["m1"],
                    "output_modes": ["text"],
                    "planned_trial_count": 1,
                    "trials": [
                        {
                            "trial_index": 1,
                            "planned_attempts": 2,
                            "completed_attempts": 2,
                            "valid_attempts": 2,
                            "passing_attempts": 1,
                            "excluded_attempts": 0,
                            "complete": True,
                        }
                    ],
                    "raw_attempts": [],
                    "fixture_aggregates": [],
                    "model_summaries": [],
                    "benchmark_summaries": [],
                    "resource_summaries": [],
                }
            ],
        }
        write_sqlite_report_db(data, str(db_path))
        with sqlite3.connect(str(db_path)) as conn:
            row = conn.execute("SELECT campaign_id, state FROM campaigns").fetchone()
            assert row == ("cmp-db", "complete")

    def test_campaign_artifact_discovery_populates_json_and_sqlite(self, tmp_path):
        from gitbench.harness.campaign import (
            AttemptIdentity,
            AttemptStatus,
            RawAttempt,
            Trial,
            make_campaign,
        )
        from gitbench.harness.campaign_store import CampaignStore

        identity = AttemptIdentity(
            campaign_id="cmp-artifact",
            trial_index=1,
            model_id="mock",
            reasoning_effort="none",
            output_mode="text",
            benchmark="commit_messages",
            fixture_id="f001",
        )
        campaign = make_campaign(
            campaign_id="cmp-artifact",
            benchmark_ids=["commit_messages"],
            fixture_ids=["commit_messages/f001"],
            model_ids=["mock"],
            reasoning_efforts=["none"],
            output_modes=["text"],
            planned_trial_count=1,
        )
        campaign.trials = [
            Trial(trial_index=1, planned_attempts=1, attempt_identities=[identity])
        ]
        campaign.planned_attempts = 1

        store = CampaignStore("cmp-artifact", base_dir=tmp_path)
        store.save_manifest(campaign)
        store.write_attempt(
            RawAttempt(
                identity=identity,
                status=AttemptStatus.VALID_PASS,
                passed=True,
                similarity=1.0,
                model_output="feat: add login",
                safety_state="reviewed",
            )
        )

        reports = load_campaign_reports_from_dir(str(tmp_path))
        assert len(reports) == 1
        data = reports[0]
        assert data["campaigns"][0]["campaign_id"] == "cmp-artifact"
        assert data["campaigns"][0]["raw_attempts"][0]["identity"]["benchmark"] == "commit_messages"

        db_path = tmp_path / "gitbench.db"
        write_sqlite_report_db(data, db_path)
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 1
            assert conn.execute("SELECT COUNT(*) FROM raw_attempts").fetchone()[0] == 1
            row = conn.execute(
                """
                SELECT campaign_id, trial_index, model_name, reasoning_level,
                       output_mode, benchmark_name, fixture_id
                FROM raw_attempts
                """
            ).fetchone()
        assert row == (
            "cmp-artifact",
            1,
            "mock",
            "none",
            "text",
            "commit_messages",
            "f001",
        )
