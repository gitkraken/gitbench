"""Tests for capacity-aware request scheduling."""

import threading
import time

from gitbench.harness.benchmark import Benchmark
from gitbench.harness.capacity import (
    RateLimitedBoundedSemaphore,
    RequestBudgetCoordinator,
    CapacityInfo,
    derive_capacity_info,
    global_request_limit,
    resolve_group_intervals,
    resolve_group_limits,
)
from gitbench.harness.runner import BenchmarkRunner
from gitbench.harness.types import Fixture, ModelMessage, Score


class _Cleanup:
    def cleanup(self) -> None:
        pass


class _SlowModel:
    reasoning_level = None

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def generate(self, messages: list[ModelMessage], **kwargs):
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(0.05)
            return {"text": "ok", "usage": None}
        finally:
            with self.lock:
                self.active -= 1


class _FastBenchmark(Benchmark):
    name = "fast"
    description = "fast"

    def load_fixtures(self) -> list[Fixture]:
        return [
            Fixture(
                id=f"f{i}",
                description="fixture",
                setup=[],
                prompt="prompt",
                expected="ok",
                scoring={"type": "exact"},
            )
            for i in range(4)
        ]

    def setup_fixture(self, fixture: Fixture):
        return _Cleanup(), "/tmp"

    def get_diff(self, repo_path: str) -> str:
        return "diff"

    def score(self, fixture: Fixture, model_output: str, repo_path: str | None = None) -> Score:
        return Score(
            fixture_id=fixture.id,
            passed=True,
            similarity=1.0,
            model_output=model_output,
        )


def test_openrouter_anthropic_opus_versions_share_capacity_group():
    config = {}
    profile = {"base_url": "https://openrouter.ai/api/v1"}

    first = derive_capacity_info(config, profile, "anthropic/claude-opus-4.7:max")
    second = derive_capacity_info(config, profile, "anthropic/claude-opus-4.8:max")

    assert first.base_model_id == "anthropic/claude-opus-4.7"
    assert first.effort == "max"
    assert first.capacity_key == "openrouter:anthropic/claude-opus"
    assert second.capacity_key == "openrouter:anthropic/claude-opus"


def test_openrouter_inference_rules_and_fallback():
    profile = {"base_url": "https://openrouter.ai/api/v1"}

    assert (
        derive_capacity_info({}, profile, "anthropic/claude-sonnet-4.7:high").capacity_key
        == "openrouter:anthropic/claude-sonnet"
    )
    assert (
        derive_capacity_info({}, profile, "anthropic/claude-haiku-4.7:low").capacity_key
        == "openrouter:anthropic/claude-haiku"
    )
    assert (
        derive_capacity_info({}, profile, "openai/gpt-5.4-mini:high").capacity_key
        == "openrouter:openai/gpt-5"
    )
    assert (
        derive_capacity_info({}, profile, "google/gemini-3-pro:max").capacity_key
        == "openrouter:google/gemini-3"
    )
    assert (
        derive_capacity_info({}, profile, "mistral/devstral-small").capacity_key
        == "openrouter:mistral/devstral-small"
    )


def test_explicit_group_override_matches_base_model_after_effort_stripping():
    config = {
        "concurrency": {
            "groups": [
                {
                    "key": "openrouter:anthropic/claude",
                    "match": ["anthropic/claude-*"],
                    "max_concurrent_requests": 1,
                }
            ]
        }
    }
    profile = {
        "base_url": "https://openrouter.ai/api/v1",
        "max_concurrent_requests": 3,
    }

    info = derive_capacity_info(config, profile, "anthropic/claude-opus-4.7:max")

    assert info.capacity_key == "openrouter:anthropic/claude"
    assert info.request_limit == 1


def test_profile_request_limit_applies_when_group_has_no_limit():
    profile = {
        "provider": "openai",
        "max_concurrent_requests": 2,
    }

    info = derive_capacity_info({}, profile, "openai/gpt-5.4-mini:max")

    assert info.capacity_key == "openai:openai/gpt-5.4-mini"
    assert info.request_limit == 2


