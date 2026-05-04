"""Tests for GitBench render module."""

import json

import pytest
from click.testing import CliRunner

from gitbench.cli import cli
from gitbench.render import aggregate_runs, load_runs_from_dir, load_runs_from_jsonl, render_html


def _make_envelope(model="mock", bench="commit_messages", total=12, passed=10, timestamp="2026-04-25T13:00:00+00:00"):
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

    def test_sorted_by_timestamp(self, tmp_path):
        """Test that runs are sorted by timestamp."""
        r1 = _make_envelope(timestamp="2026-04-25T15:00:00+00:00")
        r2 = _make_envelope(timestamp="2026-04-25T13:00:00+00:00")
        (tmp_path / "later.json").write_text(json.dumps(r1))
        (tmp_path / "earlier.json").write_text(json.dumps(r2))

        runs = load_runs_from_dir(str(tmp_path))
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

        assert "mock" in data["models"]
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
        assert "mock" in data["models"]
        assert "gpt-4o" in data["models"]

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


class TestRenderHtml:
    """Tests for render_html."""

    def test_produces_valid_html(self):
        """Test that render_html produces a complete HTML document."""
        runs = [_make_envelope()]
        data = aggregate_runs(runs)
        html = render_html(data)

        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert "Chart.js" in html or "chart.js" in html

    def test_includes_model_names(self):
        """Test that model names appear in the HTML."""
        runs = [_make_envelope(model="gpt-4o")]
        data = aggregate_runs(runs)
        html = render_html(data)

        assert "gpt-4o" in html

    def test_includes_custom_title(self):
        """Test that custom title is used."""
        runs = [_make_envelope()]
        data = aggregate_runs(runs)
        html = render_html(data, title="My Custom Report")

        assert "<title>My Custom Report</title>" in html
        assert "<h1>My Custom Report</h1>" in html

    def test_includes_benchmark_names(self):
        """Test that benchmark names appear in the HTML."""
        runs = [_make_envelope(bench="rebase")]
        data = aggregate_runs(runs)
        html = render_html(data)

        assert "rebase" in html


class TestRenderCommand:
    """Tests for the render CLI command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_render_from_dir(self, runner, tmp_path):
        """Test render command with --input-dir."""
        run = _make_envelope()
        (tmp_path / "runs" / "run1.json").parent.mkdir(exist_ok=True)
        (tmp_path / "runs" / "run1.json").write_text(json.dumps(run))
        output = tmp_path / "report.html"

        result = runner.invoke(cli, [
            "render", "--input-dir", str(tmp_path / "runs"),
            "--output", str(output),
        ])
        assert result.exit_code == 0
        assert output.exists()

        html = output.read_text()
        assert "<!DOCTYPE html>" in html
        assert "mock" in html

    def test_render_from_jsonl(self, runner, tmp_path):
        """Test render command with --input."""
        jsonl = tmp_path / "results.jsonl"
        jsonl.write_text(json.dumps(_make_envelope()))
        output = tmp_path / "report.html"

        result = runner.invoke(cli, [
            "render", "--input", str(jsonl),
            "--output", str(output),
        ])
        assert result.exit_code == 0
        assert output.exists()

    def test_render_creates_nested_output_parent_dirs(self, runner, tmp_path):
        """Test that render --output creates parent directories."""
        jsonl = tmp_path / "results.jsonl"
        jsonl.write_text(json.dumps(_make_envelope()))
        output = tmp_path / "nested" / "reports" / "report.html"

        result = runner.invoke(cli, [
            "render", "--input", str(jsonl),
            "--output", str(output),
        ])

        assert result.exit_code == 0
        assert output.exists()
        assert output.read_text().startswith("<!DOCTYPE html>")

    def test_render_requires_input(self, runner):
        """Test that render fails without input."""
        result = runner.invoke(cli, ["render"])
        assert result.exit_code != 0
        assert "--input-dir" in result.output or "--input" in result.output

    def test_render_with_title(self, runner, tmp_path):
        """Test that --title sets the report title."""
        jsonl = tmp_path / "results.jsonl"
        jsonl.write_text(json.dumps(_make_envelope()))
        output = tmp_path / "report.html"

        result = runner.invoke(cli, [
            "render", "--input", str(jsonl),
            "--title", "Q1 Benchmarks",
            "--output", str(output),
        ])
        assert result.exit_code == 0
        assert "Q1 Benchmarks" in output.read_text()

    def test_render_deduplicates(self, runner, tmp_path):
        """Test that duplicate runs (same timestamp+model) are deduplicated."""
        run = _make_envelope()
        (tmp_path / "r1.json").write_text(json.dumps(run))
        (tmp_path / "r2.json").write_text(json.dumps(run))  # duplicate

        output = tmp_path / "report.html"
        result = runner.invoke(cli, [
            "render", "--input-dir", str(tmp_path),
            "--output", str(output),
        ])
        assert result.exit_code == 0
        # Should say 1 unique run, not 2
        assert "1 unique" in result.output

    def test_render_default_output(self, runner, tmp_path, monkeypatch):
        """Test that default output is gitbench-report.html."""
        monkeypatch.chdir(tmp_path)
        jsonl = tmp_path / "results.jsonl"
        jsonl.write_text(json.dumps(_make_envelope()))

        result = runner.invoke(cli, ["render", "--input", str(jsonl)])
        assert result.exit_code == 0
        assert (tmp_path / "gitbench-report.html").exists()
