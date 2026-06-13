## Why

Initial benchmark runs still produce avoidable transient failures: OpenAI-compatible calls silently default to 30-second attempts, and repeated 429 retries occur inside a model adapter without informing other work in the same capacity group. This allows effort variants sharing one upstream model to continue retrying against a known rate limit instead of cooling down together.

## What Changes

- Establish a 240-second default timeout for all model API attempts unless a profile or CLI override is provided.
- Add shared cooldown state per capacity group so a 429 pauses new requests and retries for that group while unrelated groups continue.
- Apply capacity-group gating to every network attempt, including attempts made by adapter retry loops and LLM judge clients.
- Use `Retry-After` when available and a configurable or documented fallback cooldown when it is absent, with jitter to avoid synchronized retries.
- Record retry and cooldown telemetry sufficient to explain exhausted requests in logs and persisted fixture results.
- Leave `gitbench doctor` behavior unchanged.

## Capabilities

### New Capabilities
- `model-call-reliability`: Defines default model-attempt timeouts and observable retry/cooldown behavior for initial benchmark and judge calls.

### Modified Capabilities
- `capacity-aware-concurrency`: Extends capacity-group request gating with shared cooldown state that is enforced for every network attempt, including retries.

## Impact

- Model adapters and retry handling in `gitbench/harness/model.py`.
- Capacity coordination in `gitbench/harness/capacity.py`.
- Runner and judge client construction in `gitbench/harness/runner.py`, `gitbench/harness/judge.py`, and `gitbench/cli.py`.
- Result score serialization and run logging for retry/cooldown telemetry.
- Unit and integration tests for timeout resolution, effort-variant coordination, retry gating, cooldown isolation, and telemetry.
- No changes to doctor planning, execution, or result-repair semantics.
