"""Model capability resolution and validation for GitBench.

Queries the OpenRouter models API to discover which models support reasoning,
caches the result, and merges with a shipped effort matrix to validate
model+effort combinations before benchmarks execute.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from gitbench.harness.reasoning import VALID_REASONING_LEVELS, parse_model_reasoning

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".cache" / "gitbench"
CACHE_FILE = CACHE_DIR / "model-capabilities.json"
CACHE_TTL = timedelta(days=7)

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_PARAM = "supported_parameters=reasoning"

_EFFORT_MATRIX_PATH = Path(__file__).parent.parent / "data" / "effort_matrix.json"
_EFFORT_MATRIX_VERSION = 1


def _load_cache() -> dict[str, Any] | None:
    """Load the cached model capabilities from disk.

    Returns:
        The cache dict if it exists and is valid JSON, or None.
    """
    try:
        if not CACHE_FILE.exists():
            return None
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load capabilities cache: %s", exc)
        return None


def _save_cache(data: dict[str, Any]) -> None:
    """Save model capabilities cache to disk."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def fetch_model_capabilities() -> dict[str, Any]:
    """Fetch model capabilities from the OpenRouter models API.

    Uses ``urllib`` (stdlib, consistent with the OllamaAdapter) to GET
    ``/api/v1/models?supported_parameters=reasoning``.  Only stores the
    set of model IDs that support reasoning to keep the cache compact.

    Returns:
        A dict with keys ``fetched_at`` (ISO timestamp) and
        ``reasoning_models`` (list of model ID strings).
    """
    url = f"{OPENROUTER_MODELS_URL}?{OPENROUTER_PARAM}"
    logger.info("Fetching model capabilities from OpenRouter...")

    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Failed to fetch model capabilities from OpenRouter: {exc}"
        ) from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid JSON response from OpenRouter models API"
        ) from exc

    data_list = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(data_list, list):
        raise RuntimeError(
            "Unexpected response format from OpenRouter models API"
        )

    reasoning_models: list[str] = []
    for entry in data_list:
        model_id = entry.get("id")
        if not model_id:
            continue
        supported = entry.get("supported_parameters")
        if isinstance(supported, list) and "reasoning" in supported:
            reasoning_models.append(model_id)

    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "reasoning_models": reasoning_models,
    }
    _save_cache(result)
    logger.info(
        "Fetched %d reasoning-capable models out of %d total.",
        len(reasoning_models),
        len(data_list),
    )
    return result


