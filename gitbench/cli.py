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

import click

from gitbench.benchmarks import Benchmark
from gitbench.config import find_profile_for_model, load_config, resolve_profile
from gitbench.export import FORMAT_REGISTRY, get_available_formats
from gitbench.harness.model import MockModelClient, OllamaAdapter, OpenAIAdapter
from gitbench.harness.runner import BenchmarkRunner, RunProgress
from gitbench.harness.types import BenchmarkResult, Fixture, ModelMessage, Score
from gitbench.render import aggregate_runs, render_html, render_html_from_envelope, _run_sort_key
from gitbench.ui.progress import TerminalProgressTable, _progress_model_names, _progress_model_names_for_runs
from gitbench.ui.summary import SummaryTable
from gitbench.version import BENCHMARK_SUITE_VERSION, RESULT_SCHEMA_VERSION

DEFAULT_JSON_OUTPUT_PATH = "gitbench-results/{timestamp}/results-v{version}.json"
DEFAULT_HTML_OUTPUT_PATH = "gitbench-results/{timestamp}/report-v{version}.html"

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
        "version": RESULT_SCHEMA_VERSION,
        "schema_version": RESULT_SCHEMA_VERSION,
        "benchmark_suite_version": BENCHMARK_SUITE_VERSION,
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


def _version_slug(version: str | None = None) -> str:
    """Return a version string safe for generated filenames."""
    return _sanitize_filename(version or BENCHMARK_SUITE_VERSION)


def write_output_dir(envelope: dict, output_dir: str) -> Path:
    """Write a run envelope as a JSON file in the output directory.

    Filename format: {YYYY-MM-DDTHH-MM-SS}_{model}_v{benchmark_suite_version}.json
    If a collision exists (same timestamp + model + version within the same
    second), appends _2, _3, etc. to avoid overwriting.

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
    version = _version_slug(envelope.get("benchmark_suite_version"))
    base = f"{ts}_{model}_v{version}"

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


def write_text_file(path: str, content: str) -> Path:
    """Write text to a file, creating parent directories if needed."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    return file_path


def _get_config_output_path(config: dict, kind: str) -> str | None:
    """Return a configured output path for kind ('json' or 'html'), if set."""
    outputs = config.get("outputs") or config.get("output") or {}
    if not isinstance(outputs, dict):
        return None

    configured = outputs.get(kind)
    if configured:
        return str(configured)

    configured = outputs.get(f"{kind}_path")
    if configured:
        return str(configured)

    return None


