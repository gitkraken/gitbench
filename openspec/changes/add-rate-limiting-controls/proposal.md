## Why

Benchmark runs hitting OpenRouter frequently encounter 429 (Rate Limit Exceeded) errors, especially when running `--all-models` across many capacity groups simultaneously. The current system fires requests back-to-back with no inter-request pacing and uses a blind exponential backoff that ignores OpenRouter's `Retry-After` headers, leading to wasted retry attempts and prematurely exhausted fixtures.

## What Changes

- Add a configurable inter-request delay (default 500ms) enforced at the capacity-group semaphore level, preventing back-to-back bursts within model families
- Support per-group `min_request_interval_ms` overrides in `concurrency.groups` config for families with stricter upstream rate limits
- Read `Retry-After` headers from 429 responses and use them (bounded by existing exponential backoff minimum) for smarter retry timing in the OpenAI adapter
- No breaking changes — existing configs and behavior are preserved when delay is unset (defaults to 0ms / current behavior)

## Capabilities

### New Capabilities

- `inter-request-delay`: Configurable minimum interval between requests within a capacity group, with per-group override support

### Modified Capabilities

- `capacity-aware-concurrency`: The `RequestBudgetCoordinator` and group semaphore acquire/release lifecycle gains rate-limiting awareness; `concurrency.groups` entries accept a new `min_request_interval_ms` field

## Impact

- `gitbench/harness/capacity.py` — `RequestBudgetCoordinator` semaphores become rate-limited; group config parsing extended
- `gitbench/harness/model.py` — retry logic in `OpenAIAdapter.generate()` reads `Retry-After` headers on 429
- `gitbench/cli.py` — logger message for budget description includes interval info
- `gitbench.json` (user config) — optional new fields: `concurrency.min_request_interval_ms`, `concurrency.groups[].min_request_interval_ms`
- Tests: `tests/test_capacity.py`, `tests/test_model.py`