def load_effort_matrix() -> dict[str, dict[str, str]]:
    """Load the verified effort matrix from the package data directory.

    The matrix is populated by Responses API preflights and maps each
    model to a dict of ``{requested_effort: effective_effort}``.

    Returns:
        Dict mapping normalized model ID to effort mapping dict.
        Returns empty dict when the file is missing, malformed, or
        was written by an older preflight version.
    """
    try:
        with open(_EFFORT_MATRIX_PATH, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.warning("Could not load effort matrix: %s", exc)
        return {}

    # Version check — invalidate stale caches when preflight logic changes
    stored_version = data.get("_preflight_version", 0)
    if stored_version != _EFFORT_MATRIX_VERSION:
        logger.info(
            "Effort matrix version changed (%d → %d); "
            "discarding stale cached entries.",
            stored_version,
            _EFFORT_MATRIX_VERSION,
        )
        return {}

    matrix: dict[str, dict[str, str]] = {}
    for model_id, entry in data.get("models", {}).items():
        if isinstance(entry, dict) and "mappings" in entry:
            matrix[model_id] = entry["mappings"]
    return matrix


def save_effort_mapping(
    model_id: str,
    requested: str,
    effective: str,
) -> None:
    """Persist a verified effort mapping to the matrix file."""
    try:
        with open(_EFFORT_MATRIX_PATH, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"_comment": "", "_preflight_version": _EFFORT_MATRIX_VERSION, "models": {}}

    data["_preflight_version"] = _EFFORT_MATRIX_VERSION
    models = data.get("models", {})
    if model_id not in models:
        models[model_id] = {"mappings": {}}
    models[model_id]["mappings"][requested] = effective
    data["models"] = models

    with open(_EFFORT_MATRIX_PATH, "w") as f:
        json.dump(data, f, indent=2)


def resolve_capabilities() -> dict[str, Any]:
    """Resolve model capabilities by merging cache and matrix.

    Attempts to load the cache; if stale or missing, fetches fresh data.
    Merges reasoning-capable model IDs from the API with per-model effort
    levels from the shipped matrix.

    Returns:
        A dict with:
        * ``reasoning_models`` – set of model IDs supporting reasoning
        * ``effort_matrix`` – dict of model ID → list of valid levels
        * ``fetched_at`` – ISO timestamp of the capability data
    """
    cache = _load_cache()

    if cache is not None:
        try:
            fetched_at = datetime.fromisoformat(cache["fetched_at"])
        except (KeyError, ValueError):
            fetched_at = datetime.min.replace(tzinfo=timezone.utc)

        age = datetime.now(timezone.utc) - fetched_at
        if age <= CACHE_TTL:
            logger.debug("Using cached capabilities (age: %s)", age)
            return {
                "reasoning_models": set(cache.get("reasoning_models", [])),
                "effort_matrix": load_effort_matrix(),
                "fetched_at": cache["fetched_at"],
            }
        logger.debug("Cache is stale (age: %s), fetching fresh data.", age)

    try:
        fresh = fetch_model_capabilities()
        return {
            "reasoning_models": set(fresh.get("reasoning_models", [])),
            "effort_matrix": load_effort_matrix(),
            "fetched_at": fresh["fetched_at"],
        }
    except RuntimeError as exc:
        # If fetch fails but we have stale cache, warn and use it
        if cache is not None:
            logger.warning(
                "Could not refresh capabilities: %s. Using stale cache.", exc
            )
            return {
                "reasoning_models": set(cache.get("reasoning_models", [])),
                "effort_matrix": load_effort_matrix(),
                "fetched_at": cache.get("fetched_at", "unknown"),
            }
        raise


def _normalize_model(base_model: str) -> str:
    """Strip provider prefix (e.g. ``openai/gpt-4o`` → ``gpt-4o``)."""
    if "/" in base_model:
        return base_model.split("/", 1)[1]
    return base_model


def validate_models(
    models: list[str],
    profile_configs: list[dict] | None = None,
) -> list[str]:
    """Validate every configured model+effort combination.

    Called **before** any benchmarks execute.  This is the gate —
    if any combination is invalid the run aborts with diagnostics.
    Mock models (``mock``, ``mock#...``, ``mock:...``) bypass validation.

    Args:
        models: List of full model names (may include ``#level`` or ``:level`` suffixes).
        profile_configs: Optional list of profile configuration dicts (one per model,
            same order as *models*). Used to detect Ollama models so they receive
            warnings rather than errors.  If ``None``, all models are validated strictly.

    Returns:
        List of error message strings.  Empty list means all models pass.
    """
    errors: list[str] = []

    # Identify which models actually need capability resolution
    # (non-mock, with an effort suffix)
    needs_validation: list[tuple[int, str, str]] = []
    for i, full_model in enumerate(models):
        if full_model == "mock" or full_model.startswith(("mock#", "mock:")):
            continue
        base, level = parse_model_reasoning(full_model)
        if level is None:
            continue
        # Ollama models warn but don't need capability checking
        is_ollama = False
        if profile_configs is not None and i < len(profile_configs):
            provider = profile_configs[i].get("provider", "")
            if provider == "ollama":
                is_ollama = True
        if is_ollama:
            logger.warning(
                "Ollama model '%s' has effort level '%s' — effort is ignored "
                "by Ollama and will be dropped silently.",
                full_model,
                level,
            )
            continue
        needs_validation.append((i, base, level))

    if not needs_validation:
        return []

    # Only fetch capabilities if there are models that need checking
    try:
        caps = resolve_capabilities()
    except RuntimeError as exc:
        return [str(exc)]

    reasoning_models = caps["reasoning_models"]
    effort_matrix = caps["effort_matrix"]

    for i, base, level in needs_validation:
        full_model = models[i]

        # Validate the level string itself
        if level not in VALID_REASONING_LEVELS:
            errors.append(
                f"Model '{full_model}': invalid reasoning level '{level}'. "
                f"Valid levels: {', '.join(VALID_REASONING_LEVELS)}."
            )
            continue

        # Check reasoning support: matrix is authoritative (if we shipped it,
        # the model supports reasoning at those levels).  Only consult the API
        # for models NOT in the matrix.
        normalized = _normalize_model(base)
        model_mappings = effort_matrix.get(normalized)
        if model_mappings is not None:
            # Model has verified mappings from an earlier preflight.
            # Skip the API reasoning-support check — we know it works.
            if level not in model_mappings:
                logger.warning(
                    "Model '%s' with effort '%s' has not been verified "
                    "via preflight. The provider may map this to the "
                    "nearest supported level.",
                    base,
                    level,
                )
            continue

        # Not in matrix — check API for reasoning support.
        # Try all likely prefix combinations against the API's model IDs.
        candidates = {base, normalized}
        for prefix in ["openai", "google", "anthropic", "deepseek", "qwen",
                        "mistralai", "x-ai", "nvidia", "minimax", "moonshotai",
                        "z-ai", "arcee-ai", "ibm-granite", "inclusionai",
                        "liquid"]:
            candidates.add(f"{prefix}/{normalized}")
        if not any(c in reasoning_models for c in candidates):
            # API doesn't list this model as reasoning-capable, but the
            # matrix is the authority now (populated by Responses API
            # preflight).  Warn instead of blocking — for 'none' it's
            # harmless, and for other efforts the preflight will
            # determine actual support.
            logger.warning(
                "Model '%s' is not listed as reasoning-capable by the "
                "OpenRouter API. Requested effort '%s' may not be honored. "
                "The effort preflight will verify at runtime.",
                base,
                level,
            )
            continue

    return errors
