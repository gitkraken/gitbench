## Context

GitBench's `RequestBudgetCoordinator` currently gates concurrency via `BoundedSemaphore` — once a permit is released, the next waiter acquires it instantly. This means fixtures within the same capacity group fire back-to-back with zero inter-request gap. On OpenRouter (where 8+ capacity groups may run in parallel), this creates burst patterns that trigger 429 rate-limit responses.

Separately, the retry logic in `OpenAIAdapter.generate()` uses a fixed exponential backoff (`2^(attempt-1)` seconds, capped at 16s) for `RateLimitError`. It does not inspect the HTTP `Retry-After` header that OpenRouter returns with 429 responses, which often specifies a wait longer than the current backoff, causing retries to fail unnecessarily.

## Goals / Non-Goals

**Goals:**
- Add a configurable minimum interval between consecutive requests within a capacity group
- Support per-group overrides for families with stricter upstream rate limits
- Read `Retry-After` headers from 429 responses and use them as a floor for retry delay
- Preserve deterministic output ordering (already guaranteed by existing capacity-aware concurrency)
- Zero config change required — default `min_request_interval_ms=0` preserves current behavior

**Non-Goals:**
- Global inter-request delay (cross-group pacing)
- Token-bucket or leaky-bucket rate limiter
- OpenRouter provider preference routing
- Dynamic rate adjustment based on observed 429 frequency
- Retry-after support for Ollama adapter (Ollama doesn't return 429 with Retry-After)

## Decisions

### Decision 1: Rate limit at semaphore acquire, not in runner loop

**Chosen**: Wrap the internal `BoundedSemaphore` with a rate-limited variant that sleeps on `acquire()` if called too soon after the previous `release()`.

**Rationale**: The `RequestBudgetCoordinator.acquire()` context manager is the single choke point for all model calls. Rate-limiting there affects every path (sequential fixtures, parallel fixtures, doctor reruns) without changes to runner or CLI code.

**Alternatives considered**:
- Sleep in `_run_fixtures_sequential` loop → would miss parallel paths and `doctor`
- Sleep in `_run_fixture` after response → would block the thread, wasting concurrency slots
- Global timer in coordinator → couples group behavior unnecessarily

### Decision 2: Separate `RateLimitedBoundedSemaphore` wrapper class

**Chosen**: Introduce a thin wrapper that tracks `_last_release` time and sleeps on `acquire()` when `time_since_release < min_interval`. Both global and group semaphores use this wrapper (but global `min_interval` defaults to 0).

**Rationale**: Clean separation from budget logic. The coordinator doesn't need to know about timing; it just gets a semaphore that may have a rate limit built in. Easy to test in isolation.

### Decision 3: Configuration in `concurrency` block

**Chosen**: 
```json
{
  "concurrency": {
    "min_request_interval_ms": 500,
    "groups": [{
      "key": "openrouter:anthropic/claude-opus",
      "match": ["anthropic/claude-opus-*"],
      "min_request_interval_ms": 2000
    }]
  }
}
```

**Rationale**: The `concurrency` block already holds all request-gating config. Adding `min_request_interval_ms` alongside `max_concurrent_requests` keeps related settings together. The global default applies to all groups; per-group overrides it.

### Decision 4: Retry-After as a floor, not a replacement

**Chosen**: `delay = max(exponential_backoff, retry_after_value)`

**Rationale**: Retry-After values could be very small (1-2 seconds) or missing. The exponential backoff provides a sensible floor for non-429 errors (timeouts, connection errors). Using `max()` ensures we never wait less than OpenRouter requests, but also never less than our own backoff for other error types.

### Decision 5: Extract Retry-After from OpenAI exception response

**Chosen**: Attempt `e.response.headers.get("Retry-After")` from the `openai.RateLimitError` exception. If missing or unparseable, fall back to 0 (using only exponential backoff).

**Rationale**: The OpenAI Python client exposes the underlying `httpx.Response` on `RateLimitError.response`. The `Retry-After` header is standard HTTP. Graceful fallback means no regression if the header is absent.

## Risks / Trade-offs

- **Risk**: 500ms default may still allow cross-group bursts that trigger OpenRouter global rate limits → **Mitigation**: Users can increase `min_request_interval_ms` globally or per-group, or lower `--model-workers` to reduce concurrency
- **Risk**: Rate-limited semaphore adds a tiny sleep to every fixture, slightly increasing total runtime → **Mitigation**: 500ms per fixture is ~10 seconds overhead for a 20-fixture benchmark (typically 60-100s total); negligible compared to variance in model latency
- **Risk**: `Retry-After` may specify very long waits (60s+) causing fixture timeouts → **Mitigation**: The existing `timeout` parameter still governs the overall attempt window; if `Retry-After` exceeds timeout, the attempt fails naturally
