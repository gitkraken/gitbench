## Context

The scoring-contract cleanup keeps `benchmark_name` optional for self-check compatibility while adding effective scorer capabilities. This follow-up tightens the contract after callers have had a migration window.

## Goals / Non-Goals

**Goals:**
- Require benchmark context for suite-level fixture self-checks.
- Remove ambiguity between generic scoring type behavior and benchmark-local effective behavior.
- Keep capability metadata as the source of scorer behavior.

**Non-Goals:**
- Redesigning scorer implementations.
- Adding new fixture calibration rules beyond context enforcement.
- Changing campaign scoring behavior.

## Decisions

### Decision 1: Make benchmark context explicit at self-check boundaries

Suite-level validation should pass `benchmark_name` to self-check APIs. Direct fixture-only calls should be deprecated or constrained to explicitly generic checks.

### Decision 2: Keep capability metadata separate from self-check rules

Self-check should ask capability questions, not hardcode benchmark exceptions.

## Risks / Trade-offs

- Existing scripts may call `check_fixture(fixture)` directly -> provide a deprecation window or clear migration error.
- Tests may need updates across multiple validation paths -> keep changes mechanical and covered by local tests.
