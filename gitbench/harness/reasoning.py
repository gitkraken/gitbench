"""Reasoning level validation for GitBench models.

Validates that a given model name + reasoning level combination is supported
before any benchmarks are executed. Fails fast with clear error messages to
prevent wasted API calls on invalid configurations.
"""

import click

VALID_REASONING_LEVELS = ["minimal", "low", "medium", "high", "xhigh"]

_MODEL_MATRIX: dict[str, list[str]] = {
    "o3-mini": ["minimal", "low", "medium", "high"],
    "o3": ["minimal", "low", "medium", "high"],
    "o4-mini": ["minimal", "low", "medium", "high", "xhigh"],
    "gpt-4o": ["minimal", "low", "medium", "high", "xhigh"],
    "gpt-4o-mini": ["minimal", "low", "medium", "high"],
    "gpt-4.1": ["minimal", "low", "medium", "high", "xhigh"],
    "gpt-4.1-mini": ["minimal", "low", "medium", "high"],
    "gpt-4.1-nano": ["minimal", "low", "medium", "high"],
    "gpt-5": ["minimal", "low", "medium", "high", "xhigh"],
}


def _normalize_model(base_model: str) -> str:
    """Strip provider prefix (e.g. ``openai/gpt-4o`` → ``gpt-4o``)."""
    if "/" in base_model:
        return base_model.split("/", 1)[1]
    return base_model


def get_supported_levels(model: str) -> list[str] | None:
    """Return the list of supported reasoning levels for *model*, or ``None``.

    Args:
        model: The base model name (without ``#level`` suffix).

    Returns:
        The list of reasoning levels, or ``None`` when the model is
        not in the capability matrix.
    """
    normalized = _normalize_model(model)
    return _MODEL_MATRIX.get(normalized)


def parse_model_reasoning(model_name: str) -> tuple[str, str | None]:
    """Split a model name into base name and optional reasoning level.

    Syntax: ``base_model`` or ``base_model#level``.
    If multiple ``#`` are present, only the last one delimits the level.

    Args:
        model_name: Full model name, optionally with ``#level`` suffix.

    Returns:
        A tuple of ``(base_model, reasoning_level)`` where
        ``reasoning_level`` is ``None`` when no ``#`` is present.
    """
    if "#" in model_name:
        idx = model_name.rfind("#")
        return model_name[:idx], model_name[idx + 1:]
    return model_name, None


def validate_model_list(models: list[str]) -> None:
    """Validate every model in a list has a valid reasoning level combination.

    Called **before** any benchmarks execute so invalid combinations fail fast.
    Models named ``mock`` or prefixed ``mock#`` bypass validation.
    Models not in the capability matrix are allowed through (levels on
    unknown models are silently accepted).

    Args:
        models: List of full model names (may include ``#level`` suffixes).

    Raises:
        click.ClickException: When any model has an invalid reasoning level.

    Returns:
        ``None`` when all models pass validation.
    """
    for full_model in models:
        if full_model == "mock" or full_model.startswith("mock#"):
            continue

        base, level = parse_model_reasoning(full_model)
        if level is None:
            continue

        if level not in VALID_REASONING_LEVELS:
            raise click.ClickException(
                f"Invalid reasoning level '{level}'. "
                f"Valid levels: {', '.join(VALID_REASONING_LEVELS)}."
            )

        supported = get_supported_levels(base)
        if supported is None:
            continue

        if level not in supported:
            raise click.ClickException(
                f"Model '{base}' does not support reasoning level '{level}'. "
                f"Supported levels: {', '.join(supported)}."
            )
