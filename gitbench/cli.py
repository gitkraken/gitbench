"""CLI for GitBench."""

import copy
import importlib
import inspect
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskID, TextColumn, TimeElapsedColumn

from gitbench.benchmarks import Benchmark
from gitbench.config import (
    find_profile_for_model,
    load_campaign_defaults,
    load_config,
    load_judge_config,
    load_project_env,
    load_result_safety_config,
    resolve_profile,
)
from gitbench.export import FORMAT_REGISTRY, get_available_formats
from gitbench.harness.capabilities import validate_models, load_effort_matrix, save_effort_mapping
from gitbench.harness.capacity import (
    CapacityInfo,
    RequestAttemptGate,
    RequestBudgetCoordinator,
    derive_capacity_info,
    describe_request_budgets,
    global_request_limit,
    resolve_cooldown_config,
    resolve_group_intervals,
    resolve_group_limits,
)
from gitbench.harness.model import (
    DEFAULT_MODEL_TIMEOUT,
    MockModelClient,
    OllamaAdapter,
    OpenAIAdapter,
    ReasoningDisableError,
    parse_model_name,
)
from gitbench.harness.reasoning import parse_model_reasoning
from gitbench.harness.runner import BenchmarkRunner, RunProgress
from gitbench.harness.types import BenchmarkResult, Fixture, ModelMessage, Score
from gitbench.render import _run_sort_key
from gitbench.result_doctoring import (
    RerunPlan,
    ZeroPassFixture,
    ZeroPassModel,
    ZeroPassModelBenchmark,
    build_rerun_plan,
    build_zero_pass_targets,
    find_timestamped_result_files,
    format_dry_run_summary,
    format_zero_pass_summary,
    load_result_payload,
    mark_scores_retried,
    replace_scores_and_recompute,
    write_result_payload,
)
from gitbench.result_safety import (
    ResultSafetyError,
    ResultSafetyProcessor,
    ResultSafetyReviewer,
    SafetyValidationError,
    find_timestamped_result_files as find_safety_result_files,
    refresh_derived_safety_hashes,
    sanitize_result_file,
    stamp_artifact_safety,
    validate_payload_safety,
    write_new_run_backup,
)
from gitbench.ui.display import RichProgressDisplay
from gitbench.harness.campaign import CampaignState
from gitbench.harness.scheduler import build_schedule
from gitbench.harness.campaign_orchestrator import plan_campaign, write_campaign_manifest
from gitbench.harness.campaign_executor import execute_campaign
from gitbench.harness.benchmark import Benchmark
from gitbench.version import BENCHMARK_SUITE_VERSION, RESULT_SCHEMA_VERSION, CAMPAIGN_SCHEMA_VERSION

DEFAULT_JSON_OUTPUT_PATH = "gitbench-results/{timestamp}/results-v{version}.json"
DEFAULT_LOG_DIR = "gitbench-logs"
DEFAULT_RETRY_COUNT = 3
DEFAULT_DOCTOR_TIMEOUT = 120
DEFAULT_BAILOUT_FAILURES = 3
REASONING_PREFLIGHT_MAX_TOKENS = 16
REASONING_PREFLIGHT_PROMPT = (
    "Reply with exactly OK. Do not explain your answer."
)


@dataclass(frozen=True)
class ReasoningPreflightTarget:
    """One unique OpenRouter target that must prove reasoning is disabled."""

    profile_name: str
    model: str
    base_model: str
    provider: str
    base_url: str
    api_key: str | None
    timeout: int
    retry_count: int
    extra_body: dict[str, Any] | None


@dataclass(frozen=True)
class EffortPreflightTarget:
    """One unique model+effort pair to validate via Responses API."""

    profile_name: str
    model: str
    base_model: str
    requested_effort: str
    provider: str
    base_url: str
    api_key: str | None
    timeout: int


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


def _progress_model_names_for_runs(
    runs: list[tuple[str, dict, list[str]]],
) -> list[list[str]]:
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


def _effective_timeout(
    profile_conf: dict,
    cli_timeout: int | None,
) -> int:
    """Return the timeout to pass to the model adapter.

    Precedence: CLI override > profile timeout > 240 seconds.
    """
    if cli_timeout is not None:
        return cli_timeout
    profile_timeout = profile_conf.get("timeout")
    if profile_timeout is not None:
        return int(profile_timeout)
    return DEFAULT_MODEL_TIMEOUT


def _effective_retry_count(
    profile_conf: dict,
    cli_retry_count: int | None,
) -> int:
    """Return retry attempts, allowing profiles to override the default."""
    if cli_retry_count is not None:
        return cli_retry_count
    profile_retry_count = profile_conf.get("retry_count")
    if profile_retry_count is None:
        return DEFAULT_RETRY_COUNT
    return int(profile_retry_count)


def _effective_doctor_timeout(
    profile_conf: dict,
    cli_timeout: int | None,
) -> int:
    """Return the timeout to use for doctor repair reruns."""
    if cli_timeout is not None:
        return cli_timeout
    profile_timeout = profile_conf.get("timeout")
    if profile_timeout is None:
        return DEFAULT_DOCTOR_TIMEOUT
    return int(profile_timeout)


def _resolved_provider_name(profile_conf: dict) -> str:
    """Return the provider name that get_model_client will use."""
    provider = profile_conf.get("provider")
    if provider:
        return str(provider)

    base_url = profile_conf.get("base_url")
    if base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
        return "ollama"
    return "openai"


def _effective_provider_name(
    profile_conf: dict,
    *,
    base_url: str | None,
    provider_override: str | None,
) -> str:
    """Return the provider used after applying CLI overrides."""
    if provider_override:
        return provider_override
    provider = profile_conf.get("provider")
    if provider:
        return str(provider)
    if base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
        return "ollama"
    return "openai"


def _profile_model_generate_kwargs(profile_conf: dict) -> dict[str, Any]:
    """Return request kwargs configured for every call in a profile."""
    extra_body = profile_conf.get("extra_body")
    if extra_body is None:
        return {}
    if not isinstance(extra_body, dict):
        raise click.ClickException("Profile field 'extra_body' must be a JSON object.")
    return {"extra_body": extra_body}


def _discover_reasoning_preflight_targets(
    runs: list[tuple[str, dict, list[str]]],
    *,
    base_url_override: str | None,
    provider_override: str | None,
    timeout_override: int | None,
    retry_count_override: int | None,
) -> list[ReasoningPreflightTarget]:
    """Deduplicate statically valid OpenRouter ``none`` targets."""
    targets: list[ReasoningPreflightTarget] = []
    seen: set[tuple[str, str, str, str]] = set()

    for profile_name, profile_conf, models in runs:
        effective_base_url = base_url_override or profile_conf.get("base_url")
        if not effective_base_url or "openrouter.ai" not in effective_base_url.lower():
            continue
        effective_provider = _effective_provider_name(
            profile_conf,
            base_url=effective_base_url,
            provider_override=provider_override,
        )
        request_kwargs = _profile_model_generate_kwargs(profile_conf)
        extra_body = request_kwargs.get("extra_body")
        routing_identity = json.dumps(
            extra_body or {},
            sort_keys=True,
            separators=(",", ":"),
        )

        for full_model in models:
            if full_model == "mock" or full_model.startswith(("mock#", "mock:")):
                continue
            base_model, reasoning_level = parse_model_reasoning(full_model)
            if reasoning_level != "none":
                continue

            identity = (
                effective_provider.lower(),
                str(effective_base_url).rstrip("/").lower(),
                base_model,
                routing_identity,
            )
            if identity in seen:
                continue
            seen.add(identity)
            targets.append(
                ReasoningPreflightTarget(
                    profile_name=profile_name,
                    model=full_model,
                    base_model=base_model,
                    provider=effective_provider,
                    base_url=str(effective_base_url),
                    api_key=profile_conf.get("api_key"),
                    timeout=_effective_timeout(profile_conf, timeout_override),
                    retry_count=_effective_retry_count(
                        profile_conf,
                        retry_count_override,
                    ),
                    extra_body=extra_body,
                )
            )

    return targets


def _run_reasoning_preflights(
    targets: list[ReasoningPreflightTarget],
) -> None:
    """Run one bounded canary for every unique OpenRouter ``none`` target."""
    failures: list[str] = []

    for target in targets:
        logger.info(
            "Preflighting reasoning disablement for %s via %s",
            target.model,
            target.base_url,
        )
        model_client = get_model_client(
            target.model,
            timeout=target.timeout,
            retry_count=target.retry_count,
            base_url=target.base_url,
            api_key=target.api_key,
            provider=target.provider,
        )
        generate_kwargs: dict[str, Any] = {
            "max_tokens": REASONING_PREFLIGHT_MAX_TOKENS,
        }
        if target.extra_body is not None:
            generate_kwargs["extra_body"] = target.extra_body

        try:
            model_client.generate(
                [ModelMessage(role="user", content=REASONING_PREFLIGHT_PROMPT)],
                **generate_kwargs,
            )
        except ReasoningDisableError as exc:
            failures.append(
                f"'{target.model}': {exc.reason}"
            )
        except Exception as exc:
            failures.append(
                f"'{target.model}': {type(exc).__name__}: {exc}"
            )

    if failures:
        raise click.ClickException(
            "Reasoning preflight failed for "
            f"{len(failures)} model(s) that did not disable reasoning:\n\n  "
            + "\n  ".join(failures)
            + "\n\nBenchmark fixtures were not started."
        )


EFFORT_PREFLIGHT_PROMPTS = [
    # Counting / character reasoning
    (
        "Count the number of 'r' letters in the word 'strawberry'. "
        "Think step by step, then answer with just the number."
    ),
    # Arithmetic
    (
        "A car wash takes 12 minutes per car. How many cars can be washed "
        "in 2 hours? Think step by step, then answer with just the number."
    ),
    # Common sense / trade-off reasoning
    (
        "The car wash is only 100m away from my house. Should I walk "
        "or drive? Think step by step, then answer with just 'walk' "
        "or 'drive'."
    ),
]
EFFORT_PREFLIGHT_DELAY_S = 1.0  # pause between preflight calls to avoid rate limits


