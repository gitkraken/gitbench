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

### Requirement: Strict command answer wrapper normalization
Command-answer scoring and execution SHALL tolerate one whole-answer markdown code fence while rejecting prose extraction.

#### Scenario: Whole-answer fenced command passes normalization
- **WHEN** model output is a complete fenced code block containing `git submodule status`
- **THEN** command normalization returns `git submodule status`

#### Scenario: Prose around fenced command is rejected
- **WHEN** model output says `Run this:` before a fenced command block
- **THEN** command normalization does not extract the command as a valid answer

#### Scenario: Stateful command benchmarks use shared normalization
- **WHEN** `git_clean`, `tag_management`, `worktree_usage`, or `submodule_usage` executes model command output
- **THEN** the benchmark executes normalized command lines from the shared helper

#### Scenario: Command equivalence uses shared normalization
- **WHEN** `command_equivalence` scores a fenced command answer
- **THEN** it compares the normalized command sequence to accepted alternatives

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

#### Scenario: Resolved file-block migration is opt-in
- **WHEN** a conflict fixture remains on `exact_match`
- **THEN** it does not use `resolved_file_blocks` behavior

### Requirement: Resolved file-block scoring
The scoring system SHALL support a `resolved_file_blocks` scoring type for answers that contain resolved content for one or more named files.

#### Scenario: Correct files pass regardless of order
- **WHEN** a fixture expects `main.py` and `utils.py` using `resolved_file_blocks`
- **THEN** model output containing correct blocks for both files passes even if `utils.py` appears before `main.py`

#### Scenario: Heading punctuation differences pass
- **WHEN** a model labels an expected file block with `main.py`, `main.py:`, `--- main.py`, `### main.py`, or `` `main.py` ``
- **THEN** the scorer recognizes the heading as the same file

#### Scenario: Per-file fences pass
- **WHEN** a model wraps the content for each file in a markdown code fence with or without a language tag
- **THEN** the scorer compares the fenced content to the expected file content

#### Scenario: Missing file fails
- **WHEN** a fixture expects `main.py` and `utils.py`
- **THEN** model output containing only `main.py` fails

#### Scenario: Extra file fails by default
- **WHEN** a fixture expects only `main.py` and `utils.py`
- **THEN** model output containing an additional `README.md` file block fails

#### Scenario: Extra file can be allowed explicitly
- **WHEN** a fixture sets `allow_extra_files: true`
- **THEN** extra file blocks do not fail the answer if all expected file contents match

#### Scenario: Content comparison preserves meaningful structure
- **WHEN** model output differs only by line endings, trailing spaces, or final newline
- **THEN** the file content comparison passes
- **AND** changed indentation or removed interior blank lines still fail

### Requirement: File-block expectations are explicit
Fixtures using `resolved_file_blocks` SHALL declare expected file contents in `scoring.expected_files`.

#### Scenario: Explicit expected files score
- **WHEN** a fixture declares `scoring.expected_files.main.py` and `scoring.expected_files.utils.py`
- **THEN** the scorer uses those values as the correctness oracle

#### Scenario: Missing expected files fail closed
- **WHEN** a fixture uses `resolved_file_blocks` without valid `expected_files`
- **THEN** scoring fails with a configuration error

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

### Requirement: Runner honors benchmark-specific evaluation
The benchmark runner SHALL evaluate every non-`llm_judge` fixture through the selected benchmark's scoring hook. Benchmark-specific scoring types and benchmark-specific command execution SHALL occur before the final score is recorded.

#### Scenario: Custom selection scorer runs through the runner
- **WHEN** a `commit_squash` fixture declares `scoring.type: commit_selection` and the model identifies the expected commits
- **THEN** the runner SHALL use the benchmark's commit-selection scorer
- **AND** it SHALL NOT report the scoring type as unsupported

#### Scenario: Recovery scorer runs through the runner
- **WHEN** a `reflog` or `stash_recovery` fixture receives the expected recovery reference
- **THEN** the benchmark-specific recovery scorer SHALL determine the result

#### Scenario: Stateful commands execute before assertions
- **WHEN** a stateful fixture receives model commands that produce the expected repository state
- **THEN** the benchmark SHALL execute the commands in the fixture repository before state assertions run
- **AND** the fixture SHALL pass when all assertions succeed

### Requirement: Parallel fixture lifecycles are isolated
The runner SHALL NOT share mutable benchmark lifecycle state between concurrently executing fixtures.

#### Scenario: Worktree fixtures run with parallel workers
- **WHEN** multiple `worktree_usage` fixtures are scheduled concurrently
- **THEN** each fixture SHALL use an isolated benchmark lifecycle and executor reference
- **AND** cleanup for one fixture SHALL NOT target another fixture's worktrees

### Requirement: Benchmark setup overrides remain contract-compatible
Every benchmark setup override SHALL accept the deterministic fixture-generation context defined by the base benchmark contract and SHALL apply it to repository generation.

#### Scenario: Deterministic worktree fixture setup
- **WHEN** a campaign plans or executes a `worktree_usage` fixture with a fixture-generation context
- **THEN** setup SHALL complete without a signature error
- **AND** generated Git identities SHALL use that context

### Requirement: Commit selection uses deterministic subject lines
The `commit_squash` benchmark SHALL request and score selected commit subject lines as its deterministic output contract.

#### Scenario: Subject lines pass
- **WHEN** a `commit_squash` fixture expects `WIP: add main.py` and `WIP: continue work`
- **THEN** model output containing those subject lines passes

#### Scenario: Bullet markers are tolerated
- **WHEN** model output prefixes each expected subject line with `- `
- **THEN** commit selection scoring still passes

#### Scenario: Hash-only answer fails
- **WHEN** model output contains only the hashes of the expected commits
- **THEN** commit selection scoring fails because the prompt asks for subject lines

#### Scenario: Extra selected subject fails
- **WHEN** model output includes all expected subject lines plus `Initial commit`
- **THEN** commit selection scoring fails with an extra-selection error

#### Scenario: Legacy comma-separated subjects are tolerated
- **WHEN** model output contains expected commit subjects separated by commas
- **THEN** commit selection scoring may pass during the compatibility window

### Requirement: Single-file conflict scorer migrations are evidence-gated
Single-file conflict fixtures SHALL migrate to file-aware resolved-content scoring only after local replay evidence shows the migration preserves semantic correctness.

#### Scenario: Expected answer passes before migration
- **WHEN** a candidate single-file conflict fixture is evaluated with its expected answer
- **THEN** the expected answer passes both before and after the candidate scoring change

#### Scenario: Newly passing stored outputs are inspected
- **WHEN** stored-attempt replay shows outputs that newly pass after scorer migration
- **THEN** those outputs are manually inspected for semantic correctness before the migration is accepted

#### Scenario: Newly failing stored outputs are reviewed
- **WHEN** stored-attempt replay shows outputs that newly fail after scorer migration
- **THEN** those outputs are reviewed to determine whether the stricter failure is intentional or caused by parser/prompt mismatch

### Requirement: Single-file conflict migration decisions are documented
Each candidate single-file conflict fixture SHALL have a recorded migration decision.

#### Scenario: Fixture is migrated
- **WHEN** evidence supports migrating a fixture to file-aware scoring
- **THEN** the implementation records the fixture, reason, and replay outcome summary

#### Scenario: Fixture remains unchanged
- **WHEN** evidence does not support migration
- **THEN** the implementation records why the fixture remains on its existing scorer
