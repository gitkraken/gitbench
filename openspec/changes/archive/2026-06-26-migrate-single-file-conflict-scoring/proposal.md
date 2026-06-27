## Why

The current scoring-contract cleanup intentionally limits `resolved_file_blocks` migration to multi-file conflict fixtures. Single-file conflict fixtures need a separate calibration pass with stronger evidence, because changing their scorer can alter historical pass/fail outcomes in subtle ways.

## What Changes

- Evaluate whether single-file `merge_conflicts`, `cherry_pick`, and `rebase` fixtures should migrate from exact text scoring to `resolved_file_blocks` or another deterministic scorer.
- Replay stored attempts before and after candidate migrations to identify changed outcomes.
- Manually inspect newly passing outputs for semantic correctness and newly failing outputs for parser or prompt issues.
- Migrate only fixtures whose before/after evidence supports the scoring change.
- Keep campaign reruns out of scope for this proposal unless explicitly requested later.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `fixture-scoring-robustness`: Extend file-aware resolved-content scoring to single-file conflict fixtures when validated by replay evidence.
- `fixture-calibration`: Add a validation bar for scorer migrations that can change stored conflict-fixture outcomes.

## Impact

- Single-file conflict fixtures under `fixtures/merge_conflicts`, `fixtures/cherry_pick`, and `fixtures/rebase`.
- Scorer and parser tests for `resolved_file_blocks`, if migration reveals additional single-file edge cases.
- Stored-attempt replay or local audit tooling used to compare pre/post outcomes.
