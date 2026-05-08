"""Live progress table rendered to stderr."""

import shutil
import sys
from threading import Lock
from time import monotonic

from gitbench.harness.runner import RunProgress


def _progress_model_names(models: list[str]) -> list[str]:
    """Return stable display names for progress rows, disambiguating
    duplicates."""
    total_counts: dict[str, int] = {}
    seen_counts: dict[str, int] = {}
    for model in models:
        total_counts[model] = total_counts.get(model, 0) + 1

    display_names: list[str] = []
    for model in models:
        seen_counts[model] = seen_counts.get(model, 0) + 1
        if total_counts[model] > 1:
            display_names.append(f"{model} #{seen_counts[model]}")
        else:
            display_names.append(model)
    return display_names


def _progress_model_names_for_runs(
    runs: list[tuple[str, dict, list[str]]],
) -> list[list[str]]:
    """Return display names for every scheduled model across all run
    groups."""
    raw_labels: list[str] = []
    for _profile_name, _profile_conf, models in runs:
        raw_labels.extend(models)

    display_labels = _progress_model_names(raw_labels)
    labels_by_run: list[list[str]] = []
    offset = 0
    for _profile_name, _profile_conf, models in runs:
        labels_by_run.append(display_labels[offset : offset + len(models)])
        offset += len(models)
    return labels_by_run


class TerminalProgressTable:
    """Render a compact, updating progress table to stderr."""

    def __init__(
        self,
        models: list[str],
        benchmarks: list[str],
        stream=None,
        *,
        verbose: bool = False,
    ) -> None:
        self.stream = stream or sys.stderr
        self.verbose = verbose
        self.enabled = bool(getattr(self.stream, "isatty", lambda: False)())
        self._lock = Lock()
        self._rendered_lines = 0
        self._started_at = monotonic()
        self._rows: dict[str, dict] = {
            model: {
                "model": model,
                "current": "-",
                "status": "pending",
                "benchmarks_done": 0,
                "benchmarks_total": len(benchmarks),
                "fixtures_done": 0,
                "fixtures_total": 0,
                "passed": 0,
                "errors": 0,
            }
            for model in models
        }

    # -- RunProgress implementation ----------------------------------------

    def model_started(self, model: str) -> None:
        with self._lock:
            row = self._rows[model]
            if row["status"] == "pending":
                row["status"] = "queued"
            self._render()

    def benchmark_started(self, model: str, benchmark: str, total: int) -> None:
        with self._lock:
            row = self._rows[model]
            row["current"] = benchmark
            row["status"] = "running"
            row["fixtures_total"] += total
            self._render()

    def fixture_finished(self, model: str, benchmark: str, passed: bool, *, fixture_id: str = "", similarity: float = 0.0) -> None:
        with self._lock:
            row = self._rows[model]
            row["current"] = benchmark
            row["fixtures_done"] += 1
            if passed:
                row["passed"] += 1
            self._render()
        if self.verbose and fixture_id:
            status = "PASS" if passed else "FAIL"
            self.stream.write(
                f"  {fixture_id}: passed={passed}, "
                f"similarity={similarity:.4f} [{status}]\n"
            )
            self.stream.flush()

    def benchmark_finished(self, model: str, benchmark: str, errors: int) -> None:
        with self._lock:
            row = self._rows[model]
            row["current"] = benchmark
            row["errors"] += errors
            row["benchmarks_done"] += 1
            row["status"] = "error" if row["errors"] else "running"
            self._render()

    def model_finished(self, model: str, summary: dict) -> None:
        with self._lock:
            row = self._rows[model]
            if row["status"] in {"pending", "queued", "running", "error"}:
                row["status"] = "error" if row["errors"] else "done"
            self._render()

    def close(self) -> None:
        with self._lock:
            self._render(final=True)

    # -- rendering ----------------------------------------------------------

    def _render(self, final: bool = False) -> None:
        if not self.enabled:
            return

        lines = self._build_lines(final=final)
        if self._rendered_lines:
            for _ in range(self._rendered_lines):
                self.stream.write("\x1b[1A\x1b[2K")

        self.stream.write("\n".join(lines) + "\n")
        self.stream.flush()
        self._rendered_lines = len(lines)

    def _build_lines(self, final: bool) -> list[str]:
        width = shutil.get_terminal_size((100, 24)).columns
        elapsed = self._format_seconds(monotonic() - self._started_at)
        title = f"GitBench progress | elapsed {elapsed}"
        if final:
            title = f"GitBench complete | elapsed {elapsed}"

        model_width = 24
        benchmark_width = 22
        fixed_width = model_width + benchmark_width + 57
        if width < fixed_width:
            overflow = fixed_width - width
            benchmark_width = max(12, benchmark_width - overflow)

        header = (
            f"{'Model':<{model_width}}  {'Current':<{benchmark_width}}  "
            f"{'Status':<8} {'Bench':>7} {'Fixtures':>9} {'Passed':>8} "
            f"{'Err':>3}"
        )
        separator = "-" * min(width, len(header))

        lines = [title[:width], header[:width], separator]
        for row in self._rows.values():
            bench_progress = (
                f"{row['benchmarks_done']}/{row['benchmarks_total']}"
            )
            fixture_progress = (
                f"{row['fixtures_done']}/{row['fixtures_total']}"
            )
            line = (
                f"{self._truncate(row['model'], model_width):<{model_width}}"
                f"  "
                f"{self._truncate(row['current'], benchmark_width):<{benchmark_width}}"
                f"  "
                f"{row['status']:<8} {bench_progress:>7} "
                f"{fixture_progress:>9} {row['passed']:>8} {row['errors']:>3}"
            )
            lines.append(line[:width])
        return lines

    @staticmethod
    def _truncate(value: str, width: int) -> str:
        if len(value) <= width:
            return value
        if width <= 1:
            return value[:width]
        return value[: width - 1] + "~"

    @staticmethod
    def _format_seconds(seconds: float) -> str:
        seconds_int = int(seconds)
        minutes, secs = divmod(seconds_int, 60)
        if minutes:
            return f"{minutes}m{secs:02d}s"
        return f"{secs}s"
