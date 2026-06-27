## 1. Candidate Inventory

- [x] 1.1 List single-file conflict fixtures in `merge_conflicts`, `cherry_pick`, and `rebase` that could use file-aware scoring.
- [x] 1.2 Record current prompt shape, expected answer, scorer config, and whether the prompt names a filename explicitly.
- [x] 1.3 Identify any fixtures that should remain on exact scoring without replay because no file-block contract is present.

## 2. Replay Harness

- [x] 2.1 Build or reuse a local stored-attempt replay path for candidate fixture scoring.
- [x] 2.2 Capture before/after outcomes for each candidate scorer migration.
- [x] 2.3 Verify expected answers pass before and after each candidate migration.

## 3. Manual Review

- [x] 3.1 Inspect all newly passing stored outputs for semantic correctness.
- [x] 3.2 Inspect newly failing stored outputs to distinguish intended strictness from parser or prompt defects.
- [x] 3.3 Record a migration decision for each candidate fixture with the replay summary.

## 4. Fixture Migration

- [x] 4.1 Migrate only fixtures whose replay and manual inspection support file-aware scoring.
- [x] 4.2 Add or update tests for any parser edge cases discovered during replay.
- [x] 4.3 Document non-migrated fixtures and the reason they remain unchanged.

## 5. Local Verification

- [x] 5.1 Run local scorer and benchmark tests covering migrated fixtures.
- [x] 5.2 Run expected-answer checks for migrated fixtures.
- [x] 5.3 Confirm no full campaign run is required for this follow-up.
