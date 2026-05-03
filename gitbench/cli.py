"""CLI for GitBench."""

import importlib
import inspect
import json
import logging
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Protocol

import click

from gitbench.benchmarks import Benchmark
from gitbench.config import find_profile_for_model, load_config, resolve_profile
from gitbench.harness.model import MockModelClient, OllamaAdapter, OpenAIAdapter
from gitbench.harness.types import BenchmarkResult, Fixture, ModelMessage, Score

# Configure structured logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Global registry for discovered benchmarks
_benchmark_registry: dict[str, type[Benchmark]] = {}


def discover_benchmarks() -> dict[str, type[Benchmark]]:
    """Auto-discover all Benchmark subclasses from the benchmarks package.

    Returns:
        Dictionary mapping benchmark names to their classes.
    """
    benchmarks_dir = Path(__file__).parent / "benchmarks"

    if not benchmarks_dir.exists():
        logger.warning(f"Benchmarks directory not found: {benchmarks_dir}")
        return {}

    discovered: dict[str, type[Benchmark]] = {}

    for file_path in benchmarks_dir.glob("*.py"):
        if file_path.name.startswith("_") or file_path.name == "__init__.py":
            continue

        module_name = f"gitbench.benchmarks.{file_path.stem}"

        try:
            module = importlib.import_module(module_name)

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, Benchmark)
                    and obj is not Benchmark
                    and obj is not None
                ):
                    if hasattr(obj, "name") and obj.name:
                        discovered[obj.name] = obj
                        logger.debug(f"Discovered benchmark: {obj.name} from {module_name}")
                    else:
                        logger.warning(
                            f"Benchmark class {name} in {module_name} has no name attribute"
                        )

        except Exception as e:
            logger.error(f"Failed to load benchmarks from {module_name}: {e}")

    return discovered


def check_git_availability() -> bool:
    """Check if git CLI is available.

    Returns:
        True if git is available, False otherwise.
    """
    git_path = shutil.which("git")
    if git_path:
        logger.info(f"Git CLI found at: {git_path}")
        return True
    else:
        logger.error("Git CLI not found in PATH")
        return False


def get_model_client(model: str, timeout: int = 600, retry_count: int = 3, base_url: str | None = None, api_key: str | None = None, provider: str | None = None) -> OpenAIAdapter | OllamaAdapter | MockModelClient:
    """Get the model client based on model name and provider.

    Args:
        model: Model name. Use 'mock' for testing.
        timeout: Timeout in seconds for model generation (default: 600).
        retry_count: Number of retries on failure (default: 3).
        base_url: Optional API base URL. For Ollama, defaults to http://localhost:11434.
                  For OpenAI-compatible providers, set explicitly.
        api_key: Optional API key for OpenAI-compatible providers.
        provider: Explicit provider type: 'ollama', 'openai', or None to auto-detect.
                  When a profile is used, this comes from the config's 'provider' field.

    Returns:
        The appropriate model client instance.
    """
    if model == "mock":
        return MockModelClient()

    # Determine provider: explicit param wins, then infer from base_url
    if provider is None:
        if base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
            provider = "ollama"
        else:
            provider = "openai"

    if provider == "ollama":
        # Normalize Ollama base_url: strip /v1 suffix if present (Ollama's native API doesn't use it)
        ollama_base = base_url or "http://localhost:11434"
        ollama_base = ollama_base.rstrip("/")
        if ollama_base.endswith("/v1"):
            ollama_base = ollama_base[:-3]
        return OllamaAdapter(model=model, base_url=ollama_base, timeout=timeout, retry_count=retry_count)
    else:
        return OpenAIAdapter(model=model, timeout=timeout, retry_count=retry_count, base_url=base_url, api_key=api_key)


