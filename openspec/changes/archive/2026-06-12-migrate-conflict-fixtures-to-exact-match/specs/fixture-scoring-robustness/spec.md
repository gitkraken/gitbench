## ADDED Requirements

### Requirement: Deterministic scoring for single-answer fixtures
Fixtures whose prompt fully determines a single correct answer (conflict resolutions, filename lists) SHALL use deterministic scoring types (`exact_match`, `unordered_line_set`) rather than character-similarity scoring.

#### Scenario: Wrong conflict resolution fails
- **WHEN** a cherry_pick fixture expects `Hello, Planet!!!` and the model outputs `Hello, Planet!` (incoming change dropped)
- **THEN** the fixture fails, even though character similarity exceeds 0.9

#### Scenario: Correct conflict resolution passes
- **WHEN** the model output equals the expected resolved file content modulo leading/trailing whitespace
- **THEN** the fixture passes with similarity 1.0

#### Scenario: Filename list scored as a set
- **WHEN** a git_grep fixture expects a list of filenames one per line
- **THEN** the answer is scored order-insensitively via `unordered_line_set`

### Requirement: Optional code-fence normalization for exact_match
The `exact_match` scorer SHALL support an opt-in `strip_fences` scoring option that removes a single wrapping markdown code fence before comparison.

#### Scenario: Fenced correct answer passes
- **WHEN** a fixture sets `strip_fences: true` and the model wraps the exact expected content in ```` ``` ```` fences (with or without a language tag)
- **THEN** the fixture passes

#### Scenario: Fenced wrong answer still fails
- **WHEN** a fixture sets `strip_fences: true` and the fenced content does not match the expected value
- **THEN** the fixture fails

#### Scenario: Normalization is opt-in
- **WHEN** a fixture does not set `strip_fences`
- **THEN** exact_match comparison behavior is unchanged from before this change

#### Scenario: Unterminated fence left untouched
- **WHEN** the model output opens a fence but never closes it
- **THEN** the output is compared as-is (no partial stripping)

### Requirement: Multi-line exact_match fixtures declare ordering
Migrated multi-line `exact_match` fixtures SHALL set `scoring.order_matters: true`, satisfying the fixture self-check rule for multi-line exact comparisons.

#### Scenario: Self-check passes on migrated fixtures
- **WHEN** the fixture self-check runs over cherry_pick, merge_conflicts, and rebase after migration
- **THEN** no `multiline-exact-order-review` issues are reported