def _default_output_timestamp() -> str:
    """Return the timestamp fragment used for default run output paths."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _format_default_output_path(path_template: str, timestamp: str) -> str:
    """Format a default output path template with run metadata."""
    return path_template.format(
        timestamp=timestamp,
        version=_version_slug(BENCHMARK_SUITE_VERSION),
    )


def resolve_run_output_paths(
    config: dict,
    *,
    json_output: str | None,
    html_output: str | None,
    default_timestamp: str | None = None,
) -> tuple[str, str]:
    """Resolve run JSON/HTML output paths.

    Precedence is explicit format-specific CLI option, config file, then
    built-in default.
    """
    default_timestamp = default_timestamp or _default_output_timestamp()

    resolved_json = (
        json_output
        or _get_config_output_path(config, "json")
        or _format_default_output_path(DEFAULT_JSON_OUTPUT_PATH, default_timestamp)
    )
    resolved_html = (
        html_output
        or _get_config_output_path(config, "html")
        or _format_default_output_path(DEFAULT_HTML_OUTPUT_PATH, default_timestamp)
    )

    return resolved_json, resolved_html




def stamp_benchmark_suite_version(payload: dict | list) -> dict | list:
    """Add the benchmark suite version to a result payload."""
    if isinstance(payload, dict):
        payload.setdefault("benchmark_suite_version", BENCHMARK_SUITE_VERSION)
        return payload
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                item.setdefault("benchmark_suite_version", BENCHMARK_SUITE_VERSION)
    return payload


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
    "--json-output",
    type=click.Path(),
    default=None,
    help=f"JSON output file path (default: {DEFAULT_JSON_OUTPUT_PATH}, configurable via gitbench.json outputs.json).",
)
@click.option(
    "--html-output",
    type=click.Path(),
    default=None,
    help=f"HTML report output file path (default: {DEFAULT_HTML_OUTPUT_PATH}, configurable via gitbench.json outputs.html).",
)
@click.option(
    "--output-dir",
    "-d",
    type=click.Path(),
    default=None,
    help="Directory to write per-run JSON files (auto-named with timestamp + model + suite version)",
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
    "--export",
    "-e",
    "export_list",
    multiple=True,
    default=[],
    help="Export file format(s): csv, json (can be specified multiple times)",
)
@click.option(
    "--export-format",
    default="artificialanalysis",
    help="Schema for export (e.g. artificialanalysis). Overridden per --export item.",
)
@click.option(
    "--export-path",
    type=click.Path(),
    default=None,
    help="Path to write export file. If not specified, derives from model + timestamp.",
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
def run(
    run_all: bool,
    all_benchmarks_flag: bool,
    benchmark_name: str | None,
    profile: str | None,
    all_profiles: bool,
    all_models: bool,
    model: str | None,
    json_output: str | None,
    html_output: str | None,
    output_dir: str | None,
    jsonl_path: str | None,
    export_list: list[str],
    export_format: str,
    export_path: str | None,
    verbose: bool,
    timeout: int,
    retry_count: int,
    base_url: str | None,
    provider: str | None,
    model_workers: int,
    fixture_workers: int,
):
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
    resolved_json_output, resolved_html_output = resolve_run_output_paths(
        config,
        json_output=json_output,
        html_output=html_output,
    )
    stdout_json_enabled = (
        json_output is None
        and html_output is None
        and _get_config_output_path(config, "json") is None
        and _get_config_output_path(config, "html") is None
    )

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
            verbose=verbose,
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
                    model_client = get_model_client(
                        current_model,
                        timeout=timeout,
                        retry_count=retry_count,
                        base_url=p_base_url,
                        api_key=p_api_key,
                        provider=p_provider,
                    )
                    runner = BenchmarkRunner(_benchmark_registry, model_client)
                    future = executor.submit(
                        runner.run_all,
                        benchmarks_to_run,
                        model_name=current_model,
                        fixture_workers=fixture_workers,
                        progress=progress_table,
                        progress_model_name=progress_model_names_by_run[run_index][0],
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
                            model_client = get_model_client(
                                current_model,
                                timeout=timeout,
                                retry_count=retry_count,
                                base_url=p_base_url,
                                api_key=p_api_key,
                                provider=p_provider,
                            )
                            runner = BenchmarkRunner(_benchmark_registry, model_client)
                            future = executor.submit(
                                runner.run_all,
                                benchmarks_to_run,
                                model_name=current_model,
                                fixture_workers=fixture_workers,
                                progress=progress_table,
                                progress_model_name=progress_model_names[index],
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
                        model_client = get_model_client(
                            current_model,
                            timeout=timeout,
                            retry_count=retry_count,
                            base_url=p_base_url,
                            api_key=p_api_key,
                            provider=p_provider,
                        )
                        runner = BenchmarkRunner(_benchmark_registry, model_client)
                        model_result = runner.run_all(
                            benchmarks_to_run,
                            model_name=current_model,
                            fixture_workers=fixture_workers,
                            progress=progress_table,
                            progress_model_name=progress_model_names[index],
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
                            combined = dict(all_model_results[0])
                            if "model" in combined:
                                combined.pop("model")
                            stamp_benchmark_suite_version(combined)
                        else:
                            grand_fixtures = sum(r["summary"]["total_fixtures"] for r in all_model_results)
                            grand_passed = sum(r["summary"]["total_passed"] for r in all_model_results)
                            combined = {
                                "benchmark_suite_version": BENCHMARK_SUITE_VERSION,
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
                        combined = stamp_benchmark_suite_version(combined)
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

        if len(runs) > 1:
            grand_fixtures = sum(p["summary"]["total_fixtures"] for p in all_profile_results)
            grand_passed = sum(p["summary"]["total_passed"] for p in all_profile_results)
            grand_models = sum(p["summary"]["total_models"] for p in all_profile_results)
            combined = {
                "benchmark_suite_version": BENCHMARK_SUITE_VERSION,
                "summary": {
                    "total_profiles": len(all_profile_results),
                    "total_models": grand_models,
                    "total_fixtures": grand_fixtures,
                    "total_passed": grand_passed,
                    "overall_pass_at_k": round(grand_passed / grand_fixtures, 4) if grand_fixtures > 0 else 0.0,
                },
                "profiles": all_profile_results,
            }

        # ── Build run envelope (shared by exports + HTML) ──────────────────────────
        # Compute profile name before building envelope
        if len(runs) == 1:
            _profile_name_for_env = runs[0][0]
        elif all_profile_results:
            _profile_name_for_env = "(multi-profile)"
        else:
            _profile_name_for_env = "(unknown)"

        if all_model_results:
            _envelope = build_run_envelope(
                model=all_model_results[0]["model"],
                profile=_profile_name_for_env,
                results=[
                    r
                    for mr in all_model_results
                    for r in mr.get("results", [])
                ],
            )
        else:
            _envelope = build_run_envelope(
                model="unknown",
                profile=_profile_name_for_env,
                results=[],
            )

        # ── Export files ────────────────────────────────────────────────────────

        if export_list:
            for export_file_format in export_list:
                try:
                    export_func = FORMAT_REGISTRY[export_file_format]
                    if export_path:
                        target_path = export_path
                    else:
                        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                        model_name = all_model_results[0]["model"] if all_model_results else "unknown"
                        safe_model = _sanitize_filename(model_name)
                        ext = export_file_format  # csv → .csv, json → .json
                        version = _version_slug(BENCHMARK_SUITE_VERSION)
                        target_path = f"gitbench_export_{safe_model}_v{version}_{ts}.{ext}"
                    content = export_func(_envelope)
                    write_text_file(target_path, content)
                    click.echo(f"  Exported: {target_path}", err=True)
                except KeyError:
                    available = get_available_formats()
                    click.echo(
                        f"Unknown export format: '{export_file_format}'. "
                        f"Available: {', '.join(available)}",
                        err=True,
                    )
                    sys.exit(1)

        output_json = json.dumps(combined, indent=2)

        # Resolve effective profile name for the envelope (last single-profile result)
        if len(runs) == 1:
            _profile_name_for_env = runs[0][0]
        elif all_profile_results:
            _profile_name_for_env = "(multi-profile)"
        else:
            _profile_name_for_env = "(unknown)"

        write_text_file(resolved_json_output, output_json)
        click.echo(f"\nJSON results written to: {resolved_json_output}", err=True)

        try:
            envelopes_for_html = [envelope for _profile_name, envelope in pending_outputs]
            if len(envelopes_for_html) > 1:
                html = render_html(aggregate_runs(envelopes_for_html), title="GitBench Report")
            else:
                html = render_html_from_envelope(
                    envelopes_for_html[0] if envelopes_for_html else _envelope,
                    title="GitBench Report",
                )
            if html:
                write_text_file(resolved_html_output, html)
                click.echo(f"HTML report written to: {resolved_html_output}", err=True)
            else:
                click.echo("Warning: HTML generation returned no content; HTML report was not written.", err=True)
        except Exception as _html_exc:
            logger.warning("HTML generation failed (%s): %s", type(_html_exc).__name__, _html_exc)
            click.echo(f"Warning: HTML generation failed: {_html_exc}", err=True)

        if stdout_json_enabled:
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

    # Deduplicate by version + timestamp + model (prefer first occurrence)
    seen = set()
    unique_runs = []
    for r in runs:
        key = (
            r.get("benchmark_suite_version", ""),
            r.get("timestamp", ""),
            r.get("model", ""),
        )
        if key not in seen:
            seen.add(key)
            unique_runs.append(r)
    runs = sorted(unique_runs, key=_run_sort_key)

    click.echo(f"Rendering {len(runs)} unique run(s)...", err=True)

    data = aggregate_runs(runs)
    html = render_html(data, title=title)

    write_text_file(output_path, html)
    click.echo(f"Report written to: {output_path}", err=True)

    if open_browser:
        webbrowser.open(f"file://{Path(output_path).resolve()}")


if __name__ == "__main__":
    cli()
