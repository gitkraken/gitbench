"""Tests for GitBench render module."""

import json

import pytest

from gitbench.render import aggregate_runs, load_runs_from_dir, load_runs_from_jsonl, render_json

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
        r1 = _make_envelope(timestamp="2026-04-25T15:00:00+00:00")
        r2 = _make_envelope(timestamp="2026-04-25T13:00:00+00:00")
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