def test_global_request_limit_uses_config_before_fallback():
    assert global_request_limit({"concurrency": {"max_concurrent_requests": 4}}, fallback=8) == 4
    assert global_request_limit({}, fallback=8) == 8


def test_duplicate_capacity_keys_default_to_one_request():
    profile = {"base_url": "https://openrouter.ai/api/v1"}
    infos = [
        derive_capacity_info({}, profile, "minimax/minimax-m2.5:none"),
        derive_capacity_info({}, profile, "minimax/minimax-m2.5:low"),
        derive_capacity_info({}, profile, "minimax/minimax-m2.7:none"),
    ]

    limits = resolve_group_limits(infos)

    assert limits["openrouter:minimax/minimax-m2.5"] == 1
    assert limits["openrouter:minimax/minimax-m2.7"] is None


def test_duplicate_capacity_keys_keep_configured_limit():
    infos = [
        CapacityInfo(
            full_model="minimax/minimax-m2.5:low",
            base_model_id="minimax/minimax-m2.5",
            effort="low",
            capacity_key="openrouter:minimax/minimax-m2.5",
            request_limit=2,
        ),
        CapacityInfo(
            full_model="minimax/minimax-m2.5:high",
            base_model_id="minimax/minimax-m2.5",
            effort="high",
            capacity_key="openrouter:minimax/minimax-m2.5",
            request_limit=2,
        ),
    ]

    limits = resolve_group_limits(infos)

    assert limits["openrouter:minimax/minimax-m2.5"] == 2


def test_runner_gates_parallel_fixture_calls_by_group_budget():
    model = _SlowModel()
    budget = RequestBudgetCoordinator(
        global_limit=4,
        group_limits={"test:group": 1},
    )
    runner = BenchmarkRunner(
        {"fast": _FastBenchmark},
        model,
        request_budget=budget,
        capacity_key="test:group",
    )

    result = runner.run_benchmark("fast", fixture_workers=4)

    assert result.total == 4
    assert model.max_active == 1


# ── RateLimitedBoundedSemaphore ────────────────────────────────────────


def test_rate_limited_semaphore_zero_delay_no_sleep():
    """No delay when min_interval_s is 0."""
    sem = RateLimitedBoundedSemaphore(value=1, min_interval_s=0.0)
    t0 = time.perf_counter()
    sem.acquire()
    sem.release()
    sem.acquire()
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.05  # should be nearly instant


def test_rate_limited_semaphore_enforces_delay():
    """Acquire sleeps when interval has not elapsed."""
    sem = RateLimitedBoundedSemaphore(value=1, min_interval_s=0.2)
    sem.acquire()
    sem.release()
    t0 = time.perf_counter()
    sem.acquire()
    elapsed = time.perf_counter() - t0
    assert elapsed >= 0.18  # allow small timing variance


def test_rate_limited_semaphore_no_delay_when_interval_elapsed():
    """No sleep when enough time has passed since last release."""
    sem = RateLimitedBoundedSemaphore(value=1, min_interval_s=0.1)
    sem.acquire()
    sem.release()
    time.sleep(0.15)  # wait past the interval
    t0 = time.perf_counter()
    sem.acquire()
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.05


def test_rate_limited_semaphore_preserves_concurrency():
    """Concurrent permit limit is still enforced."""
    sem = RateLimitedBoundedSemaphore(value=2, min_interval_s=0.1)
    acquired = [False, False]
    ready = threading.Event()

    def worker(idx: int) -> None:
        sem.acquire()
        acquired[idx] = True
        ready.wait()
        sem.release()

    t1 = threading.Thread(target=worker, args=(0,))
    t2 = threading.Thread(target=worker, args=(1,))
    t1.start()
    t2.start()
    time.sleep(0.1)
    assert all(acquired)
    ready.set()
    t1.join()
    t2.join()


