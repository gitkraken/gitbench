## Context

The initial run path currently wraps `ModelInterface.generate()` with a request-budget permit. OpenAI-compatible adapters perform retries inside `generate()`, so retries are invisible to `RequestBudgetCoordinator` and retain the permit for the entire retry loop. A 429 therefore delays only the failing adapter instance; other effort variants sharing the same upstream capacity group do not learn that the group is rate-limited.

Timeout resolution also differs by path. Initial OpenAI-compatible runs fall through to the adapter's 30-second default, Ollama defaults to 120 seconds, and doctor has a separate 120-second default. The observed DeepSeek failures exhausted three 30-second attempts even though a longer benchmark-wide default was expected.

The change must cover primary benchmark generation, reasoning preflight requests, and LLM judge requests. Doctor is intentionally excluded.

## Goals / Non-Goals

**Goals:**
- Use a consistent 240-second default timeout for model-generation attempts.
- Coordinate every provider attempt, including retries, through shared capacity-group state.
- Propagate 429 cooldowns across effort variants and fixtures sharing a capacity key.
- Keep unrelated capacity groups running during a cooldown.
- Make retry and cooldown behavior diagnosable from logs and persisted fixture results.

**Non-Goals:**
- Changing doctor execution or repair behavior.
- Implementing provider routing or selecting alternate OpenRouter upstream providers.
- Dynamically learning long-term request rates or replacing request budgets with a token bucket.
- Retrying semantic validation or ordinary scoring failures.

## Decisions

### Decision 1: Gate provider attempts inside adapters

Introduce a small request-attempt gate abstraction owned by the capacity coordinator and injected into each real model adapter with its resolved capacity key. Each adapter acquires the gate immediately before an HTTP attempt and releases it immediately after that attempt returns or raises.

The existing runner-level `generate()` gate will be removed for adapters using the attempt gate. This avoids nested acquisition and ensures backoff and cooldown sleeps do not retain global or group permits.

Alternatives considered:
- Keep runner-level gating and add cooldown checks only around `generate()`. Rejected because adapter retries would still bypass the check.
- Move all retry orchestration into `BenchmarkRunner`. Rejected because provider-specific exception handling and response extraction belong in adapters, and judge/preflight paths would duplicate orchestration.

### Decision 2: Store cooldown deadlines in `RequestBudgetCoordinator`

The coordinator will maintain thread-safe per-capacity-key state containing `blocked_until`. Before acquiring request permits, an attempt waits until the key is unblocked. On HTTP 429, the adapter reports the capacity key and requested delay to the coordinator, which atomically sets:

```text
blocked_until = max(existing_blocked_until, monotonic_now + cooldown + jitter)
```

Cooldown waiting occurs before semaphore acquisition. Multiple waiters recheck the deadline after waking. Existing group concurrency limits and minimum request intervals then control release order and prevent a wake-up burst.

The default fallback cooldown is 30 seconds when `Retry-After` is absent or malformed. Configuration will support `concurrency.rate_limit_cooldown_seconds` as a global fallback and the same field on explicit group entries as an override. `Retry-After` remains the minimum when present. Positive additive jitter of up to 10% of the base delay, capped at one second, is added after the base delay.

Alternatives considered:
- Per-adapter cooldown timestamps. Rejected because effort variants use distinct adapter instances.
- A global OpenRouter cooldown. Rejected because one constrained upstream model should not stop unrelated provider groups.
- Exponential backoff alone. Rejected because it does not communicate saturation to concurrent callers.

### Decision 3: Use one explicit model timeout resolution policy

Define `DEFAULT_MODEL_TIMEOUT = 240` in the model-call layer and make timeout resolution return a concrete value:

```text
CLI override > profile timeout > 240 seconds
```

The same resolved timeout will be passed to primary adapters, reasoning preflight clients, and judge clients. Adapter constructor defaults will also be 240 seconds so direct construction follows the same policy.

Doctor continues using `_effective_doctor_timeout()` and its existing default.

### Decision 4: Separate local retry delay from shared cooldown delay

Timeouts, connection failures, server errors, and malformed provider responses keep local exponential backoff. HTTP 429 establishes a shared group cooldown. A retry may record both small local orchestration overhead and capacity cooldown waiting, but it will not independently sleep for the same `Retry-After` duration after the group cooldown has already enforced it.

This distinction prevents double-waiting and keeps failure scope explicit:

```text
request-local failure -> local backoff
capacity failure      -> shared group cooldown
```

### Decision 5: Carry request telemetry through success and failure

Add a request telemetry value object accumulated by the adapter:

```text
attempts
local_retry_wait_ms
capacity_cooldown_wait_ms
retry_reasons
```

Successful response dictionaries include this object. Exhausted retry exceptions carry the same object so `BenchmarkRunner` can attach it to the failed `Score`. Scores serialize it as `request_telemetry`.

Structured retry logs include model identity, capacity key, attempt number, error category, selected delay, and whether the delay was local or shared. Judge calls use the same adapter logging; fixture score telemetry describes the model-under-test generation call rather than merging multiple judge calls into one ambiguous total.

Alternatives considered:
- Infer retries from `duration_ms`. Rejected because provider latency, backoff, and capacity waiting cannot be separated.
- Persist every retry event. Deferred because aggregate telemetry plus structured logs is sufficient and avoids large result payloads.

## Risks / Trade-offs

- [Risk] A 240-second timeout with three attempts can keep one fixture active for roughly 12 minutes. -> Mitigation: preserve profile and CLI overrides and expose attempts and wait time in telemetry.
- [Risk] Waiting threads may wake together after a cooldown. -> Mitigation: recheck deadlines, acquire normal semaphores after cooldown, preserve minimum intervals, and add bounded jitter.
- [Risk] In-flight requests cannot be stopped when another request establishes a cooldown. -> Mitigation: allow those requests to finish and let any subsequent 429 extend, never shorten, the shared deadline.
- [Risk] Injecting attempt gates changes adapter construction across benchmark, preflight, and judge paths. -> Mitigation: use one optional protocol with a no-op default and add integration tests for every construction path.
- [Risk] New persisted telemetry fields affect result consumers. -> Mitigation: make the field additive and optional so existing readers remain compatible.

## Migration Plan

1. Add the attempt-gate and cooldown state while retaining no-op behavior when no coordinator is supplied.
2. Wire initial run, preflight, and judge adapter construction to the shared coordinator.
3. Move permit acquisition from the runner around `generate()` to adapters around each provider attempt.
4. Change default model timeout resolution to 240 seconds.
5. Add additive request telemetry serialization and update documentation.
6. Roll back by restoring runner-level gating and the prior adapter defaults; existing result files remain readable because telemetry is optional.

## Open Questions

None.
