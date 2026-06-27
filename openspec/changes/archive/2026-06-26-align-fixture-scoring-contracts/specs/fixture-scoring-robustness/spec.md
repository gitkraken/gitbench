## ADDED Requirements

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