def _responses_url(base_url: str) -> str:
    """Normalize a base URL so it points at the Responses API."""
    normalized = base_url.rstrip("/")
    # OpenRouter's chat completions URL typically ends with /v1
    if normalized.endswith("/v1"):
        return normalized + "/responses"
    return normalized + "/responses"


def _discover_effort_preflight_targets(
    runs: list[tuple[str, dict, list[str]]],
    *,
    base_url_override: str | None,
    provider_override: str | None,
    timeout_override: int | None,
) -> list[EffortPreflightTarget]:
    """Collect unique OpenRouter model+effort pairs (except bare models with no suffix).

    Skips pairs already verified in the effort matrix cache.
    """
    matrix = load_effort_matrix()
    targets: list[EffortPreflightTarget] = []
    seen: set[tuple[str, str, str]] = set()
    skipped: int = 0

    for profile_name, profile_conf, models in runs:
        effective_base_url = base_url_override or profile_conf.get("base_url")
        if not effective_base_url or "openrouter.ai" not in effective_base_url.lower():
            continue
        effective_provider = _effective_provider_name(
            profile_conf,
            base_url=effective_base_url,
            provider_override=provider_override,
        )
        for full_model in models:
            if full_model == "mock" or full_model.startswith(("mock#", "mock:")):
                continue
            base_model, effort = parse_model_reasoning(full_model)
            if effort is None:
                continue

            normalized = base_model.split("/", 1)[1] if "/" in base_model else base_model

            # Skip already-verified combos
            if normalized in matrix and effort in matrix[normalized]:
                skipped += 1
                continue

            identity = (
                effective_provider.lower(),
                str(effective_base_url).rstrip("/").lower(),
                base_model,
                effort,
            )
            if identity in seen:
                continue
            seen.add(identity)
            targets.append(
                EffortPreflightTarget(
                    profile_name=profile_name,
                    model=full_model,
                    base_model=base_model,
                    requested_effort=effort,
                    provider=effective_provider,
                    base_url=str(effective_base_url),
                    api_key=profile_conf.get("api_key"),
                    timeout=_effective_timeout(profile_conf, timeout_override),
                )
            )

    if skipped:
        logger.info(
            "Skipped %d already-verified effort mapping(s); %d to preflight",
            skipped,
            len(targets),
        )

    return targets


