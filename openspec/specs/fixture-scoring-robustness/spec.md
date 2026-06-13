## Purpose

Ensure benchmark fixture scoring is deterministic and robust by matching scoring types to the nature of the answer: exact-match for single-answer fixtures, order-insensitive set comparison for filename lists, command equivalence for CLI answers, and structured-value comparison for JSON outputs. Prevent false positives from character-similarity scoring on fixtures where the correct answer is unambiguous.
## Requirements
### Requirement: Command equivalence scoring
The scoring system SHALL support a `command_equivalence` scoring type that passes when the model output matches any fixture-declared accepted command alternative after command normalization.

#### Scenario: Single accepted command matches
- **WHEN** a fixture uses `command_equivalence` with `accepted` containing `git worktree list`
- **THEN** model output `git worktree list` passes

#### Scenario: Equivalent command alternative matches
- **WHEN** a fixture uses `command_equivalence` with `accepted` containing both `git submodule` and `git submodule status`
- **THEN** model output `git submodule status` passes

#### Scenario: Unaccepted command fails
- **WHEN** a fixture uses `command_equivalence` with `accepted` containing `git submodule` and `git submodule status`
- **THEN** model output `git status` fails

### Requirement: Command normalization
The command equivalence scorer SHALL normalize command lines by trimming whitespace, ignoring blank lines, parsing shell-like tokens, and comparing token sequences instead of raw strings.

#### Scenario: Whitespace differences do not fail
- **WHEN** a fixture accepts `git submodule status`
- **THEN** model output with leading, trailing, or repeated spaces around the same tokens passes

#### Scenario: Quoting differences do not fail
- **WHEN** a fixture accepts `git worktree lock --reason 'do not delete' ../feature-wt`
- **THEN** model output `git worktree lock --reason "do not delete" ../feature-wt` passes

#### Scenario: Invalid command syntax fails with an error
- **WHEN** model output cannot be parsed into command tokens
- **THEN** scoring fails and includes an error explaining that command parsing failed

### Requirement: Multi-command equivalence
The command equivalence scorer SHALL support accepted alternatives that are sequences of command lines, and SHALL compare the normalized model command sequence against each accepted sequence.

#### Scenario: Multi-command sequence matches
- **WHEN** a fixture accepts the sequence `git submodule init` followed by `git submodule update`
- **THEN** model output containing those two commands on separate non-blank lines passes

#### Scenario: Alternative multi-command sequence matches
- **WHEN** a fixture accepts both `git submodule init` followed by `git submodule update` and the single command `git submodule update --init`
- **THEN** model output `git submodule update --init` passes

#### Scenario: Wrong command order fails
- **WHEN** a fixture accepts `git submodule init` followed by `git submodule update`
- **THEN** model output with the same commands in the opposite order fails

### Requirement: Strict selection pass criteria
Selection-style scorers SHALL fail by default when model output includes extra incorrect selections, even if all expected selections are present.

#### Scenario: Exact branch selection passes
- **WHEN** the expected branch selection is `fix-a` and `fix-b`
- **THEN** model output containing exactly `fix-a` and `fix-b` passes

#### Scenario: Extra branch selection fails
- **WHEN** the expected branch selection is `fix-a` and `fix-b`
- **THEN** model output containing `fix-a`, `fix-b`, and `feature-active` fails

#### Scenario: Missing branch selection fails
- **WHEN** the expected branch selection is `fix-a` and `fix-b`
- **THEN** model output containing only `fix-a` fails

### Requirement: Existing scoring compatibility
Existing fixtures that use `similarity`, `exact_match`, `state_assertions`, `structured`, or benchmark-specific scoring types SHALL continue to load and score unless they are explicitly migrated to stricter behavior.

#### Scenario: Existing exact match fixture still scores
- **WHEN** a fixture continues to use `exact_match`
- **THEN** scoring uses the existing exact-match behavior

#### Scenario: Existing state assertion fixture still scores
- **WHEN** a fixture continues to use `state_assertions`
- **THEN** scoring checks the configured expected state assertions after benchmark-specific command execution

### Requirement: Unordered line-set scoring
The scoring system SHALL support an order-insensitive line-set scoring type for fixtures where the correct answer is a set of lines and order is not part of the skill under test.

#### Scenario: Same lines in different order pass
- **WHEN** a fixture expects lines `A` and `B` using unordered line-set scoring
- **THEN** model output containing `B` then `A` passes

#### Scenario: Missing line fails
- **WHEN** a fixture expects lines `A` and `B` using unordered line-set scoring
- **THEN** model output containing only `A` fails

#### Scenario: Extra line fails
- **WHEN** a fixture expects lines `A` and `B` using unordered line-set scoring
- **THEN** model output containing `A`, `B`, and `C` fails unless the fixture explicitly allows extra lines

### Requirement: Numeric exact scoring
The scoring system SHALL support numeric exact scoring for integer/count answers so formatting noise does not cause false failures while incorrect numbers still fail.

#### Scenario: Whitespace around number passes
- **WHEN** a fixture expects numeric answer `7`
- **THEN** model output `  7  ` passes

#### Scenario: Prose containing only one answer number passes
- **WHEN** a fixture expects numeric answer `7`
- **THEN** model output `The answer is 7.` passes if numeric prose normalization is enabled for that fixture

#### Scenario: Different number fails
- **WHEN** a fixture expects numeric answer `7`
- **THEN** model output `6` fails

### Requirement: Dynamic commit-hash scoring
The scoring system SHALL support commit-hash scoring that derives the expected hash from repository state using a stable fixture-declared selector such as commit subject.

#### Scenario: Short hash by subject passes
- **WHEN** a fixture asks for the short hash of the commit with subject `Fix null pointer bug`
- **THEN** scoring derives that commit hash from the fixture repository and passes the matching short hash

#### Scenario: Commit message fails for hash answer
- **WHEN** a fixture asks for a commit hash
- **THEN** model output containing only the commit message fails

#### Scenario: Wrong hash fails
- **WHEN** a fixture asks for the short hash of a selected commit
- **THEN** a short hash for a different commit fails

### Requirement: Semantic structured-value scoring
The scoring system SHALL support semantic scoring for structured values where textual formatting is not the core skill, such as JSON conflict-resolution outputs.

#### Scenario: Equivalent JSON formatting passes
- **WHEN** a fixture expects a JSON object
- **THEN** model output with the same parsed JSON value passes even if whitespace or property order differs

#### Scenario: Invalid JSON fails
- **WHEN** a fixture expects valid JSON
- **THEN** model output that cannot be parsed as JSON fails

#### Scenario: Different JSON value fails
- **WHEN** a fixture expects a JSON object with `version` equal to `2.0.0`
- **THEN** model output with `version` equal to `1.0.0` fails

### Requirement: Conflict-resolution prompts declare policy
Conflict-resolution fixtures SHALL state the intended resolution policy clearly enough that deterministic scoring evaluates the target skill rather than an unstated preference.

#### Scenario: Current-side resolution is explicit
- **WHEN** a conflict fixture expects the current branch value to win
- **THEN** the prompt identifies that policy rather than relying on ambiguous branch labels

#### Scenario: Combined resolution is explicit
- **WHEN** a conflict fixture expects preserving changes from both sides
- **THEN** the prompt describes that combined-resolution policy and scoring validates the combined output

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