def _get_git_sha() -> str | None:
    """Get the current git commit SHA, or None if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def build_run_envelope(
    model: str,
    profile: str,
    results: list[dict],
) -> dict:
    """Wrap benchmark results in a metadata envelope for structured output.

    Args:
        model: Model name used for this run.
        profile: Profile name (or '(inline)' if no profile).
        results: List of BenchmarkResult dicts.

    Returns:
        Dict with metadata envelope and results.
    """
    now = datetime.now(timezone.utc)
    total_fixtures = sum(r.get("total", 0) for r in results)
    total_passed = sum(r.get("passed", 0) for r in results)

    return {
        "version": 1,
        "timestamp": now.isoformat(),
        "git_sha": _get_git_sha(),
        "model": model,
        "profile": profile,
        "summary": {
            "total_benchmarks": len(results),
            "total_fixtures": total_fixtures,
            "total_passed": total_passed,
            "overall_pass_at_k": round(total_passed / total_fixtures, 4) if total_fixtures > 0 else 0.0,
        },
        "results": results,
    }


def _sanitize_filename(s: str) -> str:
    """Sanitize a string for use in filenames."""
    return s.replace("/", "_").replace(":", "-").replace(" ", "_")


def write_output_dir(envelope: dict, output_dir: str) -> Path:
    """Write a run envelope as a JSON file in the output directory.

    Filename format: {YYYY-MM-DDTHH-MM-SS}_{model}.json
    If a collision exists (same timestamp + model within the same second),
    appends _2, _3, etc. to avoid overwriting.

    Args:
        envelope: The run envelope dict.
        output_dir: Directory path to write to.

    Returns:
        Path to the written file.
    """
    dir_path = Path(output_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    ts = envelope["timestamp"].replace(":", "-")[:19]  # YYYY-MM-DDTHH-MM-SS
    model = _sanitize_filename(envelope["model"])
    base = f"{ts}_{model}"

    # Non-destructive: add counter suffix on collision
    candidate = dir_path / f"{base}.json"
    counter = 2
    while candidate.exists():
        candidate = dir_path / f"{base}_{counter}.json"
        counter += 1

    candidate.write_text(json.dumps(envelope, indent=2))
    return candidate


def write_jsonl(envelope: dict, jsonl_path: str) -> Path:
    """Append a run envelope as a JSON line to a JSONL file.

    Args:
        envelope: The run envelope dict.
        jsonl_path: Path to the JSONL file.

    Returns:
        Path to the written file.
    """
    file_path = Path(jsonl_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "a") as f:
        f.write(json.dumps(envelope) + "\n")

    return file_path


def _progress_model_names(models: list[str]) -> list[str]:
    """Return stable display names for progress rows, disambiguating duplicates."""
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


def _progress_model_names_for_runs(runs: list[tuple[str, dict, list[str]]]) -> list[list[str]]:
    """Return display names for every scheduled model across all run groups."""
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


class RunProgress(Protocol):
    """Progress sink used by benchmark runners."""

    def model_started(self, model: str) -> None: ...

    def benchmark_started(self, model: str, benchmark: str, total: int) -> None: ...

    def fixture_finished(self, model: str, benchmark: str, passed: bool) -> None: ...

    def benchmark_finished(self, model: str, benchmark: str, errors: int) -> None: ...

    def model_finished(self, model: str, summary: dict) -> None: ...


class TerminalProgressTable:
    """Render a compact, updating progress table to stderr."""

    def __init__(self, models: list[str], benchmarks: list[str], stream=None) -> None:
        self.stream = stream or sys.stderr
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

    def fixture_finished(self, model: str, benchmark: str, passed: bool) -> None:
        with self._lock:
            row = self._rows[model]
            row["current"] = benchmark
            row["fixtures_done"] += 1
            if passed:
                row["passed"] += 1
            self._render()

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
            f"{'Status':<8} {'Bench':>7} {'Fixtures':>9} {'Passed':>8} {'Err':>3}"
        )
        separator = "-" * min(width, len(header))

        lines = [title[:width], header[:width], separator]
        for row in self._rows.values():
            benchmark_progress = f"{row['benchmarks_done']}/{row['benchmarks_total']}"
            fixture_progress = f"{row['fixtures_done']}/{row['fixtures_total']}"
            line = (
                f"{self._truncate(row['model'], model_width):<{model_width}}  "
                f"{self._truncate(row['current'], benchmark_width):<{benchmark_width}}  "
                f"{row['status']:<8} {benchmark_progress:>7} "
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


def run_model_benchmarks(
    current_model: str,
    benchmarks_to_run: list[str],
    *,
    timeout: int,
    retry_count: int,
    base_url: str | None,
    api_key: str | None,
    provider: str | None,
    verbose: bool = False,
    progress: RunProgress | None = None,
    progress_model_name: str | None = None,
    fixture_workers: int = 1,
) -> dict:
    """Run all selected benchmarks for one model."""
    progress_model = progress_model_name or current_model
    if progress:
        progress.model_started(progress_model)

    model_client = get_model_client(
        current_model,
        timeout=timeout,
        retry_count=retry_count,
        base_url=base_url,
        api_key=api_key,
        provider=provider,
    )

    results_list: list[dict] = []

    for bench_name in benchmarks_to_run:
        if bench_name not in _benchmark_registry:
            results_list.append({
                "benchmark": bench_name,
                "error": f"Unknown benchmark '{bench_name}'",
            })
            continue

        try:
            result = run_benchmark(bench_name, model_client, verbose, progress, progress_model, fixture_workers)
            results_list.append(result.to_dict())
        except Exception as e:
            logger.error(f"Benchmark '{bench_name}' failed for model '{current_model}': {e}")
            if progress:
                progress.benchmark_finished(progress_model, bench_name, errors=1)
            results_list.append({
                "benchmark": bench_name,
                "error": str(e),
            })

    total_benchmarks = len(results_list)
    total_fixtures = sum(r.get("total", 0) for r in results_list)
    total_passed = sum(r.get("passed", 0) for r in results_list)
    overall_pass_at_k = round(total_passed / total_fixtures, 4) if total_fixtures > 0 else 0.0

    model_result = {
        "model": current_model,
        "summary": {
            "total_benchmarks": total_benchmarks,
            "total_fixtures": total_fixtures,
            "total_passed": total_passed,
            "overall_pass_at_k": overall_pass_at_k,
        },
        "results": results_list,
    }

    if progress:
        progress.model_finished(progress_model, model_result["summary"])

    return model_result


def run_benchmark(
    benchmark_name: str,
    model_client,
    verbose: bool = False,
    progress: RunProgress | None = None,
    model_name: str | None = None,
    fixture_workers: int = 1,
) -> BenchmarkResult:
    """Run a specific benchmark with the given model client.

    Args:
        benchmark_name: Name of the benchmark to run.
        model_client: The model client to use for generating outputs.
        verbose: Whether to print verbose output.
        progress: Progress callback.
        model_name: Name to use in progress callbacks.
        fixture_workers: Number of worker threads for parallel fixture execution.

    Returns:
        The benchmark result.

    Raises:
        ValueError: If the benchmark is not found.
    """
    global _benchmark_registry

    if not _benchmark_registry:
        _benchmark_registry = discover_benchmarks()

    if benchmark_name not in _benchmark_registry:
        available = list(_benchmark_registry.keys())
        raise ValueError(
            f"Unknown benchmark: {benchmark_name}. Available: {available}"
        )

    benchmark_class = _benchmark_registry[benchmark_name]
    benchmark = benchmark_class()

    logger.debug(f"Loading fixtures for {benchmark_name}...")
    fixtures = benchmark.load_fixtures()
    logger.debug(f"Loaded {len(fixtures)} fixtures")

    if progress and model_name:
        progress.benchmark_started(model_name, benchmark_name, len(fixtures))

    # Worker function: runs inside a thread, manages its own executor lifecycle
    def _run_fixture(fixture: Fixture) -> tuple[int, Score]:
        executor = None
        try:
            executor, repo_path = benchmark.setup_fixture(fixture)
            diff = benchmark.get_diff(repo_path)
            prompt = benchmark.format_prompt(fixture, diff)

            messages = [ModelMessage(role="user", content=prompt)]
            response = model_client.generate(messages)

            # Extract text from response (handle both string and dict responses)
            if isinstance(response, dict):
                model_output = response.get("text", response.get("content", ""))
            else:
                model_output = str(response)

            score = benchmark.score(fixture, model_output, repo_path=repo_path)
            return fixture.id, score
        except Exception as e:
            logger.error(f"Error processing fixture {fixture.id}: {e}")
            return fixture.id, Score(
                fixture_id=fixture.id,
                passed=False,
                similarity=0.0,
                model_output="",
                error=str(e),
            )
        finally:
            if executor is not None:
                executor.cleanup()

    if fixture_workers > 1 and len(fixtures) > 1:
        # Parallel execution: collect results, sort back into fixture order
        ordered_scores: list[Score | None] = [None] * len(fixtures)
        ordered_ids: list[str] = [f.id for f in fixtures]

        with ThreadPoolExecutor(max_workers=fixture_workers) as executor:
            futures = {executor.submit(_run_fixture, f): i for i, f in enumerate(fixtures)}
            for future in as_completed(futures):
                idx = futures[future]
                fixture_id, score = future.result()
                ordered_scores[idx] = score
                if progress and model_name:
                    progress.fixture_finished(model_name, benchmark_name, score.passed)
                if verbose:
                    click.echo(
                        f"  {fixture_id}: passed={score.passed}, "
                        f"similarity={score.similarity:.4f}"
                    )

        # Sort scores back into fixture order (order matters for deterministic output)
        fixture_index = {fid: i for i, fid in enumerate(ordered_ids)}
        scores = [ordered_scores[fixture_index[s.fixture_id]] for s in ordered_scores if s is not None]
    else:
        # Sequential fallback
        scores: list[Score] = []
        errors = 0

        for fixture in fixtures:
            logger.debug(f"Processing fixture {fixture.id}...")
            _, score = _run_fixture(fixture)
            scores.append(score)
            if progress and model_name:
                progress.fixture_finished(model_name, benchmark_name, score.passed)
            if verbose:
                click.echo(
                    f"  {fixture.id}: passed={score.passed}, "
                    f"similarity={score.similarity:.4f}"
                )
        errors = sum(1 for s in scores if s.error)

    total = len(fixtures)
    passed = sum(1 for s in scores if s.passed)
    pass_at_k = passed / total if total > 0 else 0.0

    if progress and model_name:
        progress.benchmark_finished(model_name, benchmark_name, sum(1 for s in scores if s.error))

    return BenchmarkResult(
        benchmark=benchmark_name,
        total=total,
        passed=passed,
        pass_at_k=round(pass_at_k, 4),
        scores=scores,
        errors=sum(1 for s in scores if s.error),
    )


# ANSI color codes
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RESET = "\x1b[0m"
BOLD = "\x1b[1m"

# Cached color detection result
_use_colors: bool | None = None


def should_use_colors(stream=None) -> bool:
    """Determine whether to use colored terminal output.

    Checks:
    - NO_COLOR environment variable (per https://no-color.org/)
    - TERM environment variable set to 'dumb'
    - Whether the stream is a TTY

    Result is cached after first call for performance when no stream argument is provided.

    Args:
        stream: Stream to check TTY status against. Defaults to sys.stdout.

    Returns:
        True if colors should be used, False otherwise.
    """
    global _use_colors

    # Always check NO_COLOR and TERM=dumb first (no caching — these are env-based).
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        _use_colors = False
        return False

    # If a specific stream was provided, check it directly (no caching).
    # Caching is only used for the default sys.stdout check.
    if stream is not None:
        return bool(getattr(stream, "isatty", lambda: False)())

    if _use_colors is not None:
        return _use_colors

    # Check if stream is a TTY
    check_stream = stream or sys.stdout
    is_tty = getattr(check_stream, "isatty", lambda: False)()
    _use_colors = bool(is_tty)
    return _use_colors


def is_output_suppressed(stream=None) -> bool:
    """Determine whether TTY-only output should be suppressed.

    TTY-only output (e.g. summary table) should only print when stdout is a
    real terminal, not when piped or redirected. This differs from color
    detection in that we never suppress just because of NO_COLOR or TERM=dumb
    — those only disable colors, not the output itself.

    Args:
        stream: Stream to check TTY status against. Defaults to sys.stdout.

    Returns:
        True if TTY-only output should be suppressed, False if it should print.
    """
    check_stream = stream or sys.stdout
    return not bool(getattr(check_stream, "isatty", lambda: False)())


class SummaryTable:
    """Render a colored summary table of benchmark results to stdout.

    Only renders when stdout is a TTY (colored output suppressed when piped).
    Uses ANSI escape codes when color is enabled, plain text otherwise.
    Color coding for pass@1: green >= 0.8, yellow >= 0.5, red < 0.5.
    """

    def __init__(self, results: list[dict], stream=None) -> None:
        """Initialize summary table with benchmark results.

        Args:
            results: List of BenchmarkResult dicts with benchmark, total, passed, pass_at_k keys.
            stream: Output stream. Defaults to sys.stdout.
        """
        self.stream = stream or sys.stdout
        self.results = results
        # Only render when stdout is a TTY. NO_COLOR/TERM=dumb only disable colors, not the table.
        self.enabled = not is_output_suppressed(self.stream)
        # Colors are disabled if NO_COLOR/TERM=dumb even in a TTY.
        self._color_enabled = should_use_colors(self.stream)

    def _color(self, text: str, color: str) -> str:
        """Wrap text in ANSI color codes if colors are enabled."""
        if self._color_enabled:
            return f"{color}{text}{RESET}"
        return text

    def _bold(self, text: str) -> str:
        """Wrap text in ANSI bold code if colors are enabled."""
        if self._color_enabled:
            return f"{BOLD}{text}{RESET}"
        return text

    def _pass_at_k_color(self, pass_at_k: float) -> str:
        """Return color for a pass@1 value."""
        if pass_at_k >= 0.8:
            return GREEN
        elif pass_at_k >= 0.5:
            return YELLOW
        else:
            return RED

    def render(self) -> str | None:
        """Render the summary table and write to stream.

        Returns:
            The table string, or None if stdout is not a TTY (table suppressed).
        """
        if not self.enabled:
            return None

        # Sort results alphabetically by benchmark name
        sorted_results = sorted(self.results, key=lambda r: r.get("benchmark", ""))

        # Calculate totals
        total_fixtures = sum(r.get("total", 0) for r in sorted_results)
        total_passed = sum(r.get("passed", 0) for r in sorted_results)
        overall_pass_at_k = round(total_passed / total_fixtures, 4) if total_fixtures > 0 else 0.0

        # Build table lines
        lines: list[str] = []

        # Header
        header = f"{'Benchmark':<30} {'Pass@1':>8} {'Passed/Fail':>12}"
        lines.append(self._bold(header))
        lines.append("-" * 54)

        # Data rows
        for r in sorted_results:
            benchmark = r.get("benchmark", "?")
            total = r.get("total", 0)
            passed = r.get("passed", 0)
            failed = total - passed
            pass_at_k = r.get("pass_at_k", 0.0)
            pass_at_k_str = f"{pass_at_k:.1%}"

            color = self._pass_at_k_color(pass_at_k)
            pass_at_k_colored = self._color(pass_at_k_str, color)
            passed_fail = f"{passed}/{failed}"

            line = f"{benchmark:<30} {pass_at_k_colored:>8} {passed_fail:>12}"
            lines.append(line)

        # Separator before summary
        lines.append("-" * 54)

        # Summary row
        summary_pass_at_k_str = f"{overall_pass_at_k:.1%}"
        summary_color = self._pass_at_k_color(overall_pass_at_k)
        summary_pass_at_k_colored = self._color(summary_pass_at_k_str, summary_color)
        total_str = f"{total_passed}/{total_fixtures}"

        summary_line = f"{'TOTAL':<30} {summary_pass_at_k_colored:>8} {total_str:>12}"
        lines.append(self._bold(summary_line))

        table = "\n".join(lines) + "\n"

        # Write to stream
        self.stream.write(table)
        self.stream.flush()

        return table


@click.group()
def cli():
    """GitBench: Benchmark harness for evaluating LLM-generated git commit messages."""
    pass


@cli.command()
@click.option(
    "--all",
    "-a",
    "run_all",
    is_flag=True,
    help="Run all benchmarks against all models (shorthand for --all-benchmarks --all-models)",
)
@click.option(
    "--all-benchmarks",
    "all_benchmarks_flag",
    is_flag=True,
    help="Run all available benchmarks",
)
@click.option(
    "--benchmark",
    "-b",
    "benchmark_name",
    help="Name of the benchmark to run (cannot be used with --all-benchmarks)",
)
@click.option(
    "--profile",
    "-p",
    default=None,
    help="Model profile name from gitbench.json (overrides --model/--base-url for unset values)",
)
@click.option(
    "--all-profiles",
    is_flag=True,
    help="Run against all profiles defined in gitbench.json",
)
@click.option(
    "--all-models",
    is_flag=True,
    help="Run against all models across all profiles (flattened)",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model to use. 'mock' for testing, Ollama models (e.g. 'llama3.1:8b') for local inference, or any model name for OpenAI-compatible APIs (e.g. 'gpt-4o'). Overrides profile model if both set.",
)
@click.option(
    "--base-url",
    default=None,
    help="API base URL. Defaults to http://localhost:11434 for Ollama models. Set explicitly for OpenAI-compatible providers (e.g. https://openrouter.ai/api/v1). Overrides profile base_url if both set.",
)
@click.option(
    "--provider",
    default=None,
    type=click.Choice(["ollama", "openai"], case_sensitive=False),
    help="Model provider type. Overrides profile provider if set. Auto-detected from base_url if omitted.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (writes JSON, defaults to stdout)",
)
@click.option(
    "--output-dir",
    "-d",
    type=click.Path(),
    default=None,
    help="Directory to write per-run JSON files (auto-named with timestamp + model)",
)
@click.option(
    "--jsonl",
    "-j",
    "jsonl_path",
    type=click.Path(),
    default=None,
    help="Append run results as a JSON line to this file (for accumulating runs)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Print detailed per-fixture results",
)
@click.option(
    "--timeout",
    "-t",
    default=600,
    type=int,
    help="Timeout in seconds for model generation (default: 600)",
)
@click.option(
    "--retry-count",
    "-r",
    default=3,
    type=int,
    help="Number of retries on model failure (default: 3)",
)
@click.option(
    "--model-workers",
    default=1,
    type=click.IntRange(1),
    show_default=True,
    help="Number of models to run concurrently.",
)
@click.option(
    "--fixture-workers",
    default=1,
    type=click.IntRange(1),
    show_default=True,
    help="Number of fixtures to run concurrently within a benchmark.",
)
def run(run_all: bool, all_benchmarks_flag: bool, benchmark_name: str | None, profile: str | None, all_profiles: bool, all_models: bool, model: str | None, output: str | None, output_dir: str | None, jsonl_path: str | None, verbose: bool, timeout: int, retry_count: int, base_url: str | None, provider: str | None, model_workers: int, fixture_workers: int):
    """Run one or all benchmarks against the specified model."""
    # -a means all benchmarks + all models (flat comparison), unless a specific model is given
    if run_all:
        all_benchmarks_flag = True
        if not model:
            all_models = True

    # Normalize to single "run_all_benchmarks" flag
    run_all_benchmarks = run_all or all_benchmarks_flag

    if run_all_benchmarks and benchmark_name:
        raise click.ClickException("Cannot use --benchmark with --all-benchmarks. Choose one or the other.")

    if not run_all_benchmarks and not benchmark_name:
        raise click.ClickException("Must specify either --benchmark <name> or --all-benchmarks.")

    if all_profiles and all_models:
        raise click.ClickException("Cannot use --all-profiles with --all-models. Choose one.")

    if (all_profiles or all_models) and profile:
        raise click.ClickException("Cannot use --profile with --all-profiles or --all-models.")

    if (all_profiles or all_models) and model:
        raise click.ClickException("Cannot use --model with --all-profiles or --all-models.")

    # Check git availability on startup
    if not check_git_availability():
        click.echo("Error: Git CLI is required but not found in PATH", err=True)
        sys.exit(1)

    config = load_config()

    # Build the list of (profile_name, resolved_profile_dict, models_list) tuples to run
    runs: list[tuple[str, dict, list[str]]] = []

    if all_profiles or all_models:
        profiles = config.get("models", {})
        if not profiles:
            raise click.ClickException("No profiles defined in config. Add a 'models' object to gitbench.json.")

        if all_models:
            # Flatten: each model gets its own entry with its parent profile's config
            for profile_name, profile_values in profiles.items():
                resolved = resolve_profile(config, profile_name)
                for m in resolved.get("models", []):
                    runs.append((profile_name, resolved, [m]))
        else:
            # all_profiles: each profile is one entry with its full models list
            for profile_name in profiles:
                resolved = resolve_profile(config, profile_name)
                runs.append((profile_name, resolved, resolved.get("models", [])))
    else:
        # Single profile/model mode (existing behavior)
        profile_values: dict = {}

        if profile:
            profile_values = resolve_profile(config, profile)
        elif model and model != "mock":
            profile_values = find_profile_for_model(config, model)

        profile_models: list[str] = profile_values.get("models", [])

        if model:
            models_to_run = [model]
        elif profile_models:
            models_to_run = profile_models
        else:
            models_to_run = ["mock"]

        resolved_base_url = base_url or profile_values.get("base_url")
        resolved_api_key = profile_values.get("api_key")
        resolved_provider = provider or profile_values.get("provider")

        has_real_models = any(m != "mock" for m in models_to_run)
        if has_real_models and not resolved_api_key and profile_values.get("_api_key_env"):
            raise click.ClickException(
                f"Environment variable {profile_values['_api_key_env']} is not set "
                f"(required by profile '{profile}')"
            )

        effective_profile_name = profile or "(inline)"
        runs.append((effective_profile_name, profile_values, models_to_run))

    total_models = sum(len(r[2]) for r in runs)
    if total_models == 1:
        logger.info(f"Starting benchmark(s) with model: {runs[0][2][0]}")
    else:
        logger.info(f"Starting benchmark(s) with {total_models} models across {len(runs)} profile(s)")

    # Discover benchmarks once
    global _benchmark_registry
    if not _benchmark_registry:
        _benchmark_registry = discover_benchmarks()

    benchmarks_to_run: list[str]
    if run_all_benchmarks:
        benchmarks_to_run = list(_benchmark_registry.keys())
    else:
        benchmarks_to_run = [benchmark_name]

    unknown_benchmarks = [name for name in benchmarks_to_run if name not in _benchmark_registry]
    if unknown_benchmarks:
        available = list(_benchmark_registry.keys())
        raise click.ClickException(
            f"Unknown benchmark: {unknown_benchmarks[0]}. Available: {available}"
        )

    try:
        # Run each (profile, models) entry
        all_profile_results: list[dict] = []
        pending_outputs: list[tuple[str, dict]] = []
        progress_model_names_by_run = _progress_model_names_for_runs(runs)
        progress_table = TerminalProgressTable(
            [name for names in progress_model_names_by_run for name in names],
            benchmarks_to_run,
        )

        def announce_model(profile_label: str, models_to_run: list[str], current_model: str) -> None:
            if progress_table.enabled:
                return
            if len(runs) > 1 or len(models_to_run) > 1:
                parts = []
                if profile_label:
                    parts.append(profile_label)
                parts.append(f"model '{current_model}'")
                click.echo(f"\nRunning benchmarks ({', '.join(parts)})...", err=True)
            for bench_name in benchmarks_to_run:
                click.echo(f"  Running '{bench_name}'...", err=True)

        def finish_model_result(model_result: dict) -> None:
            summary = model_result["summary"]
            logger.info(
                "Model '%s' completed: %d/%d fixtures passed",
                model_result["model"],
                summary["total_passed"],
                summary["total_fixtures"],
            )

        def append_pending_output(profile_name: str, model_result: dict) -> None:
            if output_dir or jsonl_path:
                envelope = build_run_envelope(
                    model=model_result["model"],
                    profile=profile_name,
                    results=model_result["results"],
                )
                pending_outputs.append((profile_name, envelope))

        def append_profile_result(profile_name: str, all_model_results: list[dict]) -> None:
            profile_fixtures = sum(r["summary"]["total_fixtures"] for r in all_model_results)
            profile_passed = sum(r["summary"]["total_passed"] for r in all_model_results)
            all_profile_results.append({
                "profile": profile_name,
                "summary": {
                    "total_models": len(all_model_results),
                    "total_fixtures": profile_fixtures,
                    "total_passed": profile_passed,
                    "overall_pass_at_k": round(profile_passed / profile_fixtures, 4) if profile_fixtures > 0 else 0.0,
                },
                "models": all_model_results,
            })

        if all_models and model_workers > 1 and total_models > 1:
            worker_count = min(model_workers, total_models)
            click.echo(f"Running up to {worker_count} model(s) concurrently.", err=True)
            ordered_results: list[dict | None] = [None] * len(runs)

            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                future_to_run_index = {}
                for run_index, (profile_name, profile_conf, models_to_run) in enumerate(runs):
                    if not models_to_run:
                        continue

                    current_model = models_to_run[0]
                    p_base_url = base_url or profile_conf.get("base_url")
                    p_api_key = profile_conf.get("api_key")
                    p_provider = provider or profile_conf.get("provider")
                    p_api_key_env = profile_conf.get("_api_key_env")

                    if current_model != "mock" and not p_api_key and p_api_key_env:
                        click.echo(f"Skipping profile '{profile_name}': env var {p_api_key_env} not set", err=True)
                        continue

                    profile_label = f"profile '{profile_name}'" if len(runs) > 1 else ""
                    announce_model(profile_label, models_to_run, current_model)
                    future = executor.submit(
                        run_model_benchmarks,
                        current_model,
                        benchmarks_to_run,
                        timeout=timeout,
                        retry_count=retry_count,
                        base_url=p_base_url,
                        api_key=p_api_key,
                        provider=p_provider,
                        verbose=verbose,
                        progress=progress_table,
                        progress_model_name=progress_model_names_by_run[run_index][0],
                        fixture_workers=fixture_workers,
                    )
                    future_to_run_index[future] = run_index

                for future in as_completed(future_to_run_index):
                    run_index = future_to_run_index[future]
                    ordered_results[run_index] = future.result()

            for run_index, model_result in enumerate(ordered_results):
                if model_result is None:
                    continue
                profile_name, _profile_conf, _models_to_run = runs[run_index]
                finish_model_result(model_result)
                append_pending_output(profile_name, model_result)
                append_profile_result(profile_name, [model_result])

            all_model_results = [mr for mr in ordered_results if mr is not None]

        else:
            for run_index, (profile_name, profile_conf, models_to_run) in enumerate(runs):
                p_base_url = base_url or profile_conf.get("base_url")
                p_api_key = profile_conf.get("api_key")
                p_provider = provider or profile_conf.get("provider")
                p_api_key_env = profile_conf.get("_api_key_env")

                # Validate api_key
                has_real_models = any(m != "mock" for m in models_to_run)
                if has_real_models and not p_api_key and p_api_key_env:
                    click.echo(f"Skipping profile '{profile_name}': env var {p_api_key_env} not set", err=True)
                    continue

                profile_label = f"profile '{profile_name}'" if len(runs) > 1 else ""

                all_model_results: list[dict] = []
                progress_model_names = progress_model_names_by_run[run_index]

                all_model_results: list[dict] = []

                if model_workers > 1 and len(models_to_run) > 1:
                    worker_count = min(model_workers, len(models_to_run))
                    click.echo(f"Running up to {worker_count} model(s) concurrently.", err=True)
                    ordered_results: list[dict | None] = [None] * len(models_to_run)
                    with ThreadPoolExecutor(max_workers=worker_count) as executor:
                        future_to_index = {}
                        for index, current_model in enumerate(models_to_run):
                            announce_model(profile_label, models_to_run, current_model)
                            future = executor.submit(
                                run_model_benchmarks,
                                current_model,
                                benchmarks_to_run,
                                timeout=timeout,
                                retry_count=retry_count,
                                base_url=p_base_url,
                                api_key=p_api_key,
                                provider=p_provider,
                                verbose=verbose,
                                progress=progress_table,
                                progress_model_name=progress_model_names[index],
                                fixture_workers=fixture_workers,
                            )
                            future_to_index[future] = index

                        for future in as_completed(future_to_index):
                            index = future_to_index[future]
                            ordered_results[index] = future.result()

                    for model_result in ordered_results:
                        if model_result is not None:
                            all_model_results.append(model_result)
                            finish_model_result(model_result)
                else:
                    for index, current_model in enumerate(models_to_run):
                        announce_model(profile_label, models_to_run, current_model)
                        model_result = run_model_benchmarks(
                            current_model,
                            benchmarks_to_run,
                            timeout=timeout,
                            retry_count=retry_count,
                            base_url=p_base_url,
                            api_key=p_api_key,
                            provider=p_provider,
                            verbose=verbose,
                            progress=progress_table,
                            progress_model_name=progress_model_names[index],
                            fixture_workers=fixture_workers,
                        )
                        all_model_results.append(model_result)
                        finish_model_result(model_result)

                for model_result in all_model_results:
                    append_pending_output(profile_name, model_result)

                # Build per-profile output
                if len(runs) == 1:
                    # Single profile: keep backward-compat structure
                    if run_all_benchmarks:
                        # --all-benchmarks: summary + results wrapper
                        if len(all_model_results) == 1:
                            combined = all_model_results[0]
                            if "model" in combined:
                                combined.pop("model")
                        else:
                            grand_fixtures = sum(r["summary"]["total_fixtures"] for r in all_model_results)
                            grand_passed = sum(r["summary"]["total_passed"] for r in all_model_results)
                            combined = {
                                "summary": {
                                    "total_models": len(all_model_results),
                                    "total_fixtures": grand_fixtures,
                                    "total_passed": grand_passed,
                                    "overall_pass_at_k": round(grand_passed / grand_fixtures, 4) if grand_fixtures > 0 else 0.0,
                                },
                                "models": all_model_results,
                            }
                    else:
                        # Single benchmark: flat result(s)
                        if len(all_model_results) == 1 and len(all_model_results[0]["results"]) == 1:
                            # Single model, single benchmark: raw BenchmarkResult dict
                            combined = all_model_results[0]["results"][0]
                        else:
                            # Single benchmark, multiple models: list of results with model key
                            single_results = []
                            for mr in all_model_results:
                                for r in mr["results"]:
                                    single_results.append({"model": mr["model"], **r})
                            combined = single_results if len(single_results) > 1 else single_results[0]
                else:
                    # Multiple profiles: nest under profile name
                    append_profile_result(profile_name, all_model_results)

        progress_table.close()

        # Collect all results for summary table
        all_results: list[dict] = []
        for model_result in all_model_results:
            for r in model_result.get("results", []):
                all_results.append(r)

        # Print summary table to stdout (suppressed when piped)
        if all_results:
            summary_table = SummaryTable(all_results)
            summary_table.render()

        for _profile_name, envelope in pending_outputs:
            if output_dir:
                written = write_output_dir(envelope, output_dir)
                click.echo(f"  Saved: {written}", err=True)

            if jsonl_path:
                written = write_jsonl(envelope, jsonl_path)
                click.echo(f"  Appended: {written}", err=True)

        # Final output assembly
        if len(runs) > 1:
            grand_fixtures = sum(p["summary"]["total_fixtures"] for p in all_profile_results)
            grand_passed = sum(p["summary"]["total_passed"] for p in all_profile_results)
            grand_models = sum(p["summary"]["total_models"] for p in all_profile_results)
            combined = {
                "summary": {
                    "total_profiles": len(all_profile_results),
                    "total_models": grand_models,
                    "total_fixtures": grand_fixtures,
                    "total_passed": grand_passed,
                    "overall_pass_at_k": round(grand_passed / grand_fixtures, 4) if grand_fixtures > 0 else 0.0,
                },
                "profiles": all_profile_results,
            }
        else:
            # Single profile: combined was built inside the run loop
            pass

        output_json = json.dumps(combined, indent=2)

        if output:
            Path(output).write_text(output_json)
            click.echo(f"\nResults written to: {output}", err=True)
        else:
            click.echo(output_json)

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command("list")
def list_benchmarks():
    """List available benchmarks."""
    # Check git availability
    if not check_git_availability():
        click.echo("Warning: Git CLI not found - some benchmarks may not work", err=True)

    # Discover and list benchmarks
    benchmarks = discover_benchmarks()

    if not benchmarks:
        click.echo("No benchmarks found.")
        return

    click.echo("Available benchmarks:")
    for name, benchmark_class in benchmarks.items():
        desc = getattr(benchmark_class, "description", "")
        click.echo(f"  - {name}: {desc}")


@cli.command("profiles")
def list_profiles():
    """List model profiles from gitbench.json."""
    from gitbench.config import find_config

    config_path = find_config()
    if config_path is None:
        click.echo("No config file found. Create a gitbench.json with a 'models' object.")
        click.echo("Searched: ./gitbench.json, ./.gitbench.json, ~/.gitbench.json")
        return

    config = load_config(config_path)
    profiles = config.get("models", {})

    if not profiles:
        click.echo(f"Config found at {config_path} but no 'models' profiles defined.")
        return

    click.echo(f"Profiles from {config_path}:")
    for name, values in profiles.items():
        # Normalize models display: support both "model" (string) and "models" (list)
        models_list = values.get("models")
        if models_list is None:
            single = values.get("model", "?")
            models_str = single
        elif isinstance(models_list, list):
            models_str = ", ".join(models_list) if models_list else "?"
        else:
            models_str = str(models_list)

        base_url = values.get("base_url", "")
        api_key_env = values.get("api_key_env", "")
        api_key = values.get("api_key", "")
        provider = values.get("provider", "")
        parts = [f"models=[{models_str}]"]
        if base_url:
            parts.append(f"base_url={base_url}")
        if provider:
            parts.append(f"provider={provider}")
        if api_key_env:
            parts.append(f"api_key_env={api_key_env}")
        elif api_key:
            parts.append("api_key=<set>")
        click.echo(f"  - {name}: {', '.join(parts)}")


@cli.command("render")
@click.option(
    "--input-dir",
    "-d",
    default=None,
    help="Directory of per-run JSON files (from --output-dir)",
)
@click.option(
    "--input",
    "-i",
    "input_file",
    default=None,
    type=click.Path(),
    help="JSONL file of run results (from --jsonl)",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    default="gitbench-report.html",
    show_default=True,
    type=click.Path(),
    help="Output HTML file path",
)
@click.option(
    "--title",
    "-t",
    default="GitBench Report",
    show_default=True,
    help="Report title",
)
@click.option(
    "--open",
    "open_browser",
    is_flag=True,
    help="Open the report in the default browser after rendering",
)
def render(input_dir: str | None, input_file: str | None, output_path: str, title: str, open_browser: bool):
    """Render a static HTML report from saved benchmark results.

    Reads run results from a directory of JSON files (--input-dir) or a
    JSONL file (--input), or both. Generates a self-contained HTML report
    with charts. No benchmarks are re-run.

    \b
    Examples:
      gitbench render --input-dir results/
      gitbench render --input results.jsonl -o report.html
      gitbench render -d results/ -i extra.jsonl --open
    """
    import webbrowser

    from gitbench.render import aggregate_runs, load_runs_from_dir, load_runs_from_jsonl, render_html

    if not input_dir and not input_file:
        raise click.ClickException("Provide --input-dir and/or --input to specify result files.")

    runs: list[dict] = []

    if input_dir:
        try:
            dir_runs = load_runs_from_dir(input_dir)
            click.echo(f"Loaded {len(dir_runs)} run(s) from {input_dir}", err=True)
            runs.extend(dir_runs)
        except FileNotFoundError as e:
            raise click.ClickException(str(e))

    if input_file:
        try:
            file_runs = load_runs_from_jsonl(input_file)
            click.echo(f"Loaded {len(file_runs)} run(s) from {input_file}", err=True)
            runs.extend(file_runs)
        except FileNotFoundError as e:
            raise click.ClickException(str(e))

    if not runs:
        raise click.ClickException("No valid run data found in the provided inputs.")

    # Deduplicate by timestamp + model (prefer first occurrence)
    seen = set()
    unique_runs = []
    for r in runs:
        key = (r.get("timestamp", ""), r.get("model", ""))
        if key not in seen:
            seen.add(key)
            unique_runs.append(r)
    runs = unique_runs

    click.echo(f"Rendering {len(runs)} unique run(s)...", err=True)

    data = aggregate_runs(runs)
    html = render_html(data, title=title)

    Path(output_path).write_text(html)
    click.echo(f"Report written to: {output_path}", err=True)

    if open_browser:
        webbrowser.open(f"file://{Path(output_path).resolve()}")


if __name__ == "__main__":
    cli()
