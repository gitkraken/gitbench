"""Capacity-group derivation and request-budget coordination."""

from __future__ import annotations

import fnmatch
import threading
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from typing import Any, Iterable, Iterator

from gitbench.harness.reasoning import parse_model_reasoning


@dataclass(frozen=True)
class CapacityInfo:
    """Capacity identity for one configured run target."""

    full_model: str
    base_model_id: str
    effort: str | None
    capacity_key: str
    request_limit: int | None


def is_openrouter_profile(profile: dict[str, Any]) -> bool:
    """Return whether a profile targets OpenRouter's OpenAI-compatible API."""
    base_url = str(profile.get("base_url") or "").lower()
    return "openrouter.ai" in base_url


def infer_openrouter_capacity_key(base_model_id: str) -> str:
    """Infer an OpenRouter upstream family capacity key from a base model ID."""
    if base_model_id.startswith("anthropic/claude-opus-"):
        return "openrouter:anthropic/claude-opus"
    if base_model_id.startswith("anthropic/claude-sonnet-"):
        return "openrouter:anthropic/claude-sonnet"
    if base_model_id.startswith("anthropic/claude-haiku-"):
        return "openrouter:anthropic/claude-haiku"
    if (
        base_model_id.startswith("openai/gpt-5.")
        or base_model_id.startswith("openai/gpt-5-")
        or base_model_id == "openai/gpt-5"
    ):
        return "openrouter:openai/gpt-5"
    if base_model_id.startswith("google/gemini-3"):
        return "openrouter:google/gemini-3"
    return f"openrouter:{base_model_id}"


def _positive_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 1:
        return None
    return parsed


def _iter_concurrency_groups(
    config: dict[str, Any],
    profile: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    for group in (config.get("concurrency") or {}).get("groups") or []:
        if isinstance(group, dict):
            yield group
    for group in (profile.get("concurrency") or {}).get("groups") or []:
        if isinstance(group, dict):
            yield group


def _match_explicit_group(
    config: dict[str, Any],
    profile: dict[str, Any],
    base_model_id: str,
) -> tuple[str, int | None] | None:
    for group in _iter_concurrency_groups(config, profile):
        key = group.get("key")
        patterns = group.get("match") or []
        if isinstance(patterns, str):
            patterns = [patterns]
        if not key or not isinstance(patterns, list):
            continue
        if any(fnmatch.fnmatchcase(base_model_id, str(pattern)) for pattern in patterns):
            return str(key), _positive_int(group.get("max_concurrent_requests"))
    return None


def derive_capacity_info(
    config: dict[str, Any],
    profile: dict[str, Any],
    full_model: str,
) -> CapacityInfo:
    """Derive base model, effort, capacity key, and request limit."""
    base_model_id, effort = parse_model_reasoning(full_model)
    explicit = _match_explicit_group(config, profile, base_model_id)
    if explicit is not None:
        capacity_key, request_limit = explicit
    elif is_openrouter_profile(profile):
        capacity_key = infer_openrouter_capacity_key(base_model_id)
        request_limit = None
    else:
        provider = str(profile.get("provider") or "openai")
        capacity_key = f"{provider}:{base_model_id}"
        request_limit = None

    if request_limit is None:
        request_limit = _positive_int(profile.get("max_concurrent_requests"))

    return CapacityInfo(
        full_model=full_model,
        base_model_id=base_model_id,
        effort=effort,
        capacity_key=capacity_key,
        request_limit=request_limit,
    )


def global_request_limit(
    config: dict[str, Any],
    *,
    fallback: int | None = None,
) -> int | None:
    """Return configured global request limit, or fallback when unset."""
    return _positive_int((config.get("concurrency") or {}).get("max_concurrent_requests")) or fallback


def resolve_group_limits(infos: Iterable[CapacityInfo]) -> dict[str, int | None]:
    """Resolve per-capacity-key request limits from configured run targets.

    When multiple targets share a capacity key and no explicit limit was configured,
    default that key to one concurrent request. This automatically serializes
    effort variants of the same configured base model.
    """
    group_limits: dict[str, int | None] = {}
    group_counts: dict[str, int] = {}

    for info in infos:
        group_counts[info.capacity_key] = group_counts.get(info.capacity_key, 0) + 1
        if info.capacity_key not in group_limits:
            group_limits[info.capacity_key] = info.request_limit
        elif info.request_limit is not None:
            existing = group_limits[info.capacity_key]
            group_limits[info.capacity_key] = (
                info.request_limit
                if existing is None
                else min(existing, info.request_limit)
            )

    for key, count in group_counts.items():
        if count > 1 and group_limits.get(key) is None:
            group_limits[key] = 1

    return group_limits


class RequestBudgetCoordinator:
    """Coordinates global and per-capacity-group request semaphores."""

    def __init__(
        self,
        *,
        global_limit: int | None = None,
        group_limits: dict[str, int | None] | None = None,
    ) -> None:
        self.global_limit = global_limit
        self.group_limits = dict(group_limits or {})
        self._global = threading.BoundedSemaphore(global_limit) if global_limit else None
        self._groups: dict[str, threading.BoundedSemaphore] = {}
        self._lock = threading.Lock()

    def _group_semaphore(self, capacity_key: str) -> threading.BoundedSemaphore | None:
        limit = self.group_limits.get(capacity_key)
        if not limit:
            return None
        with self._lock:
            semaphore = self._groups.get(capacity_key)
            if semaphore is None:
                semaphore = threading.BoundedSemaphore(limit)
                self._groups[capacity_key] = semaphore
            return semaphore

    @contextmanager
    def acquire(self, capacity_key: str) -> Iterator[None]:
        """Acquire global then group permits, releasing both on exit."""
        global_context = self._global or nullcontext()
        group = self._group_semaphore(capacity_key)
        group_context = group or nullcontext()
        with global_context:
            with group_context:
                yield


def describe_request_budgets(
    global_limit: int | None,
    group_limits: dict[str, int | None],
) -> str:
    """Format budget settings for run-start logging."""
    global_label = str(global_limit) if global_limit else "unlimited"
    limited_groups = {
        key: value for key, value in sorted(group_limits.items()) if value is not None
    }
    if not limited_groups:
        return f"Request budgets: global={global_label}; groups=unlimited"
    groups_label = ", ".join(f"{key}={value}" for key, value in limited_groups.items())
    return f"Request budgets: global={global_label}; groups={groups_label}"