def _call_responses_api(
    base_url: str,
    model: str,
    effort: str,
    prompt: str,
    api_key: str | None,
    timeout: int,
) -> dict | None:
    """Make a single Responses API call and return the parsed body."""
    url = _responses_url(base_url)
    payload = json.dumps({
        "model": model,
        "input": prompt,
        "reasoning": {"effort": effort},
    })
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(
        url, data=payload.encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _check_reasoning_evidence(body: dict) -> tuple[bool, int, bool]:
    """Return (has_evidence, reasoning_tokens, has_reasoning_output)."""
    output = body.get("output") or []
    usage = body.get("usage") or {}
    output_details = usage.get("output_tokens_details") or {}
    reasoning_tokens = output_details.get("reasoning_tokens") or 0
    has_reasoning_output = any(
        item.get("type") == "reasoning" for item in output
    )
    has_evidence = (
        isinstance(reasoning_tokens, (int, float)) and reasoning_tokens > 0
    ) or has_reasoning_output
    return has_evidence, reasoning_tokens, has_reasoning_output


def _run_effort_preflights(
    targets: list[EffortPreflightTarget],
) -> None:
    """Query the Responses API to discover effective effort for each target.

    Verifies actual reasoning occurred by checking for reasoning output
    items and reasoning token counts.  Runs every target before reporting
    failures so the matrix cache is populated for passing models.
    """
    failures: list[str] = []
    # Load matrix to check whether model supports reasoning at OTHER levels
    matrix = load_effort_matrix()
    first = True

    logger.info(
        "Effort preflight: verifying %d model-effort pair(s)", len(targets)
    )
    for t in targets:
        logger.debug("  -> %s (effort=%s)", t.model, t.requested_effort)

    for target in targets:
        if not first:
            time.sleep(EFFORT_PREFLIGHT_DELAY_S)
        first = False

        click.echo(
            f"  Effort preflight: {target.model} (requested {target.requested_effort})…",
            err=True,
            nl=False,
        )

        effective_effort = None
        has_evidence = False
        reasoning_tokens = 0
        has_reasoning_output = False

        for prompt_index, prompt in enumerate(EFFORT_PREFLIGHT_PROMPTS):
            body = _call_responses_api(
                base_url=target.base_url,
                model=target.base_model,
                effort=target.requested_effort,
                prompt=prompt,
                api_key=target.api_key,
                timeout=target.timeout,
            )
            if body is None:
                continue
            if body.get("error"):
                continue

            effective_effort = (body.get("reasoning") or {}).get("effort")
            has_evidence, reasoning_tokens, has_reasoning_output = _check_reasoning_evidence(body)

            if target.requested_effort == "none" or has_evidence:
                break  # got what we need

            # Not reasoning yet — pause before next retry
            if prompt_index < len(EFFORT_PREFLIGHT_PROMPTS) - 1:
                time.sleep(0.5)

        if body is None or body.get("error"):
            api_msg = "API error"
            if body and body.get("error"):
                api_err = body["error"]
                api_msg = f"API error: {api_err.get('message', str(api_err)) if isinstance(api_err, dict) else str(api_err)}"
            click.echo(f" {api_msg}", err=True)
            continue

        if effective_effort is None:
            click.echo(" no reasoning.effort in response", err=True)
            continue

        if target.requested_effort != "none" and not has_evidence:
            normalized = (
                target.base_model.split("/", 1)[1]
                if "/" in target.base_model
                else target.base_model
            )
            model_supports_reasoning = bool(matrix.get(normalized))

            # Log the raw response details for diagnosis
            output = body.get("output") or []
            logger.warning(
                "Effort preflight for '%s' (effort=%s): no reasoning evidence. "
                "effective_effort=%s reasoning_tokens=%s has_reasoning_output=%s "
                "output_types=%s",
                target.model,
                target.requested_effort,
                effective_effort,
                reasoning_tokens,
                has_reasoning_output,
                [item.get("type") for item in output],
            )

            if model_supports_reasoning:
                click.echo(
                    f" effort '{target.requested_effort}' not honored",
                    err=True,
                )
                failures.append(
                    f"'{target.model}': requested effort "
                    f"'{target.requested_effort}' produced no reasoning, "
                    f"but lower effort levels are supported. "
                    f"This model may not support high effort levels."
                )
            else:
                click.echo(" model does not support reasoning", err=True)
                failures.append(
                    f"'{target.model}': requested effort "
                    f"'{target.requested_effort}' but the model produced "
                    f"no reasoning output or tokens."
                )
            continue

        if effective_effort is None:
            click.echo(" no reasoning.effort in response", err=True)
            logger.warning(
                "Effort preflight for '%s' (requested effort=%s): "
                "Responses API did not return reasoning.effort",
                target.model,
                target.requested_effort,
            )
            continue

        if effective_effort != target.requested_effort:
            click.echo(
                f" mapped to {effective_effort}",
                err=True,
            )
            logger.warning(
                "Effort mismatch for '%s': requested '%s' but provider "
                "used '%s'. OpenRouter mapped the requested effort to the "
                "nearest supported level.",
                target.model,
                target.requested_effort,
                effective_effort,
            )
        else:
            reasoning_note = ""
            if target.requested_effort == "none" and has_evidence:
                reasoning_note = " but reasoning was produced"
            elif target.requested_effort != "none" and has_evidence:
                if prompt_index > 0:
                    reasoning_note = f" (verified, prompt {prompt_index + 1})"
                else:
                    reasoning_note = " (verified)"
            click.echo(f" confirmed ({effective_effort}){reasoning_note}", err=True)
            logger.info(
                "Effort preflight for '%s': requested '%s', effective '%s'",
                target.model,
                target.requested_effort,
                effective_effort,
            )

        # Persist the verified mapping
        normalized = (
            target.base_model.split("/", 1)[1]
            if "/" in target.base_model
            else target.base_model
        )
        save_effort_mapping(
            model_id=normalized,
            requested=target.requested_effort,
            effective=effective_effort,
        )

    if failures:
        raise click.ClickException(
            "Effort preflight failed for "
            f"{len(failures)} model(s):\n\n  "
            + "\n  ".join(failures)
            + "\n\nRemove these models or adjust their effort levels."
        )


def _doctor_progress_label(profile_conf: dict, model: str) -> str:
    """Format doctor progress as provider/model:effort when effort exists."""
    provider = _resolved_provider_name(profile_conf)
    base_model, effort = parse_model_name(model)
    model_label = f"{base_model}:{effort}" if effort else base_model
    if model_label.startswith(f"{provider}/"):
        return model_label
    return f"{provider}/{model_label}"

# Keep package logs off stderr unless a command explicitly installs a handler.
logging.getLogger("gitbench").addHandler(logging.NullHandler())
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


def get_model_client(
    model: str,
    timeout: int = DEFAULT_MODEL_TIMEOUT,
    retry_count: int = DEFAULT_RETRY_COUNT,
    base_url: str | None = None,
    api_key: str | None = None,
    provider: str | None = None,
    attempt_gate: "RequestAttemptGate | None" = None,
) -> OpenAIAdapter | OllamaAdapter | MockModelClient:
    """Get the model client based on model name and provider.

    Args:
        model: Model name. Use 'mock' for testing.
        timeout: Timeout in seconds for model generation (default: 240).
        retry_count: Number of retry attempts on failure.
        base_url: Optional API base URL. For Ollama, defaults to http://localhost:11434.
                  For OpenAI-compatible providers, set explicitly.
        api_key: Optional API key for OpenAI-compatible providers.
        provider: Explicit provider type: 'ollama', 'openai', or None to auto-detect.
                  When a profile is used, this comes from the config's 'provider' field.
        attempt_gate: Optional request-attempt gate for capacity coordination.

    Returns:
        The appropriate model client instance.
    """
    if model == "mock" or model.startswith(("mock#", "mock:")):
        return MockModelClient(model=model)

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
        return OllamaAdapter(model=model, base_url=ollama_base, timeout=timeout, retry_count=retry_count, attempt_gate=attempt_gate)
    else:
        return OpenAIAdapter(model=model, timeout=timeout, retry_count=retry_count, base_url=base_url, api_key=api_key, attempt_gate=attempt_gate)


def _build_result_safety_processor(
    config: dict[str, Any],
    *,
    required: bool = False,
) -> ResultSafetyProcessor | None:
    """Build the configured single-model result-safety processor."""
    try:
        safety_config = load_result_safety_config(config)
    except SystemExit as exc:
        raise click.ClickException(str(exc)) from exc

    if safety_config is None:
        if required:
            raise click.ClickException(
                "Result safety is not configured. Add "
                "'result_safety.profile' to gitbench.json."
            )
        return None

    profile_name = safety_config["profile"]
    model_name = safety_config["model"]
    profile = safety_config["resolved_profile"]
    api_key_env = profile.get("_api_key_env")
    if (
        not model_name.startswith("mock")
        and api_key_env
        and not profile.get("api_key")
    ):
        raise click.ClickException(
            f"Environment variable {api_key_env} is not set for result-safety "
            f"profile '{profile_name}'."
        )

    model_client = get_model_client(
        model_name,
        timeout=_effective_timeout(profile, None),
        retry_count=_effective_retry_count(profile, None),
        base_url=profile.get("base_url"),
        api_key=profile.get("api_key"),
        provider=profile.get("provider"),
    )
    reviewer = ResultSafetyReviewer(
        model_client,
        profile_name=profile_name,
        model_name=model_name,
        generate_kwargs=_profile_model_generate_kwargs(profile),
    )
    return ResultSafetyProcessor(reviewer)


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
    output_mode: str = "both",
) -> dict:
    """Wrap benchmark results in a metadata envelope for structured output.

    Args:
        model: Model name used for this run.
        profile: Profile name (or '(inline)' if no profile).
        results: List of BenchmarkResult dicts.
        output_mode: ``text``, ``json_schema``, or ``both`` (default).

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
        "output_mode": output_mode,
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

    Filename format:
    {YYYY-MM-DDTHH-MM-SS}_{model}_{output_mode}_v{benchmark_suite_version}.json
    If a collision exists (same timestamp + model + mode + version within the
    same second), appends _2, _3, etc. to avoid overwriting.

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
    output_mode = _sanitize_filename(envelope.get("output_mode", "text"))
    version = _version_slug(envelope.get("benchmark_suite_version"))
    base = f"{ts}_{model}_{output_mode}_v{version}"

    # Non-destructive: add counter suffix on collision
    candidate = dir_path / f"{base}.json"
    counter = 2
    while candidate.exists():
        candidate = dir_path / f"{base}_{counter}.json"
        counter += 1

    candidate.write_text(json.dumps(envelope, indent=2, allow_nan=False))
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
        f.write(json.dumps(envelope, allow_nan=False) + "\n")

    return file_path


def _replace_envelope_results_in_place(
    envelope: dict[str, Any],
    sanitized: dict[str, Any],
) -> None:
    """Apply sanitized results while preserving shared combined-output references."""
    current_results = envelope.get("results")
    sanitized_results = sanitized.get("results")
    if not isinstance(current_results, list) or not isinstance(sanitized_results, list):
        raise ResultSafetyError("Sanitized run envelope is missing result lists.")
    if len(current_results) != len(sanitized_results):
        raise ResultSafetyError("Sanitized run envelope changed the result count.")

    for current, replacement in zip(current_results, sanitized_results):
        if not isinstance(current, dict) or not isinstance(replacement, dict):
            raise ResultSafetyError("Sanitized benchmark results must be objects.")
        current.clear()
        current.update(replacement)

    for key, value in sanitized.items():
        if key != "results":
            envelope[key] = value


def _validate_report_safety_input(path: Path) -> None:
    """Validate every artifact in a JSON or JSONL report input."""
    try:
        if path.suffix.lower() == ".jsonl":
            for line_number, line in enumerate(
                path.read_text().splitlines(),
                start=1,
            ):
                if not line.strip():
                    continue
                payload = json.loads(line)
                validate_payload_safety(
                    payload,
                    artifact_name=f"{path} line {line_number}",
                )
            return

        payload = json.loads(path.read_text())
        validate_payload_safety(payload, artifact_name=str(path))
    except json.JSONDecodeError as exc:
        raise SafetyValidationError(f"{path} contains invalid JSON.") from exc


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


def _default_log_path(timestamp: str | None = None) -> Path:
    """Return the benchmark run log path for a timestamp."""
    timestamp = timestamp or _default_output_timestamp()
    return Path(DEFAULT_LOG_DIR) / f"run-{timestamp}.log"


def configure_run_logging(log_path: str | Path | None = None) -> Path:
    """Route GitBench runtime logs to a file, never the benchmark TUI stream."""
    resolved = Path(log_path) if log_path is not None else _default_log_path()
    resolved.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if getattr(handler, "_gitbench_run_log_handler", False):
            root_logger.removeHandler(handler)
            handler.close()

    handler = logging.FileHandler(resolved, encoding="utf-8")
    handler._gitbench_run_log_handler = True
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
    return resolved


def _format_default_output_path(path_template: str, timestamp: str) -> str:
    """Format a default output path template with run metadata."""
    return path_template.format(
        timestamp=timestamp,
        version=_version_slug(BENCHMARK_SUITE_VERSION),
    )


def resolve_run_output_path(
    config: dict,
    *,
    json_output: str | None,
    default_timestamp: str | None = None,
) -> str:
    """Resolve the run JSON output path.

    Precedence is explicit CLI option, config file, then built-in default.
    """
    default_timestamp = default_timestamp or _default_output_timestamp()

    return (
        json_output
        or _get_config_output_path(config, "json")
        or _format_default_output_path(DEFAULT_JSON_OUTPUT_PATH, default_timestamp)
    )




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


def _resolve_doctor_profile(config: dict, profile_name: str, model_name: str) -> dict:
    """Resolve the profile/model pair needed by doctor before rerunning."""
    if not profile_name:
        raise click.ClickException(
            f"Cannot resolve model '{model_name}' because the result has no profile"
        )

    try:
        profile_conf = resolve_profile(config, profile_name)
    except SystemExit as exc:
        raise click.ClickException(str(exc)) from exc

    api_key_env = profile_conf.get("_api_key_env")
    if not model_name.startswith("mock") and api_key_env and not profile_conf.get("api_key"):
        raise click.ClickException(
            f"Environment variable {api_key_env} is not set "
            f"(required by profile '{profile_name}')"
        )

    return profile_conf


def _validate_run_credentials(runs: list[tuple[str, dict, list[str]]]) -> None:
    """Fail before model calls when a configured credential variable is missing."""
    for profile_name, profile_conf, models in runs:
        api_key_env = profile_conf.get("_api_key_env")
        if not api_key_env or profile_conf.get("api_key"):
            continue
        if any(not model.startswith("mock") for model in models):
            raise click.ClickException(
                f"Environment variable {api_key_env} is not set "
                f"(required by profile '{profile_name}')"
            )


def _display_campaign_plan(
    campaign_id: str,
    trials: int,
    benchmarks_to_run: list[str],
    runs: list[tuple[str, dict, list[str]]],
    modes_to_run: list[str],
    resolved_judge_config: dict[str, Any] | None,
) -> None:
    """Print a campaign scope preview and persist or resume a planned manifest."""
    import random

    global _benchmark_registry
    if not _benchmark_registry:
        _benchmark_registry = discover_benchmarks()

    fixture_ids: list[str] = []
    benchmark_instances: list[tuple[str, Benchmark]] = []
    for benchmark_name in benchmarks_to_run:
        benchmark_class = _benchmark_registry.get(benchmark_name)
        if benchmark_class is None:
            continue
        benchmark = benchmark_class()
        benchmark_instances.append((benchmark_name, benchmark))
        for fixture in benchmark.load_fixtures():
            fixture_ids.append(fixture.id)

    models: list[tuple[str, str, dict[str, Any]]] = []
    for profile_name, profile_conf, models_list in runs:
        for full_model in models_list:
            from gitbench.harness.reasoning import parse_model_reasoning
            base_model, effort = parse_model_reasoning(full_model)
            models.append((full_model, effort or "none", profile_conf))

    output_modes = list(modes_to_run)
    planned_attempts = trials * len(fixture_ids) * len(models) * len(output_modes)
    judge_estimate = planned_attempts if resolved_judge_config is not None else 0
    # Safety review, when configured, is evaluated once per retained raw attempt.
    safety_estimate = planned_attempts if resolved_judge_config is not None else 0

    click.echo("\n── Campaign plan ──", err=True)
    click.echo(f"  Campaign ID: {campaign_id}", err=True)
    click.echo(f"  Trials: {trials}", err=True)
    click.echo(f"  Benchmarks: {len(benchmarks_to_run)}", err=True)
    click.echo(f"  Models: {len(models)}", err=True)
    click.echo(f"  Output modes: {', '.join(output_modes)}", err=True)
    click.echo(f"  Fixtures: {len(fixture_ids)}", err=True)
    click.echo(f"  Planned target attempts: {planned_attempts}", err=True)
    if judge_estimate:
        click.echo(f"  Estimated judge calls: {judge_estimate}", err=True)
    if safety_estimate:
        click.echo(f"  Estimated safety-review calls: {safety_estimate}", err=True)

    # Load any existing campaign manifest to show resume state.
    from gitbench.harness.campaign_store import CampaignStore, build_resume_plan
    store = CampaignStore(campaign_id)
    existing = store.load_manifest()
    if existing is not None:
        needed = build_resume_plan(existing, store)
        reused = planned_attempts - len(needed)
        completed = existing.completed_attempts
        valid = existing.valid_attempts
        failures = completed - valid
        click.echo(f"  Existing valid attempts: {reused}", err=True)
        click.echo(f"  Remaining attempts: {len(needed)}", err=True)
        click.echo(f"  Completed attempts: {completed}", err=True)
        click.echo(f"  Valid attempts: {valid}", err=True)
        if failures:
            click.echo(f"  Failed/invalid attempts: {failures}", err=True)
        click.echo(f"  Campaign state: {existing.state.value}", err=True)
        click.echo(
            f"  Publication state: {existing.publication_state.value}",
            err=True,
        )
        if existing.legacy:
            click.echo("  Legacy campaign: true", err=True)
    else:
        # Persist a planned manifest with fixture hashes.  Use a deterministic
        # seed when the user did not supply one so resume can reconstruct order.
        scheduler_seed = random.randrange(0, 2**32)
        try:
            campaign = plan_campaign(
                campaign_id=campaign_id,
                benchmarks=benchmark_instances,
                models=models,
                output_modes=output_modes,
                planned_trial_count=trials,
                scheduler_seed=scheduler_seed,
                judge_config=resolved_judge_config,
                fixture_generation_version=BENCHMARK_SUITE_VERSION,
            )
            manifest_path = write_campaign_manifest(campaign)
            click.echo(f"  Manifest: {manifest_path}", err=True)
        except Exception as exc:
            logger.warning("Could not persist campaign manifest: %s", exc)


def _validate_doctor_targets(config: dict, plan) -> dict[tuple[str, str], dict]:
    """Validate and cache config profiles for every doctor target.

    Historical result models can be rerun through their original profile even
    when they are no longer listed in the current profile config. Targets are
    skipped only when the profile itself or its required credentials are missing.
    """
    resolved: dict[tuple[str, str], dict] = {}
    for target in plan.targets:
        key = (target.profile, target.model)
        if key not in resolved:
            try:
                resolved[key] = _resolve_doctor_profile(
                    config,
                    target.profile,
                    target.model,
                )
            except click.ClickException:
                resolved[key] = None
    return resolved


def _doctor_one_file(
    input_path: Path,
    *,
    output_path: Path | None,
    timeout: int | None,
    include_all_failures: bool = False,
    bailout_failures: int = DEFAULT_BAILOUT_FAILURES,
    progress: Progress | None = None,
    progress_task: TaskID | None = None,
) -> tuple[Path, int]:
    """Doctor one result file and return output path plus repaired fixture count."""
    payload = load_result_payload(input_path)
    plan = build_rerun_plan(payload)

    zero_pass_targets: list = []
    if include_all_failures:
        zero_pass_targets = build_zero_pass_targets(payload)

    all_targets = list(plan.targets) + zero_pass_targets

    # Remove duplicates: if a (profile, model, benchmark, fixture_id) combo
    # appears in both doctorable and zero-pass targets, keep only once
    seen_fixtures: dict[tuple[str, str, str], set[str]] = {}
    deduped: list = []
    for t in all_targets:
        key = (t.profile, t.model, t.benchmark)
        if key not in seen_fixtures:
            seen_fixtures[key] = set()
        new_ids = set(t.fixture_ids) - seen_fixtures[key]
        if new_ids:
            seen_fixtures[key] |= new_ids
            deduped.append(
                type(t)(t.profile, t.model, t.benchmark, tuple(sorted(new_ids)))
            )

    total_fixture_count = sum(len(t.fixture_ids) for t in deduped)
    if total_fixture_count == 0:
        return input_path, 0

    config = load_config()
    resolved_profiles = _validate_doctor_targets(config, RerunPlan(targets=deduped))

    global _benchmark_registry
    if not _benchmark_registry:
        _benchmark_registry = discover_benchmarks()

    final_output_path = output_path or input_path
    consecutive_failures: dict[tuple[str, str], int] = {}
    repaired_count = 0

    for target in deduped:
        model_key = (target.profile, target.model)
        profile_conf = resolved_profiles.get(model_key)
        if profile_conf is None:
            # Model not in config — skip
            if progress is not None and progress_task is not None:
                progress.update(
                    progress_task,
                    advance=len(target.fixture_ids),
                    description=f"Skipping {target.model}/{target.benchmark} (not in config)",
                )
            continue

        if consecutive_failures.get(model_key, 0) >= bailout_failures:
            if progress is not None and progress_task is not None:
                progress.update(
                    progress_task,
                    advance=len(target.fixture_ids),
                    description=f"Skipping {target.model}/{target.benchmark} "
                    f"({consecutive_failures[model_key]} consecutive failures)",
                )
            continue

        progress_label = _doctor_progress_label(profile_conf, target.model)
        progress_description = (
            f"Doctoring {input_path.parent.name}/{progress_label}/"
            f"{target.benchmark}"
        )
        if progress is not None and progress_task is not None:
            progress.update(progress_task, description=progress_description)

        model_client = get_model_client(
            target.model,
            timeout=_effective_doctor_timeout(profile_conf, timeout),
            retry_count=_effective_retry_count(profile_conf, None),
            base_url=profile_conf.get("base_url"),
            api_key=profile_conf.get("api_key"),
            provider=profile_conf.get("provider"),
        )
        runner = BenchmarkRunner(
            _benchmark_registry,
            model_client,
            model_generate_kwargs=_profile_model_generate_kwargs(profile_conf),
        )
        result = runner.run_benchmark(
            target.benchmark,
            selected_fixture_ids=list(target.fixture_ids),
            fixture_workers=1,
            progress=None,
            progress_model_name=target.model,
        )
        replace_scores_and_recompute(payload, target, result.to_dict())
        mark_scores_retried(payload, target)
        write_result_payload(final_output_path, payload)

        # Rate-limit: 1s pause between targets to avoid upstream global rate limits
        time.sleep(1.0)

        # Track consecutive failures for bailout
        if result.passed == 0 and result.total > 0:
            consecutive_failures[model_key] = consecutive_failures.get(model_key, 0) + 1
        else:
            consecutive_failures[model_key] = 0

        repaired_count += len(target.fixture_ids)
        if progress is not None and progress_task is not None:
            progress.update(
                progress_task,
                advance=len(target.fixture_ids),
                description=progress_description,
            )
    return final_output_path, repaired_count


@click.group()
def cli():
    """GitBench: Benchmark harness for evaluating LLM-generated git commit messages."""
    pass


@cli.command("doctor")
@click.argument("result_file", required=False, type=click.Path(exists=True))
@click.option(
    "--latest",
    is_flag=True,
    help="Doctor every JSON result file in timestamped gitbench-results/ directories.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print the doctor plan without model calls or file writes.",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(),
    default=None,
    help="Path to write repaired JSON. Defaults to updating the input file.",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=None,
    help=(
        "Timeout in seconds per doctor rerun attempt "
        f"(default: profile timeout or {DEFAULT_DOCTOR_TIMEOUT})."
    ),
)
@click.option(
    "--include-all-failures",
    is_flag=True,
    help=(
        "Also rerun fixtures from 100%-failure models and fixtures, "
        f"with early bailout after {DEFAULT_BAILOUT_FAILURES} consecutive zero-pass reruns per model."
    ),
)
def doctor(
    result_file: str | None,
    latest: bool,
    dry_run: bool,
    output_path: str | None,
    timeout: int | None,
    include_all_failures: bool,
):
    """Repair an existing result file by rerunning doctorable failures."""
    if latest and result_file:
        raise click.ClickException("Use either RESULT_FILE or --latest, not both.")
    if not latest and not result_file:
        raise click.ClickException("Provide RESULT_FILE or use --latest.")

    input_paths = find_timestamped_result_files() if latest else [Path(result_file)]
    if not input_paths:
        raise click.ClickException("No result file found under gitbench-results")

    if output_path and len(input_paths) > 1:
        raise click.ClickException("--output can only be used with a single input file.")

    if dry_run:
        total_doctorable = 0
        total_zero_pass_fixtures = 0
        click.echo(f"Inputs: {len(input_paths)}")
        for input_path in input_paths:
            payload = load_result_payload(input_path)
            plan = build_rerun_plan(payload)
            total_doctorable += plan.doctorable_count
            click.echo(f"\nInput: {input_path}")
            click.echo(format_dry_run_summary(plan))

            if include_all_failures:
                zp_targets = build_zero_pass_targets(payload)
                zp_count = sum(len(t.fixture_ids) for t in zp_targets)
                total_zero_pass_fixtures += zp_count
                if zp_count:
                    click.echo(
                        f"[--include-all-failures] Would also rerun "
                        f"{zp_count} fixture(s) from zero-pass models/fixtures "
                        f"({len(zp_targets)} target(s))"
                    )

        click.echo(f"\nTotal doctorable failed fixtures: {total_doctorable}")
        if include_all_failures and total_zero_pass_fixtures:
            click.echo(
                f"Total zero-pass rerun fixtures: {total_zero_pass_fixtures}"
            )

        # Consolidated zero-pass summary across all inputs
        if not include_all_failures:
            zero_pass_models: dict[tuple[str, str], ZeroPassModel] = {}
            zero_pass_fixtures: dict[tuple[str, frozenset[str]], ZeroPassFixture] = {}
            zero_pass_mbs: dict[tuple[str, str, str], ZeroPassModelBenchmark] = {}
            for input_path in input_paths:
                plan = build_rerun_plan(load_result_payload(input_path))
                for m in plan.zero_pass_models:
                    key = (m.profile, m.model)
                    if key not in zero_pass_models:
                        zero_pass_models[key] = m
                for f in plan.zero_pass_fixtures:
                    key = (f.fixture_id, frozenset(f.benchmarks))
                    if key not in zero_pass_fixtures:
                        zero_pass_fixtures[key] = f
                for mb in plan.zero_pass_model_benchmarks:
                    key = (mb.profile, mb.model, mb.benchmark)
                    if key not in zero_pass_mbs:
                        zero_pass_mbs[key] = mb
            if zero_pass_models or zero_pass_fixtures or zero_pass_mbs:
                consolidated_plan = RerunPlan(
                    targets=[],
                    zero_pass_models=sorted(zero_pass_models.values(), key=lambda m: (m.profile, m.model)),
                    zero_pass_fixtures=sorted(zero_pass_fixtures.values(), key=lambda f: f.fixture_id),
                    zero_pass_model_benchmarks=sorted(zero_pass_mbs.values(), key=lambda m: (m.profile, m.model, m.benchmark)),
                )
                click.echo(f"\n{format_zero_pass_summary(consolidated_plan)}")
        return

    repaired_files = 0
    repaired_fixtures = 0
    total_doctorable = 0
    for input_path in input_paths:
        total_doctorable += build_rerun_plan(load_result_payload(input_path)).doctorable_count
        if include_all_failures:
            total_doctorable += sum(
                len(t.fixture_ids)
                for t in build_zero_pass_targets(load_result_payload(input_path))
            )

    # Consolidated warning about zero-pass models/fixtures
    if not include_all_failures:
        zero_pass_models: dict[tuple[str, str], ZeroPassModel] = {}
        zero_pass_fixtures: dict[tuple[str, frozenset[str]], ZeroPassFixture] = {}
        zero_pass_mbs: dict[tuple[str, str, str], ZeroPassModelBenchmark] = {}
        for input_path in input_paths:
            plan = build_rerun_plan(load_result_payload(input_path))
            for m in plan.zero_pass_models:
                key = (m.profile, m.model)
                if key not in zero_pass_models:
                    zero_pass_models[key] = m
            for f in plan.zero_pass_fixtures:
                key = (f.fixture_id, frozenset(f.benchmarks))
                if key not in zero_pass_fixtures:
                    zero_pass_fixtures[key] = f
            for mb in plan.zero_pass_model_benchmarks:
                key = (mb.profile, mb.model, mb.benchmark)
                if key not in zero_pass_mbs:
                    zero_pass_mbs[key] = mb
        if zero_pass_models or zero_pass_fixtures or zero_pass_mbs:
            consolidated_plan = RerunPlan(
                targets=[],
                zero_pass_models=sorted(zero_pass_models.values(), key=lambda m: (m.profile, m.model)),
                zero_pass_fixtures=sorted(zero_pass_fixtures.values(), key=lambda f: f.fixture_id),
                zero_pass_model_benchmarks=sorted(zero_pass_mbs.values(), key=lambda m: (m.profile, m.model, m.benchmark)),
            )
            click.echo(
                "\nWarning: The following models/fixtures scored 0% across all runs. "
                "Doctor will NOT repair these (they may indicate config or fixture data issues):\n",
                err=True,
            )
            click.echo(format_zero_pass_summary(consolidated_plan), err=True)

    progress_context = nullcontext(None)
    if total_doctorable > 0:
        progress_context = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} fixtures"),
            TimeElapsedColumn(),
            console=Console(stderr=True),
            transient=False,
        )

    with progress_context as progress:
        progress_task = None
        if progress is not None:
            progress_task = progress.add_task(
                "Doctoring results",
                total=total_doctorable,
            )

        for input_path in input_paths:
            written_path, count = _doctor_one_file(
                input_path,
                output_path=Path(output_path) if output_path else None,
                timeout=timeout,
                include_all_failures=include_all_failures,
                progress=progress,
                progress_task=progress_task,
            )
            if count == 0:
                click.echo(f"No doctorable failures found in: {input_path}")
                continue
            repaired_files += 1
            repaired_fixtures += count
            click.echo(f"Doctored results written to: {written_path}")

    click.echo(
        f"Doctor complete: repaired {repaired_fixtures} fixture(s) "
        f"across {repaired_files} file(s)."
    )


@cli.command("safety-doctor")
@click.argument(
    "result_file",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--latest",
    is_flag=True,
    help="Review JSON files in timestamped directories beneath gitbench-results/.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Classify and report planned redactions without writing files or backups.",
)
def safety_doctor(
    result_file: Path | None,
    latest: bool,
    dry_run: bool,
) -> None:
    """Review and sanitize historical result artifacts."""
    if bool(result_file) == latest:
        raise click.ClickException(
            "Specify exactly one RESULT_FILE or --latest."
        )

    config = load_config()
    processor = _build_result_safety_processor(config, required=True)
    assert processor is not None

    input_paths = find_safety_result_files() if latest else [result_file]
    if not input_paths:
        raise click.ClickException(
            "No JSON result files found in timestamped gitbench-results/ directories."
        )

    total_reviewed = 0
    total_redacted = 0
    total_skipped = 0
    click.echo(f"Inputs: {len(input_paths)}")

    for input_path in input_paths:
        assert input_path is not None
        click.echo(f"Reviewing: {input_path}")
        try:
            result = sanitize_result_file(
                input_path,
                processor,
                dry_run=dry_run,
            )
        except (OSError, ResultSafetyError) as exc:
            raise click.ClickException(f"{input_path}: {exc}") from exc

        total_reviewed += result.reviewed_scores
        total_redacted += result.redacted_scores
        total_skipped += result.skipped_scores
        action = "Would redact" if dry_run else "Redacted"
        click.echo(
            f"  Reviewed scores: {result.reviewed_scores + result.skipped_scores}; "
            f"{action.lower()}: {result.redacted_scores}; "
            f"already current: {result.skipped_scores}"
        )
        if result.backup_path is not None:
            click.echo(f"  Original backup: {result.backup_path}")

    prefix = "Dry run complete" if dry_run else "Safety doctor complete"
    click.echo(
        f"{prefix}: reviewed {total_reviewed + total_skipped} score(s), "
        f"redacted {total_redacted}, already current {total_skipped}."
    )


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
    default=None,
    type=click.IntRange(1),
    help=(
        "Timeout in seconds for each model attempt "
        "(default: profile timeout or 240)."
    ),
)
@click.option(
    "--retry-count",
    "-r",
    default=None,
    type=click.IntRange(1),
    help=(
        "Number of model attempts on retryable failures "
        f"(default: profile retry_count or {DEFAULT_RETRY_COUNT})."
    ),
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
@click.option(
    "--output-mode",
    default="both",
    type=click.Choice(["text", "json_schema", "both"], case_sensitive=True),
    show_default=True,
    help=(
        "Output mode for model responses. Defaults to 'both' which runs every model "
        "in text and JSON-schema modes producing separate raw run artifacts. "
        "'text' is free-form mode. 'json_schema' enforces fixture-specific JSON Schema structured output."
    ),
)
@click.option(
    "--judge",
    is_flag=True,
    help=(
        "Enable LLM judge scoring for configured benchmarks "
        "(overrides the judge config benchmarks list)."
    ),
)
@click.option(
    "--judge-profile",
    default=None,
    help=(
        "Override the judge model profile from config "
        "(e.g. 'openrouter-llms-as-judges')."
    ),
)
@click.option(
    "--campaign-id",
    default=None,
    help="Unique campaign identifier for repeated evaluation campaigns.",
)
@click.option(
    "--trials",
    default=None,
    type=click.IntRange(1),
    show_default=True,
    help="Number of complete trial rounds for each model/output-mode/fixture combination. Defaults to config campaign.default_trials or 3.",
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
    output_dir: str | None,
    jsonl_path: str | None,
    export_list: list[str],
    export_format: str,
    export_path: str | None,
    verbose: bool,
    timeout: int | None,
    retry_count: int | None,
    base_url: str | None,
    provider: str | None,
    model_workers: int,
    fixture_workers: int,
    output_mode: str,
    judge: bool,
    judge_profile: str | None,
    campaign_id: str | None,
    trials: int | None,
):
    """Run one or all benchmarks against the specified model."""
    run_log_path = configure_run_logging()
    logger.info("Benchmark run log started: %s", run_log_path)

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

    # Resolve campaign defaults from configuration.
    campaign_defaults = load_campaign_defaults(config)
    resolved_trials = trials if trials is not None else campaign_defaults.get("default_trials", 3)
    if campaign_defaults.get("require_campaign_id") and campaign_id is None:
        raise click.ClickException(
            "Configuration requires --campaign-id for every run."
        )

    result_safety_processor = _build_result_safety_processor(config)
    resolved_json_output = resolve_run_output_path(
        config,
        json_output=json_output,
    )
    stdout_json_enabled = (
        json_output is None
        and _get_config_output_path(config, "json") is None
    )

    # Resolve which output modes to run
    if output_mode == "both":
        modes_to_run = ["text", "json_schema"]
    else:
        modes_to_run = [output_mode]

    # When running both modes, suppress stdout output (combined JSON goes to file)
    if len(modes_to_run) > 1 and stdout_json_enabled:
        stdout_json_enabled = False

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
        elif model and not model.startswith("mock"):
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

        effective_profile_name = profile or "(inline)"
        runs.append((effective_profile_name, profile_values, models_to_run))

    _validate_run_credentials(runs)

    total_models = sum(len(r[2]) for r in runs)
    if total_models == 1:
        logger.info(f"Starting benchmark(s) with model: {runs[0][2][0]}")
    else:
        logger.info(f"Starting benchmark(s) with {total_models} models across {len(runs)} profile(s)")

    # Validate all model-reasoning combinations before any benchmarks execute
    all_models_to_validate: list[str] = []
    all_profile_configs: list[dict] = []
    for _profile_name, profile_conf, models_list in runs:
        for m in models_list:
            all_models_to_validate.append(m)
            all_profile_configs.append(profile_conf)

    validation_errors = validate_models(all_models_to_validate, all_profile_configs)
    if validation_errors:
        click.echo(
            f"\n  Validation failed: {len(validation_errors)} model-effort combination(s) are invalid:\n\n"
            f"  " + "\n\n  ".join(validation_errors) + "\n\n  Aborting run.\n",
            err=True,
        )
        sys.exit(1)

    preflight_targets = _discover_reasoning_preflight_targets(
        runs,
        base_url_override=base_url,
        provider_override=provider,
        timeout_override=timeout,
        retry_count_override=retry_count,
    )
    capacity_by_target: dict[tuple[int, int], CapacityInfo] = {}
    for run_index, (_profile_name, profile_conf, models_list) in enumerate(runs):
        for model_index, model_name in enumerate(models_list):
            info = derive_capacity_info(config, profile_conf, model_name)
            capacity_by_target[(run_index, model_index)] = info
    group_limits = resolve_group_limits(capacity_by_target.values())
    group_intervals = resolve_group_intervals(config, capacity_by_target.values())
    fallback_cooldown, _cooldown_overrides = resolve_cooldown_config(
        config, capacity_by_target.values()
    )

    request_budget = RequestBudgetCoordinator(
        global_limit=global_request_limit(
            config,
            fallback=max(1, model_workers * fixture_workers),
        ),
        group_limits=group_limits,
        group_intervals=group_intervals,
        fallback_cooldown=fallback_cooldown,
    )
    logger.info(
        describe_request_budgets(
            request_budget.global_limit,
            request_budget.group_limits,
            request_budget.group_intervals,
        )
    )

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

    _run_reasoning_preflights(preflight_targets)

    effort_targets = _discover_effort_preflight_targets(
        runs,
        base_url_override=base_url,
        provider_override=provider,
        timeout_override=timeout,
    )
    if effort_targets:
        logger.info(
            "Preflighting effort compatibility for %d model-effort pair(s)",
            len(effort_targets),
        )
        _run_effort_preflights(effort_targets)

    # Resolve judge configuration
    resolved_judge_config = None
    if judge or judge_profile:
        # CLI override: --judge or --judge-profile
        raw_judge = load_judge_config(config)
        if judge_profile:
            if raw_judge is None:
                raw_judge = {"profile": judge_profile}
            else:
                raw_judge = dict(raw_judge)
                raw_judge["profile"] = judge_profile
        if judge and raw_judge is None:
            raise click.ClickException(
                "--judge requires a judge profile. "
                "Add a 'judge' section to gitbench.json or use --judge-profile.\n"
                "Example: --judge --judge-profile my-judge-models"
            )
        if raw_judge is not None:
            # Validate profile exists
            if raw_judge["profile"]:
                try:
                    resolve_profile(config, raw_judge["profile"])
                except SystemExit as e:
                    raise click.ClickException(str(e))
            resolved_judge_config = dict(raw_judge)
            resolved_judge_config["_config"] = config
    else:
        # Use config-based judge if available
        raw_judge = load_judge_config(config)
        if raw_judge is not None:
            resolved_judge_config = dict(raw_judge)
            resolved_judge_config["_config"] = config

    if resolved_judge_config is not None:
        logger.info(
            "Judge enabled: profile=%s",
            resolved_judge_config.get("profile"),
        )

    # Validate that judge-required benchmarks have a judge configured.
    # Skip the requirement when all models are mock (testing mode).
    from gitbench.config import discover_judge_benchmarks

    all_models_mock = all(
        m == "mock" or m.startswith(("mock#", "mock:"))
        for _, _, models in runs
        for m in models
    )
    judge_required_requested = discover_judge_benchmarks(benchmarks_to_run)
    if judge_required_requested and resolved_judge_config is None and not all_models_mock:
        raise click.ClickException(
            f"Benchmark(s) {', '.join(judge_required_requested)} require an LLM judge. "
            "Add a 'judge' section to gitbench.json with a model profile "
            "for the judge models. Example:\n"
            '  "judge": {"profile": "my-judge-models"}'
        )

    if campaign_id:
        _display_campaign_plan(
            campaign_id=campaign_id,
            trials=resolved_trials,
            benchmarks_to_run=benchmarks_to_run,
            runs=runs,
            modes_to_run=modes_to_run,
            resolved_judge_config=resolved_judge_config,
        )

        from gitbench.export import export_campaign_report
        from gitbench.harness.campaign_store import (
            CampaignStore,
            validate_resume_compatibility,
        )

        store = CampaignStore(campaign_id)
        campaign = store.load_manifest()
        if campaign is None:
            raise click.ClickException(
                f"Campaign manifest was not created for {campaign_id}."
            )

        model_profile_by_id: dict[str, tuple[int, int, str, dict[str, Any]]] = {}
        model_ids: list[str] = []
        reasoning_efforts: list[str] = []
        for run_index, (profile_name, profile_conf, models_list) in enumerate(runs):
            for model_index, full_model in enumerate(models_list):
                base_model, effort = parse_model_reasoning(full_model)
                model_ids.append(full_model)
                reasoning_efforts.append(effort or "none")
                model_profile_by_id.setdefault(
                    full_model,
                    (run_index, model_index, profile_name, profile_conf),
                )

        qualified_fixture_ids: list[str] = []
        for benchmark_name in benchmarks_to_run:
            benchmark_class = _benchmark_registry.get(benchmark_name)
            if benchmark_class is None:
                continue
            for fixture in benchmark_class().load_fixtures():
                qualified_fixture_ids.append(f"{benchmark_name}/{fixture.id}")

        try:
            validate_resume_compatibility(
                campaign,
                benchmark_ids=benchmarks_to_run,
                fixture_ids=qualified_fixture_ids,
                model_ids=sorted(set(model_ids)),
                reasoning_efforts=sorted(set(reasoning_efforts)),
                output_modes=modes_to_run,
                planned_trial_count=resolved_trials,
                fixture_generation_version=BENCHMARK_SUITE_VERSION,
            )
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

        progress_display = RichProgressDisplay(
            _progress_model_names(model_ids),
            benchmarks_to_run,
            verbose=verbose,
            campaign_id=campaign_id,
            trials=resolved_trials,
            planned_attempts=campaign.planned_attempts,
            publication_state=campaign.publication_state.value,
        )

        runner_cache: dict[tuple[str, str], BenchmarkRunner] = {}

        def runner_for_identity(identity, *, judge_cache=None):
            try:
                run_index, model_index, _profile_name, profile_conf = model_profile_by_id[
                    identity.model_id
                ]
            except KeyError as exc:
                raise click.ClickException(
                    f"Campaign identity references unknown model: {identity.model_id}"
                ) from exc

            cache_key = (identity.model_id, identity.output_mode)
            if cache_key in runner_cache:
                return runner_cache[cache_key]

            p_base_url = base_url or profile_conf.get("base_url")
            p_api_key = profile_conf.get("api_key")
            p_provider = provider or profile_conf.get("provider")
            p_timeout = _effective_timeout(profile_conf, timeout)
            p_retry_count = _effective_retry_count(profile_conf, retry_count)
            capacity_info = capacity_by_target[(run_index, model_index)]
            model_client = get_model_client(
                identity.model_id,
                timeout=p_timeout,
                retry_count=p_retry_count,
                base_url=p_base_url,
                api_key=p_api_key,
                provider=p_provider,
                attempt_gate=RequestAttemptGate(
                    request_budget,
                    capacity_info.capacity_key,
                ),
            )
            runner = BenchmarkRunner(
                _benchmark_registry,
                model_client,
                request_budget=request_budget,
                capacity_key=capacity_info.capacity_key,
                output_mode=identity.output_mode,
                model_generate_kwargs=_profile_model_generate_kwargs(profile_conf),
                judge_config=resolved_judge_config,
                model_timeout=p_timeout,
                attempt_gate=RequestAttemptGate(
                    request_budget,
                    capacity_info.capacity_key,
                ),
                judge_cache=judge_cache,
            )
            runner_cache[cache_key] = runner
            return runner

        try:
            campaign = execute_campaign(
                campaign,
                store,
                runner_for_identity,
                progress=progress_display,
            )
        finally:
            progress_display.close()

        report_path = store.campaign_dir / "campaign-report.json"
        report_path.write_text(export_campaign_report(campaign))
        click.echo(f"\nCampaign report written to: {report_path}", err=True)

        if result_safety_processor is not None:
            from gitbench.harness.campaign_store import review_campaign_safety

            review_campaign_safety(campaign, result_safety_processor, store)
            click.echo(
                f"Safety review completed for campaign {campaign_id}: "
                f"{campaign.safety_summary}",
                err=True,
            )
        return

    # Collect all run envelopes for combined aggregation when running "both"
    all_mode_envelopes: list[dict] = []

    # Pre-compute fixture count for campaign-aware progress displays.
    fixture_ids: list[str] = []
    if campaign_id:
        for benchmark_name in benchmarks_to_run:
            benchmark_class = _benchmark_registry.get(benchmark_name)
            if benchmark_class is None:
                continue
            benchmark = benchmark_class()
            for fixture in benchmark.load_fixtures():
                fixture_ids.append(fixture.id)

    for output_mode in modes_to_run:
        if len(modes_to_run) > 1:
            click.echo(f"\n── Running in {output_mode} mode ──", err=True)
        mode_json_output = resolved_json_output
        progress_display: RichProgressDisplay | None = None
        try:
            # Run each (profile, models) entry
            all_profile_results: list[dict] = []
            pending_outputs: list[tuple[str, dict]] = []
            progress_model_names_by_run = _progress_model_names_for_runs(runs)
            all_models_flat = [name for names in progress_model_names_by_run for name in names]
            progress_kwargs: dict[str, Any] = {"verbose": verbose}
            if campaign_id:
                # Compute campaign scope for the live display.
                total_fixtures = len(fixture_ids)
                total_models = sum(len(r[2]) for r in runs)
                mode_planned_attempts = (
                    resolved_trials * total_fixtures * total_models
                )
                progress_kwargs.update(
                    {
                        "campaign_id": campaign_id,
                        "trials": resolved_trials,
                        "planned_attempts": mode_planned_attempts,
                        "publication_state": "draft",
                    }
                )
            progress_display = RichProgressDisplay(
                all_models_flat,
                benchmarks_to_run,
                **progress_kwargs,
            )

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
                    output_mode=output_mode,
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
                logger.info("Running up to %d model(s) concurrently.", worker_count)
                ordered_results: list[dict | None] = [None] * len(runs)

                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    future_to_run_index: dict = {}
                    active_group_counts: dict[str, int] = {}
                    pending_run_indices = [
                        run_index
                        for run_index, (_profile_name, _profile_conf, models_to_run) in enumerate(runs)
                        if models_to_run
                    ]

                    def can_submit_run(run_index: int) -> bool:
                        capacity_info = capacity_by_target[(run_index, 0)]
                        limit = group_limits.get(capacity_info.capacity_key)
                        if limit is None:
                            return True
                        return active_group_counts.get(capacity_info.capacity_key, 0) < limit

                    def submit_run(run_index: int) -> None:
                        profile_name, profile_conf, models_to_run = runs[run_index]
                        current_model = models_to_run[0]
                        p_base_url = base_url or profile_conf.get("base_url")
                        p_api_key = profile_conf.get("api_key")
                        p_provider = provider or profile_conf.get("provider")
                        p_api_key_env = profile_conf.get("_api_key_env")
                        p_timeout = _effective_timeout(profile_conf, timeout)
                        p_retry_count = _effective_retry_count(profile_conf, retry_count)

                        if not current_model.startswith("mock") and not p_api_key and p_api_key_env:
                            logger.warning(
                                "Skipping profile '%s': env var %s not set",
                                profile_name,
                                p_api_key_env,
                            )
                            return

                        model_client = get_model_client(
                            current_model,
                            timeout=p_timeout,
                            retry_count=p_retry_count,
                            base_url=p_base_url,
                            api_key=p_api_key,
                            provider=p_provider,
                            attempt_gate=RequestAttemptGate(
                                request_budget,
                                capacity_by_target[(run_index, 0)].capacity_key,
                            ),
                        )
                        capacity_info = capacity_by_target[(run_index, 0)]
                        runner = BenchmarkRunner(
                            _benchmark_registry,
                            model_client,
                            request_budget=request_budget,
                            capacity_key=capacity_info.capacity_key,
                            output_mode=output_mode,
                            model_generate_kwargs=_profile_model_generate_kwargs(
                                profile_conf
                            ),
                            judge_config=resolved_judge_config,
                            model_timeout=p_timeout,
                            attempt_gate=RequestAttemptGate(
                                request_budget,
                                capacity_info.capacity_key,
                            ),
                        )
                        future = executor.submit(
                            runner.run_all,
                            benchmarks_to_run,
                            model_name=current_model,
                            fixture_workers=fixture_workers,
                            progress=progress_display,
                            progress_model_name=progress_model_names_by_run[run_index][0],
                        )
                        future_to_run_index[future] = run_index
                        active_group_counts[capacity_info.capacity_key] = (
                            active_group_counts.get(capacity_info.capacity_key, 0) + 1
                        )

                    while pending_run_indices or future_to_run_index:
                        submitted_any = True
                        while len(future_to_run_index) < worker_count and submitted_any:
                            submitted_any = False
                            for pending_run_index in list(pending_run_indices):
                                if can_submit_run(pending_run_index):
                                    pending_run_indices.remove(pending_run_index)
                                    submit_run(pending_run_index)
                                    submitted_any = True
                                    break

                        if not future_to_run_index:
                            break

                        done, _pending = wait(
                            future_to_run_index,
                            return_when=FIRST_COMPLETED,
                        )
                        for future in done:
                            run_index = future_to_run_index.pop(future)
                            capacity_info = capacity_by_target[(run_index, 0)]
                            active_group_counts[capacity_info.capacity_key] -= 1
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
                    p_timeout = _effective_timeout(profile_conf, timeout)
                    p_retry_count = _effective_retry_count(profile_conf, retry_count)

                    # Validate api_key
                    has_real_models = any(not m.startswith("mock") for m in models_to_run)
                    if has_real_models and not p_api_key and p_api_key_env:
                        logger.warning(
                            "Skipping profile '%s': env var %s not set",
                            profile_name,
                            p_api_key_env,
                        )
                        continue

                    profile_label = f"profile '{profile_name}'" if len(runs) > 1 else ""

                    all_model_results: list[dict] = []
                    progress_model_names = progress_model_names_by_run[run_index]

                    all_model_results: list[dict] = []

                    if model_workers > 1 and len(models_to_run) > 1:
                        worker_count = min(model_workers, len(models_to_run))
                        logger.info("Running up to %d model(s) concurrently.", worker_count)
                        ordered_results: list[dict | None] = [None] * len(models_to_run)
                        with ThreadPoolExecutor(max_workers=worker_count) as executor:
                            future_to_index: dict = {}
                            active_group_counts: dict[str, int] = {}
                            pending_indices = list(range(len(models_to_run)))

                            def can_submit(index: int) -> bool:
                                capacity_info = capacity_by_target[(run_index, index)]
                                limit = group_limits.get(capacity_info.capacity_key)
                                if limit is None:
                                    return True
                                return active_group_counts.get(capacity_info.capacity_key, 0) < limit

                            def submit_model(index: int) -> None:
                                current_model = models_to_run[index]
                                capacity_info = capacity_by_target[(run_index, index)]
                                model_client = get_model_client(
                                    current_model,
                                    timeout=p_timeout,
                                    retry_count=p_retry_count,
                                    base_url=p_base_url,
                                    api_key=p_api_key,
                                    provider=p_provider,
                                    attempt_gate=RequestAttemptGate(
                                        request_budget,
                                        capacity_info.capacity_key,
                                    ),
                                )
                                runner = BenchmarkRunner(
                                    _benchmark_registry,
                                    model_client,
                                    request_budget=request_budget,
                                    capacity_key=capacity_info.capacity_key,
                                    output_mode=output_mode,
                                    model_generate_kwargs=_profile_model_generate_kwargs(
                                        profile_conf
                                    ),
                                    judge_config=resolved_judge_config,
                                    model_timeout=p_timeout,
                                    attempt_gate=RequestAttemptGate(
                                        request_budget,
                                        capacity_info.capacity_key,
                                    ),
                                )
                                future = executor.submit(
                                    runner.run_all,
                                    benchmarks_to_run,
                                    model_name=current_model,
                                    fixture_workers=fixture_workers,
                                    progress=progress_display,
                                    progress_model_name=progress_model_names[index],
                                )
                                future_to_index[future] = index
                                active_group_counts[capacity_info.capacity_key] = (
                                    active_group_counts.get(capacity_info.capacity_key, 0)
                                    + 1
                                )

                            while pending_indices or future_to_index:
                                submitted_any = True
                                while len(future_to_index) < worker_count and submitted_any:
                                    submitted_any = False
                                    for pending_index in list(pending_indices):
                                        if can_submit(pending_index):
                                            pending_indices.remove(pending_index)
                                            submit_model(pending_index)
                                            submitted_any = True
                                            break

                                if not future_to_index:
                                    break

                                done, _pending = wait(
                                    future_to_index,
                                    return_when=FIRST_COMPLETED,
                                )
                                for future in done:
                                    index = future_to_index.pop(future)
                                    capacity_info = capacity_by_target[(run_index, index)]
                                    active_group_counts[capacity_info.capacity_key] -= 1
                                    ordered_results[index] = future.result()

                        for model_result in ordered_results:
                            if model_result is not None:
                                all_model_results.append(model_result)
                                finish_model_result(model_result)
                    else:
                        for index, current_model in enumerate(models_to_run):
                            capacity_info = capacity_by_target[(run_index, index)]
                            model_client = get_model_client(
                                current_model,
                                timeout=p_timeout,
                                retry_count=p_retry_count,
                                base_url=p_base_url,
                                api_key=p_api_key,
                                provider=p_provider,
                                attempt_gate=RequestAttemptGate(
                                    request_budget,
                                    capacity_info.capacity_key,
                                ),
                            )
                            runner = BenchmarkRunner(
                                _benchmark_registry,
                                model_client,
                                request_budget=request_budget,
                                capacity_key=capacity_info.capacity_key,
                                output_mode=output_mode,
                                model_generate_kwargs=_profile_model_generate_kwargs(
                                    profile_conf
                                ),
                                judge_config=resolved_judge_config,
                                model_timeout=p_timeout,
                                attempt_gate=RequestAttemptGate(
                                    request_budget,
                                    capacity_info.capacity_key,
                                ),
                            )
                            model_result = runner.run_all(
                                benchmarks_to_run,
                                model_name=current_model,
                                fixture_workers=fixture_workers,
                                progress=progress_display,
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

            progress_display.close()

            # Collect all results for summary table (close() already printed summary)
            all_results: list[dict] = []
            for model_result in all_model_results:
                for r in model_result.get("results", []):
                    all_results.append(r)

            if result_safety_processor is not None:
                reviewed_outputs: list[
                    tuple[dict[str, Any], dict[str, Any], int]
                ] = []
                for _profile_name, envelope in pending_outputs:
                    reviewed = result_safety_processor.review_payload(envelope)
                    reviewed_outputs.append(
                        (envelope, reviewed.payload, reviewed.redacted_scores)
                    )

                # Required original backups complete before any normal writer runs.
                for envelope, _sanitized, redacted_scores in reviewed_outputs:
                    if redacted_scores:
                        try:
                            write_new_run_backup(copy.deepcopy(envelope))
                        except OSError as exc:
                            raise ResultSafetyError(
                                f"Could not write required result-safety backup: {exc}"
                            ) from exc

                for envelope, sanitized, _redacted_scores in reviewed_outputs:
                    _replace_envelope_results_in_place(envelope, sanitized)

            for _profile_name, envelope in pending_outputs:
                if output_dir:
                    written = write_output_dir(envelope, output_dir)
                    click.echo(f"  Saved: {written}", err=True)

                if jsonl_path:
                    written = write_jsonl(envelope, jsonl_path)
                    click.echo(f"  Appended: {written}", err=True)

                # Collect for cross-mode aggregation when running "both"
                all_mode_envelopes.append(envelope)

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

            if result_safety_processor is not None:
                if isinstance(combined, list):
                    combined = {
                        "benchmark_suite_version": BENCHMARK_SUITE_VERSION,
                        "results": combined,
                    }
                combined = result_safety_processor.review_payload(combined).payload

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
                    output_mode=output_mode,
                )
            else:
                _envelope = build_run_envelope(
                    model="unknown",
                    profile=_profile_name_for_env,
                    results=[],
                    output_mode=output_mode,
                )

            if result_safety_processor is not None:
                _envelope = result_safety_processor.review_payload(_envelope).payload

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

            # Write per-mode combined JSON only when running a single mode.
            # For "both" mode, aggregation happens after all modes complete.
            if len(modes_to_run) == 1:
                output_json = json.dumps(combined, indent=2, allow_nan=False)
                write_text_file(mode_json_output, output_json)
                click.echo(f"\nJSON results written to: {mode_json_output}", err=True)

                if stdout_json_enabled:
                    click.echo(output_json)

        except Exception as e:
            if progress_display is not None:
                progress_display.close()
            logger.exception("Benchmark failed in %s mode", output_mode)
            click.echo(f"Error in {output_mode} mode: {e}", err=True)
            if isinstance(e, ResultSafetyError):
                raise click.ClickException(str(e)) from e
            if len(modes_to_run) == 1:
                sys.exit(1)
            # Continue to next mode when running both
        finally:
            if progress_display is not None:
                progress_display.close()

    # For explicit "both" mode, --output-dir/--jsonl already received one raw
    # run envelope per model/mode.  Keep the default results-v*.json path raw as
    # well so `gitbench report` can ingest newly produced artifacts directly.
    if len(modes_to_run) > 1 and all_mode_envelopes:
        if not output_dir and not jsonl_path:
            for envelope in all_mode_envelopes:
                written = write_output_dir(envelope, str(Path(resolved_json_output).parent))
                click.echo(f"  Saved: {written}", err=True)

    # Integrate campaign publication with result-safety review when configured.
    if campaign_id and result_safety_processor is not None:
        from gitbench.harness.campaign_store import (
            CampaignStore,
            review_campaign_safety,
        )

        store = CampaignStore(campaign_id)
        campaign = store.load_manifest()
        if campaign is not None:
            review_campaign_safety(campaign, result_safety_processor, store)
            click.echo(
                f"\nSafety review completed for campaign {campaign_id}: "
                f"{campaign.safety_summary}",
                err=True,
            )


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

    load_project_env(config_path)
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
        provider = values.get("provider", "")
        parts = [f"models=[{models_str}]"]
        if base_url:
            parts.append(f"base_url={base_url}")
        if provider:
            parts.append(f"provider={provider}")
        if api_key_env:
            parts.append(f"api_key_env={api_key_env}")
        click.echo(f"  - {name}: {', '.join(parts)}")


def _warn_deprecated_report_flags(*, no_build: bool, open_browser: bool, dev: bool) -> None:
    deprecated_flags = []
    if no_build:
        deprecated_flags.append("--no-build")
    if open_browser:
        deprecated_flags.append("--open")
    if dev:
        deprecated_flags.append("--dev")

    for flag in deprecated_flags:
        click.echo(
            f"Warning: `gitbench report {flag}` is deprecated; the flag is now a no-op.",
            err=True,
        )
    if deprecated_flags:
        click.echo(
            "Use the top-level web module commands after JSON publication instead.",
            err=True,
        )


def _print_report_next_steps() -> None:
    click.echo("Next web commands:", err=True)
    click.echo("  cd web && pnpm build:db       # derive web/data/gitbench.db", err=True)
    click.echo("  cd web && pnpm build          # derive SQLite and build static pages", err=True)
    click.echo("  cd web && pnpm dev:api        # run local API-backed report", err=True)


def _resolve_report_output_path(output_path: str | None) -> str:
    if output_path:
        return output_path

    required_web_paths = (
        Path("web/package.json"),
        Path("web/scripts/build-db.mjs"),
    )
    missing = [path for path in required_web_paths if not path.is_file()]
    if missing:
        missing_list = ", ".join(str(path) for path in missing)
        raise click.ClickException(
            "Default report output requires the top-level web module in the "
            "current working directory. Run `gitbench report` from the "
            "repository root, or pass `--output <path>` to write standalone "
            f"JSON. Missing: {missing_list}"
        )

    return "web/public/results.json"


@cli.command("report")
@click.option(
    "--input-dir",
    "-d",
    default=None,
    help="Directory of per-run JSON files (default: gitbench-results/)",
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
    default=None,
    type=click.Path(),
    help="Output path for results.json (default: web/public/results.json)",
)
@click.option(
    "--no-build",
    is_flag=True,
    help="Deprecated no-op; report generation now only writes compatibility JSON",
)
@click.option(
    "--open",
    "open_browser",
    is_flag=True,
    help="Deprecated no-op; use web module commands to preview or open the report",
)
@click.option(
    "--dev",
    is_flag=True,
    help="Deprecated no-op; use `cd web && pnpm dev:api` for local development",
)
def report(input_dir: str | None, input_file: str | None, output_path: str | None, no_build: bool, open_browser: bool, dev: bool):
    """Publish compatibility JSON from benchmark results.

    Reads run results from gitbench-results/ (or --input-dir / --input),
    aggregates them into web/public/results.json, and prints the web module
    commands used to derive SQLite or view the report.

    \b
    Examples:
      gitbench report                            # publish JSON from gitbench-results/
      gitbench report --no-build                 # deprecated no-op flag
      gitbench report --open                     # deprecated no-op flag
      gitbench report -d my-results/ -i extra.jsonl
    """
    from gitbench.render import (
        aggregate_runs,
        load_aggregate_report,
        load_campaign_reports_from_dir,
        load_runs_from_combined,
        load_runs_from_dir,
        load_runs_from_jsonl,
        merge_aggregate_reports,
        render_json,
    )
    from gitbench.report_contract import (
        ReportArtifactContractError,
        validate_report_json_contract,
    )

    # Determine input directory
    results_dir = input_dir or "gitbench-results"
    json_output = _resolve_report_output_path(output_path)
    _warn_deprecated_report_flags(no_build=no_build, open_browser=open_browser, dev=dev)
    config = load_config()
    try:
        report_safety_config = load_result_safety_config(config)
    except SystemExit as exc:
        raise click.ClickException(str(exc)) from exc

    if report_safety_config is not None:
        if input_file:
            safety_inputs = [Path(input_file)]
        else:
            root = Path(results_dir)
            safety_inputs = sorted(root.glob("*.json")) if root.is_dir() else []
            if root.is_dir():
                for subdir in sorted(path for path in root.iterdir() if path.is_dir()):
                    safety_inputs.extend(sorted(subdir.glob("*.json")))
            safety_inputs = [
                path
                for path in safety_inputs
                if path.name not in {"campaign.json", "campaign-report.json"}
            ]

        try:
            for safety_input in safety_inputs:
                _validate_report_safety_input(safety_input)
        except SafetyValidationError as exc:
            raise click.ClickException(
                f"{exc} Run 'gitbench safety-doctor {safety_input}' before "
                "generating the report."
            ) from exc
        except ResultSafetyError as exc:
            raise click.ClickException(
                f"{safety_input}: {exc} Repair or regenerate this result artifact "
                "before generating the report."
            ) from exc

    runs: list[dict] = []
    aggregate_reports: list[dict] = []
    campaign_reports: list[dict] = []

    # 1. Try combined or raw run JSON from every timestamped subdirectory.
    #    Generated aggregate report JSON is ignored by load_runs_from_combined().
    combined_runs_loaded = False
    if not input_file:
        campaign_reports = load_campaign_reports_from_dir(results_dir)
        for _campaign_report in campaign_reports:
            click.echo("Loaded campaign artifact data", err=True)
        try:
            dir_path = Path(results_dir)
            if dir_path.is_dir():
                any_loaded = False
                for subdir in sorted(dir_path.iterdir()):
                    if subdir.is_dir():
                        for f in sorted(subdir.glob("*.json")):
                            aggregate_report = load_aggregate_report(str(f))
                            if aggregate_report:
                                click.echo(f"Loaded aggregate report data from {f}", err=True)
                                aggregate_reports.append(aggregate_report)
                                continue
                            combined_runs = load_runs_from_combined(str(f))
                            if combined_runs:
                                click.echo(f"Loaded {len(combined_runs)} run(s) from {f}", err=True)
                                runs.extend(combined_runs)
                                any_loaded = True
                if any_loaded:
                    combined_runs_loaded = True
        except Exception:
            pass

    # 2. Fall back: per-run directory of envelope files
    if not combined_runs_loaded and (input_dir or (not input_file and Path(results_dir).exists())):
        try:
            dir_runs = load_runs_from_dir(results_dir)
            if dir_runs:
                click.echo(f"Loaded {len(dir_runs)} run(s) from {results_dir}", err=True)
                runs.extend(dir_runs)
        except FileNotFoundError as e:
            if not input_file:
                raise click.ClickException(str(e))

    # 3. Load from JSONL file
    if input_file:
        try:
            file_runs = load_runs_from_jsonl(input_file)
            click.echo(f"Loaded {len(file_runs)} run(s) from {input_file}", err=True)
            runs.extend(file_runs)
        except FileNotFoundError as e:
            raise click.ClickException(str(e))

    if not runs and not aggregate_reports and not campaign_reports:
        raise click.ClickException(
            "No valid run data found. Run 'gitbench run -a' first or provide --input-dir/--input."
        )

    # Deduplicate by version + timestamp + model + output mode
    seen = set()
    unique_runs = []
    for r in runs:
        key = (
            r.get("benchmark_suite_version", ""),
            r.get("timestamp", ""),
            r.get("model", ""),
            r.get("output_mode", "text"),
        )
        if key not in seen:
            seen.add(key)
            unique_runs.append(r)
    runs = sorted(unique_runs, key=_run_sort_key)

    click.echo(
        f"Aggregating {len(runs)} unique run(s)"
        f", {len(aggregate_reports)} aggregate report file(s),"
        f" and {len(campaign_reports)} campaign report source(s)...",
        err=True,
    )

    data_sources = aggregate_reports.copy()
    data_sources.extend(campaign_reports)
    if runs:
        data_sources.append(aggregate_runs(runs))
    data = merge_aggregate_reports(data_sources)
    if report_safety_config is not None:
        refresh_derived_safety_hashes(data)
        stamp_artifact_safety(
            data,
            profile_name=report_safety_config["profile"],
            model_name=report_safety_config["model"],
        )
        try:
            validate_payload_safety(data, artifact_name="generated report data")
        except SafetyValidationError as exc:
            raise click.ClickException(str(exc)) from exc
    try:
        validate_report_json_contract(data)
    except ReportArtifactContractError as exc:
        raise click.ClickException(str(exc)) from exc
    render_json(data, json_output)
    click.echo(f"JSON data written to: {json_output}", err=True)
    _print_report_next_steps()


if __name__ == "__main__":
    cli()
