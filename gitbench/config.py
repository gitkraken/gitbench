"""Configuration loader for GitBench."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

CONFIG_FILENAMES = ["gitbench.json", ".gitbench.json"]
USER_CONFIG = Path.home() / ".gitbench.json"

def discover_judge_benchmarks(benchmarks: list[str]) -> set[str]:
    """Discover which requested benchmarks require an LLM judge.

    Loads each benchmark's fixtures and returns the set of benchmark
    names that contain at least one fixture with ``scoring.type: llm_judge``.

    Args:
        benchmarks: List of benchmark names to check.

    Returns:
        Set of benchmark names that require a judge.
    """
    from pathlib import Path

    import gitbench
    from gitbench.harness.loader import FixtureLoader

    fixtures_root = Path(gitbench.__file__).parent.parent / "fixtures"
    loader = FixtureLoader()
    judge_benchmarks: set[str] = set()

    for name in benchmarks:
        bench_dir = fixtures_root / name
        if not bench_dir.is_dir():
            continue
        try:
            fixtures = loader.load_dir(str(bench_dir))
        except Exception:
            continue
        for fixture in fixtures:
            if fixture.scoring.get("type") == "llm_judge":
                judge_benchmarks.add(name)
                break

    return judge_benchmarks


def load_project_env(config_path: Path | None = None) -> bool:
    """Load a project .env file without overriding existing environment values."""
    base_dir = config_path.parent if config_path is not None else Path.cwd()
    env_path = base_dir / ".env"
    return load_dotenv(dotenv_path=env_path, override=False)


def find_config() -> Path | None:
    """Find the config file, searching project root then home directory.

    Returns:
        Path to config file, or None if not found.
    """
    for name in CONFIG_FILENAMES:
        candidate = Path.cwd() / name
        if candidate.exists():
            return candidate

    if USER_CONFIG.exists():
        return USER_CONFIG

    return None


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from a JSON file.

    Args:
        config_path: Explicit path to config file. If None, searches for one.

    Returns:
        Parsed config dict, or empty dict if no config found.
    """
    if config_path is None:
        config_path = find_config()

    load_project_env(config_path)

    if config_path is None:
        return {}

    try:
        with open(config_path) as f:
            config = json.load(f)
        logger.info(f"Loaded config from {config_path}")
        return config
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        raise SystemExit(f"Error loading config: {e}")


def load_campaign_defaults(config: dict[str, Any]) -> dict[str, Any]:
    """Return campaign defaults from config, if present.

    Reads a top-level ``campaign`` object and supports ``default_trials`` and
    ``require_campaign_id`` keys.  Unknown keys are ignored.
    """
    campaign_config = config.get("campaign")
    if not isinstance(campaign_config, dict):
        return {}
    defaults: dict[str, Any] = {}
    if "default_trials" in campaign_config:
        defaults["default_trials"] = int(campaign_config["default_trials"])
    if "require_campaign_id" in campaign_config:
        defaults["require_campaign_id"] = bool(campaign_config["require_campaign_id"])
    return defaults


def resolve_profile(config: dict[str, Any], profile_name: str) -> dict[str, Any]:
    """Resolve a named profile to its configuration values.

    Args:
        config: Full config dict.
        profile_name: Name of the profile to resolve.

    Returns:
        Dict with keys: models (list), base_url, api_key, provider.
        'models' is always a list, even for single-model profiles.
        Provider defaults to 'ollama' when base_url contains localhost,
        otherwise 'openai'.

    Raises:
        SystemExit: If profile not found.
    """
    profiles = config.get("models", {})

    if profile_name not in profiles:
        available = list(profiles.keys())
        raise SystemExit(
            f"Profile '{profile_name}' not found in config. "
            f"Available profiles: {available}"
        )

    profile = dict(profiles[profile_name])

    if "api_key" in profile:
        raise SystemExit(
            f"Profile '{profile_name}' contains unsupported field 'api_key'. "
            "Move the secret to .env or your shell environment and set "
            "'api_key_env' to the environment variable name."
        )

    # Normalize models: accept "model" (string or list) or "models" (list), always produce list
    if "models" in profile:
        models = profile.pop("models")
        if isinstance(models, str):
            models = [models]
        profile["models"] = models
    elif "model" in profile:
        model_val = profile.pop("model")
        if isinstance(model_val, list):
            profile["models"] = model_val
        else:
            profile["models"] = [model_val]
    else:
        profile["models"] = []

    api_key_env = profile.pop("api_key_env", None)
    if api_key_env:
        profile["api_key"] = os.environ.get(api_key_env)
        profile["_api_key_env"] = api_key_env

    # Resolve provider: explicit field wins, otherwise infer from base_url
    if "provider" not in profile:
        base_url = profile.get("base_url", "")
        if "localhost" in base_url or "127.0.0.1" in base_url:
            profile["provider"] = "ollama"
        else:
            profile["provider"] = "openai"

    return profile


def load_judge_config(config: dict[str, Any]) -> dict[str, Any] | None:
    """Parse the ``judge`` section from config.

    Args:
        config: Full config dict.

    Returns:
        Dict with key ``profile`` (str), or None if no judge section is present.

    Raises:
        SystemExit: If the judge profile is not found.
    """
    judge = config.get("judge")
    if not judge or not isinstance(judge, dict):
        return None

    profile_name = judge.get("profile")
    if not profile_name:
        return None

    # Validate that the profile exists
    try:
        resolve_profile(config, profile_name)
    except SystemExit:
        raise SystemExit(
            f"Judge profile '{profile_name}' not found in config. "
            f"Available profiles: {list(config.get('models', {}).keys())}"
        )

    return {"profile": profile_name}


def load_result_safety_config(config: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve the optional single-model result-safety profile."""
    if "result_safety" not in config:
        return None

    result_safety = config["result_safety"]
    if not isinstance(result_safety, dict):
        raise SystemExit("Result safety configuration must be an object.")

    profile_name = result_safety.get("profile")
    if not isinstance(profile_name, str) or not profile_name.strip():
        raise SystemExit("Result safety requires a non-empty 'profile' value.")

    try:
        profile = resolve_profile(config, profile_name)
    except SystemExit:
        raise SystemExit(
            f"Result safety profile '{profile_name}' not found in config. "
            f"Available profiles: {list(config.get('models', {}).keys())}"
        )

    models = profile.get("models", [])
    if len(models) != 1:
        raise SystemExit(
            f"Result safety profile '{profile_name}' requires exactly one model; "
            f"found {len(models)}."
        )

    return {
        "profile": profile_name,
        "model": models[0],
        "resolved_profile": profile,
    }


def find_profile_for_model(config: dict[str, Any], model: str) -> dict[str, Any]:
    """Find a profile that matches the given model name.

    Searches profiles for one whose 'models' list contains the given model.
    Supports legacy single-model profiles (normalized to list internally).

    Args:
        config: Full config dict.
        model: Model name to search for (e.g. 'gemma4:26b').

    Returns:
        Resolved profile dict if found, empty dict otherwise.
    """
    profiles = config.get("models", {})

    for profile_name, profile_values in profiles.items():
        # Check both "models" (list) and "model" (string or list)
        models = profile_values.get("models")
        if models is None:
            model_val = profile_values.get("model")
            if isinstance(model_val, list):
                models = model_val
            elif model_val:
                models = [model_val]
            else:
                models = []

        if model in models:
            logger.info(f"Found profile '{profile_name}' for model '{model}'")
            return resolve_profile(config, profile_name)

    return {}
