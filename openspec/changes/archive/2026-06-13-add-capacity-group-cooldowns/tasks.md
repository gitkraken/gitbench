## 1. Timeout Policy

- [x] 1.1 Define a shared 240-second model-attempt timeout constant and update OpenAI-compatible and Ollama adapter constructor defaults.
- [x] 1.2 Update CLI timeout resolution to use `CLI override > profile timeout > 240 seconds` for initial benchmark runs.
- [x] 1.3 Pass the resolved timeout policy through reasoning preflight and every LLM judge client.
- [x] 1.4 Add unit tests for default, profile, and CLI timeout precedence across primary, preflight, judge, OpenAI-compatible, and Ollama paths.
- [x] 1.5 Preserve the existing doctor timeout resolution and add a regression test proving it is unchanged.

## 2. Capacity Cooldown Coordination

- [x] 2.1 Add thread-safe per-capacity-group cooldown state and attempt-level acquisition APIs to `RequestBudgetCoordinator`.
- [x] 2.2 Parse `concurrency.rate_limit_cooldown_seconds` with a 30-second default and support per-explicit-group overrides.
- [x] 2.3 Implement atomic cooldown extension using the later of the current deadline and the reported deadline.
- [x] 2.4 Add additive cooldown jitter up to 10% capped at one second, with injectable timing/randomness for deterministic tests.
- [x] 2.5 Ensure cooldown waits occur before semaphore acquisition and preserve group concurrency and minimum request intervals after wake-up.
- [x] 2.6 Add concurrency tests for shared effort-variant cooldowns, independent groups, deadline extension, missing `Retry-After`, and wake-up pacing.

## 3. Attempt-Level Adapter Integration

- [x] 3.1 Define an optional request-attempt gate protocol that real model adapters can use without coupling them to CLI or runner types.
- [x] 3.2 Inject the shared coordinator and resolved capacity key into primary benchmark, reasoning preflight, and judge model adapters.
- [x] 3.3 Move global and group permit acquisition from around `generate()` to immediately around each provider network attempt.
- [x] 3.4 Report HTTP 429 delays to the shared capacity group before scheduling a retry and avoid sleeping twice for the same `Retry-After`.
- [x] 3.5 Keep timeout, connection, server, and response errors on local exponential backoff without establishing group cooldowns.
- [x] 3.6 Add adapter and integration tests proving retry attempts reacquire budgets and release permits during local backoff and shared cooldown waits.

## 4. Retry Telemetry

- [x] 4.1 Add a request telemetry value object containing provider attempts, cumulative local retry wait, cumulative capacity cooldown wait, and retry reason counts.
- [x] 4.2 Include request telemetry in successful adapter responses and attach it to exhausted retry exceptions.
- [x] 4.3 Persist optional `request_telemetry` on fixture `Score` records for both successful and failed model-under-test calls.
- [x] 4.4 Emit structured retry logs with model, capacity key, attempt number, retry category, wait type, and wait duration, including judge calls.
- [x] 4.5 Add serialization and failure-path tests showing telemetry survives successful retries, exhausted retries, and result round trips.

## 5. Documentation And Verification

- [x] 5.1 Document the 240-second default, timeout precedence, shared group cooldown behavior, fallback cooldown configuration, and telemetry fields.
- [x] 5.2 Add an end-to-end initial-run test where one effort variant receives 429 and another effort variant waits while an unrelated group proceeds.
- [x] 5.3 Run focused model, capacity, runner, judge, CLI, and result serialization test suites.
- [x] 5.4 Run the full Python test suite and confirm no doctor behavior regressions.
