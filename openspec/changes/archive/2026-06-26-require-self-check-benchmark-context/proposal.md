## Why

Fixture self-checks can only be fully scorer-aware when they know the benchmark context that determines effective scoring behavior. The current cleanup keeps benchmark context optional for compatibility; this follow-up makes the API contract stricter after callers have migrated.

## What Changes

- Require suite-level fixture self-check callers to provide `benchmark_name`.
- Remove or deprecate generic-only self-check paths that are too conservative for benchmark-local scorers.
- Update tests and any CLI/audit entry points to pass benchmark context explicitly.
- Keep the capability registry from the scoring-contract cleanup as the source of effective scorer behavior.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `fixture-calibration`: Require benchmark-aware self-check execution for suite-level validation.
- `scorer-capability-metadata`: Treat benchmark context as required for full effective scorer capability resolution.

## Impact

- `gitbench/fixture_self_check.py` public function signature and callers.
- Fixture audit and validation tests.
- Any local scripts or CLI paths that run fixture self-checks directly.
