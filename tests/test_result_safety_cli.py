"""CLI integration tests for result-safety doctoring and publication gates."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gitbench.cli import cli
from gitbench.result_safety import (
    REDACTION_MARKER,
    ResultSafetyProcessor,
    ResultSafetyReviewer,
    validate_payload_safety,
)


@pytest.fixture
def runner():
    return CliRunner()


def _score(output="unsafe content"):
    return {
        "fixture_id": "f001",
        "passed": True,
        "similarity": 0.75,
        "model_output": output,
        "error": None,
        "input_tokens": 10,
        "output_tokens": 4,
        "total_tokens": 14,
        "cost_usd": 0.02,
        "duration_ms": 50.0,
        "transcript": [
            {"role": "user", "content": "user prompt"},
            {"role": "assistant", "content": output},
        ],
    }


def _envelope(output="unsafe content"):
    return {
        "version": "0.1.0",
        "schema_version": "0.1.0",
        "benchmark_suite_version": "0.3.0",
        "timestamp": "2026-06-13T20:00:00+00:00",
        "git_sha": "abc123",
        "model": "mock",
        "profile": "(inline)",
        "output_mode": "text",
        "summary": {
            "total_benchmarks": 1,
            "total_fixtures": 1,
            "total_passed": 1,
            "overall_pass_at_k": 1.0,
        },
        "results": [
            {
                "benchmark": "commit_messages",
                "total": 1,
                "passed": 1,
                "pass_at_k": 1.0,
                "errors": 0,
                "scores": [_score(output)],
            }
        ],
    }


def _run_result(output="unsafe content"):
    envelope = _envelope(output)
    return {
        "model": "mock",
        "summary": envelope["summary"],
        "results": envelope["results"],
    }


def _config():
    return {
        "models": {
            "safety": {
                "model": "safety-model",
                "base_url": "https://example.test/v1",
            }
        },
        "result_safety": {"profile": "safety"},
    }


def _reviewed_envelope():
    client = MagicMock()
    client.generate.return_value = {"text": '{"decision":"allow"}'}
    processor = ResultSafetyProcessor(
        ResultSafetyReviewer(
            client,
            profile_name="safety",
            model_name="safety-model",
        )
    )
    return processor.review_payload(_envelope("safe content")).payload


class TestSafetyDoctorCommand:
    def test_explicit_file_redacts_and_backs_up_original(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("gitbench.json").write_text(json.dumps(_config()))
            result_path = Path("gitbench-results/20260613T200000Z/run.json")
            result_path.parent.mkdir(parents=True)
            original = _envelope()
            result_path.write_text(json.dumps(original))
            safety_client = MagicMock()
            safety_client.generate.return_value = {
                "text": '{"decision":"redact","reason":"inappropriate_nsfw_content"}'
            }

            with patch("gitbench.cli.get_model_client", return_value=safety_client):
                result = runner.invoke(cli, ["safety-doctor", str(result_path)])

            sanitized = json.loads(result_path.read_text())
            backup = Path("gitbench-results-nsfw/20260613T200000Z/run.json")

            assert result.exit_code == 0
            assert "redacted 1" in result.output
            assert sanitized["results"][0]["scores"][0]["model_output"] == REDACTION_MARKER
            assert json.loads(backup.read_text()) == original

    def test_latest_reviews_every_timestamped_json_file(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("gitbench.json").write_text(json.dumps(_config()))
            for timestamp in ("20260613T200000Z", "20260613T210000Z"):
                path = Path("gitbench-results") / timestamp / "run.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(_envelope("safe")))
            ignored = Path("gitbench-results/not-a-timestamp/run.json")
            ignored.parent.mkdir(parents=True)
            ignored.write_text(json.dumps(_envelope("safe")))
            safety_client = MagicMock()
            safety_client.generate.return_value = {"text": '{"decision":"allow"}'}

            with patch("gitbench.cli.get_model_client", return_value=safety_client):
                result = runner.invoke(cli, ["safety-doctor", "--latest"])

            assert result.exit_code == 0
            assert "Inputs: 2" in result.output
            assert safety_client.generate.call_count == 1
            assert "safety_review" not in json.loads(ignored.read_text())

    def test_dry_run_and_missing_configuration_write_nothing(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result_path = Path("run.json")
            original = json.dumps(_envelope())
            result_path.write_text(original)

            missing = runner.invoke(cli, ["safety-doctor", str(result_path)])
            assert missing.exit_code != 0
            assert "Result safety is not configured" in missing.output
            assert result_path.read_text() == original

            Path("gitbench.json").write_text(json.dumps(_config()))
            safety_client = MagicMock()
            safety_client.generate.return_value = {
                "text": '{"decision":"redact","reason":"inappropriate_nsfw_content"}'
            }
            with patch("gitbench.cli.get_model_client", return_value=safety_client):
                dry_run = runner.invoke(
                    cli,
                    ["safety-doctor", str(result_path), "--dry-run"],
                )

            assert dry_run.exit_code == 0
            assert "Dry run complete" in dry_run.output
            assert result_path.read_text() == original
            assert not Path("gitbench-results-nsfw").exists()

    def test_unsupported_format_and_reviewer_failure_are_fail_closed(
        self, runner, tmp_path
    ):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("gitbench.json").write_text(json.dumps(_config()))
            unsupported = Path("unsupported.json")
            unsupported.write_text('{"other":"shape"}')
            safety_client = MagicMock()
            safety_client.generate.return_value = {"text": '{"decision":"allow"}'}

            with patch("gitbench.cli.get_model_client", return_value=safety_client):
                unsupported_result = runner.invoke(
                    cli,
                    ["safety-doctor", str(unsupported)],
                )

            assert unsupported_result.exit_code != 0
            assert "Unsupported result format" in unsupported_result.output
            assert unsupported.read_text() == '{"other":"shape"}'

            result_path = Path("run.json")
            original = json.dumps(_envelope())
            result_path.write_text(original)
            safety_client.generate.side_effect = RuntimeError("provider down")
            with patch("gitbench.cli.get_model_client", return_value=safety_client):
                failed = runner.invoke(cli, ["safety-doctor", str(result_path)])

            assert failed.exit_code != 0
            assert "provider down" in failed.output
            assert result_path.read_text() == original
            assert not Path("gitbench-results-nsfw").exists()


class TestRunSafetyGate:
    def test_stdout_json_and_default_file_are_sanitized(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("gitbench.json").write_text(json.dumps(_config()))
            export_path = Path("export.json")
            safety_client = MagicMock()
            safety_client.generate.return_value = {
                "text": '{"decision":"redact","reason":"inappropriate_nsfw_content"}'
            }

            with (
                patch("gitbench.cli.check_git_availability", return_value=True),
                patch("gitbench.cli._benchmark_registry", {"commit_messages": object()}),
                patch(
                    "gitbench.harness.runner.BenchmarkRunner.run_all",
                    return_value=_run_result(),
                ),
                patch(
                    "gitbench.cli.get_model_client",
                    side_effect=[safety_client, MagicMock()],
                ),
            ):
                result = runner.invoke(
                    cli,
                    [
                        "run",
                        "--benchmark",
                        "commit_messages",
                        "--model",
                        "mock",
                        "--output-mode",
                        "text",
                        "--export",
                        "json",
                        "--export-path",
                        str(export_path),
                    ],
                )

            assert result.exit_code == 0, result.output
            default_file = next(Path("gitbench-results").rglob("results-v*.json"))
            assert REDACTION_MARKER in result.output
            assert "unsafe content" not in result.output
            assert REDACTION_MARKER in default_file.read_text()
            assert "unsafe content" not in default_file.read_text()
            assert REDACTION_MARKER in export_path.read_text()
            assert "unsafe content" not in export_path.read_text()

    def test_all_output_destinations_receive_sanitized_content_and_backup(
        self, runner, tmp_path
    ):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("gitbench.json").write_text(json.dumps(_config()))
            output_dir = Path("per-run")
            jsonl_path = Path("runs.jsonl")
            combined_path = Path("combined.json")
            export_path = Path("results.csv")
            safety_client = MagicMock()
            safety_client.generate.return_value = {
                "text": '{"decision":"redact","reason":"inappropriate_nsfw_content"}'
            }

            with (
                patch("gitbench.cli.check_git_availability", return_value=True),
                patch("gitbench.cli._benchmark_registry", {"commit_messages": object()}),
                patch(
                    "gitbench.harness.runner.BenchmarkRunner.run_all",
                    return_value=_run_result(),
                ),
                patch(
                    "gitbench.cli.get_model_client",
                    side_effect=[safety_client, MagicMock()],
                ),
            ):
                result = runner.invoke(
                    cli,
                    [
                        "run",
                        "--benchmark",
                        "commit_messages",
                        "--model",
                        "mock",
                        "--output-mode",
                        "text",
                        "--output-dir",
                        str(output_dir),
                        "--jsonl",
                        str(jsonl_path),
                        "--json-output",
                        str(combined_path),
                        "--export",
                        "csv",
                        "--export-path",
                        str(export_path),
                    ],
                )

            assert result.exit_code == 0, result.output
            per_run = json.loads(next(output_dir.glob("*.json")).read_text())
            jsonl = json.loads(jsonl_path.read_text())
            combined = json.loads(combined_path.read_text())
            csv_text = export_path.read_text()
            backup = next(Path("gitbench-results-nsfw").rglob("*.json"))

            assert per_run["results"][0]["scores"][0]["model_output"] == REDACTION_MARKER
            assert jsonl["results"][0]["scores"][0]["model_output"] == REDACTION_MARKER
            assert combined["scores"][0]["model_output"] == REDACTION_MARKER
            assert REDACTION_MARKER in csv_text
            assert "unsafe content" not in json.dumps(per_run)
            assert "unsafe content" not in json.dumps(jsonl)
            assert "unsafe content" not in json.dumps(combined)
            assert "unsafe content" not in csv_text
            assert "unsafe content" in backup.read_text()
            assert combined["passed"] == 1
            assert combined["scores"][0]["similarity"] == 0.75

    def test_review_failure_writes_no_normal_output(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("gitbench.json").write_text(json.dumps(_config()))
            output_dir = Path("per-run")
            jsonl_path = Path("runs.jsonl")
            combined_path = Path("combined.json")
            export_path = Path("results.csv")
            safety_client = MagicMock()
            safety_client.generate.side_effect = RuntimeError("review failed")

            with (
                patch("gitbench.cli.check_git_availability", return_value=True),
                patch("gitbench.cli._benchmark_registry", {"commit_messages": object()}),
                patch(
                    "gitbench.harness.runner.BenchmarkRunner.run_all",
                    return_value=_run_result(),
                ),
                patch(
                    "gitbench.cli.get_model_client",
                    side_effect=[safety_client, MagicMock()],
                ),
            ):
                result = runner.invoke(
                    cli,
                    [
                        "run",
                        "--benchmark",
                        "commit_messages",
                        "--model",
                        "mock",
                        "--output-mode",
                        "text",
                        "--output-dir",
                        str(output_dir),
                        "--jsonl",
                        str(jsonl_path),
                        "--json-output",
                        str(combined_path),
                        "--export",
                        "csv",
                        "--export-path",
                        str(export_path),
                    ],
                )

            assert result.exit_code != 0
            assert "review failed" in result.output
            assert not output_dir.exists()
            assert not jsonl_path.exists()
            assert not combined_path.exists()
            assert not export_path.exists()
            assert not Path("gitbench-results-nsfw").exists()


class TestReportSafetyGate:
    def test_rejects_unswept_input_before_report_writes_or_model_calls(
        self, runner, tmp_path
    ):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("gitbench.json").write_text(json.dumps(_config()))
            result_path = Path("gitbench-results/20260613T200000Z/run.json")
            result_path.parent.mkdir(parents=True)
            result_path.write_text(json.dumps(_envelope("safe content")))
            output_path = Path("report.json")

            with patch("gitbench.cli.get_model_client") as get_model_client:
                result = runner.invoke(
                    cli,
                    [
                        "report",
                        "--input-dir",
                        "gitbench-results",
                        "--output",
                        str(output_path),
                        "--no-build",
                    ],
                )

            assert result.exit_code != 0
            assert str(result_path) in result.output
            assert "safety-doctor" in result.output
            assert not output_path.exists()
            get_model_client.assert_not_called()

    def test_accepts_reviewed_input_and_stamps_generated_report(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("gitbench.json").write_text(json.dumps(_config()))
            result_path = Path("gitbench-results/20260613T200000Z/run.json")
            result_path.parent.mkdir(parents=True)
            result_path.write_text(json.dumps(_reviewed_envelope()))
            output_path = Path("report.json")

            with patch("gitbench.cli.get_model_client") as get_model_client:
                result = runner.invoke(
                    cli,
                    [
                        "report",
                        "--input-dir",
                        "gitbench-results",
                        "--output",
                        str(output_path),
                        "--no-build",
                    ],
                )

            assert result.exit_code == 0, result.output
            report_data = json.loads(output_path.read_text())
            validate_payload_safety(report_data)
            assert (
                report_data["fixtures"]["mock"]["commit_messages"][0][
                    "safety_review"
                ]["status"]
                == "allow"
            )
            get_model_client.assert_not_called()