def test_rate_limited_semaphore_context_manager():
    """Supports context manager protocol."""
    sem = RateLimitedBoundedSemaphore(value=1, min_interval_s=0.1)
    with sem:
        pass
    with sem:
        pass


# ── resolve_group_intervals ────────────────────────────────────────────


def test_resolve_intervals_global_default():
    config = {"concurrency": {"min_request_interval_ms": 500}}
    infos = [
        CapacityInfo(
            full_model="openai/gpt-5.4-mini:low",
            base_model_id="openai/gpt-5.4-mini",
            effort="low",
            capacity_key="gpt",
            request_limit=1,
        ),
    ]
    intervals = resolve_group_intervals(config, infos)
    assert intervals == {"gpt": 0.5}


def test_resolve_intervals_per_group_override():
    config = {
        "concurrency": {
            "min_request_interval_ms": 500,
            "groups": [{
                "key": "opus",
                "match": ["anthropic/claude-opus-*"],
                "min_request_interval_ms": 2000,
            }],
        },
    }
    infos = [
        CapacityInfo(
            full_model="anthropic/claude-opus-4.7:max",
            base_model_id="anthropic/claude-opus-4.7",
            effort="max",
            capacity_key="opus",
            request_limit=1,
        ),
    ]
    intervals = resolve_group_intervals(config, infos)
    assert intervals == {"opus": 2.0}


def test_resolve_intervals_explicit_zero_overrides_global():
    """Zero interval in group overrides global default."""
    config = {
        "concurrency": {
            "min_request_interval_ms": 500,
            "groups": [{
                "key": "fast",
                "match": ["*"],
                "min_request_interval_ms": 0,
            }],
        },
    }
    infos = [
        CapacityInfo(
            full_model="test",
            base_model_id="test",
            effort=None,
            capacity_key="fast",
            request_limit=1,
        ),
    ]
    intervals = resolve_group_intervals(config, infos)
    assert intervals == {"fast": 0.0}


def test_resolve_intervals_missing_uses_global():
    config = {"concurrency": {"min_request_interval_ms": 1000}}
    infos = [
        CapacityInfo(
            full_model="test",
            base_model_id="test",
            effort=None,
            capacity_key="unmatched",
            request_limit=1,
        ),
    ]
    intervals = resolve_group_intervals(config, infos)
    assert intervals == {"unmatched": 1.0}


def test_resolve_intervals_no_config_returns_empty():
    config = {}
    infos = [
        CapacityInfo(
            full_model="test",
            base_model_id="test",
            effort=None,
            capacity_key="test",
            request_limit=1,
        ),
    ]
    intervals = resolve_group_intervals(config, infos)
    assert intervals == {}


# ── Integration: delay enforced between sequential fixtures ────────────


class _TimingRecorder:
    """Model that records per-call timestamps."""
    reasoning_level = None

    def __init__(self) -> None:
        self.timestamps: list[float] = []
        self.lock = threading.Lock()

    def generate(self, messages: list[ModelMessage], **kwargs):
        with self.lock:
            self.timestamps.append(time.perf_counter())
        return {"text": "ok", "usage": None}


def test_delay_enforced_between_sequential_fixtures():
    model = _TimingRecorder()
    budget = RequestBudgetCoordinator(
        global_limit=4,
        group_limits={"test:group": 1},
        group_intervals={"test:group": 0.2},
    )
    runner = BenchmarkRunner(
        {"fast": _FastBenchmark},
        model,
        request_budget=budget,
        capacity_key="test:group",
    )

    result = runner.run_benchmark("fast", fixture_workers=1)

    assert result.total == 4
    assert len(model.timestamps) == 4
    # Sequential fixtures: each pair should be separated by at least the interval
    for i in range(1, len(model.timestamps)):
        gap = model.timestamps[i] - model.timestamps[i - 1]
        assert gap >= 0.18, f"Expected gap >= 0.18s between fixtures {i-1} and {i}, got {gap:.3f}s"
