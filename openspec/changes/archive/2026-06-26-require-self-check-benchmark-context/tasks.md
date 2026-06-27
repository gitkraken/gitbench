## 1. Caller Inventory

- [x] 1.1 Find all direct and indirect callers of fixture self-check functions.
- [x] 1.2 Classify callers as suite-level benchmark validation or explicit generic fixture-only validation.
- [x] 1.3 Identify any scripts or tests that need migration guidance.

## 2. API Contract

- [x] 2.1 Update self-check APIs so suite-level validation requires `benchmark_name`.
- [x] 2.2 Preserve or clearly mark an explicit generic fixture-only path for callers that intentionally do not use benchmark-local behavior.
- [x] 2.3 Ensure capability lookup no longer falls back to generic scoring behavior for suite-level validation.

## 3. Caller Migration

- [x] 3.1 Update suite-level validation and test callers to pass benchmark context.
- [x] 3.2 Update docs or error messages for callers that need benchmark context.
- [x] 3.3 Remove compatibility paths that were only kept for the initial scorer-capability migration.

## 4. Verification

- [x] 4.1 Add tests that suite-level self-check calls fail or warn when benchmark context is missing.
- [x] 4.2 Add tests that explicit generic fixture-only checks remain possible and clearly labeled.
- [x] 4.3 Run local fixture self-check and related validation tests.
