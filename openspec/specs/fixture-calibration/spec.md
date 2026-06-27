## Purpose

Fixture calibration corrects known brittle or ambiguous test fixtures to ensure reliable and fair benchmark comparisons.

## Requirements

### Requirement: Known brittle fixtures are corrected
Fixtures with known incorrect, ambiguous, or brittle expectations SHALL be corrected so valid answers pass, objectively wrong expectations are removed, and the repository state identifies one deterministic expected answer.

#### Scenario: Submodule list accepts status form
- **WHEN** the submodule listing fixture asks for the command to list configured submodules
- **THEN** both `git submodule` and `git submodule status` are accepted as correct

#### Scenario: Full hash fixture expects a hash
- **WHEN** the `git_show/f008` fixture asks for the full SHA hash of the commit with message `Second commit`
- **THEN** the fixture no longer expects the literal text `Second commit`

#### Scenario: Broken import has one introducing commit
- **WHEN** `blame_forensics/f010` asks which commit introduced an import from the nonexistent `helpers` module
- **THEN** exactly one commit SHALL introduce the broken import and the current broken line SHALL blame to `Update import path`

#### Scenario: Later formatter commits do not duplicate the defect
- **WHEN** later commits in `blame_forensics/f010` add or modify a formatter import
- **THEN** those commits SHALL use an existing module and SHALL preserve blame for the broken helper import on `Update import path`

### Requirement: Fixture audit covers every suite
The calibration work SHALL audit every benchmark suite for brittle exact matches, loose similarity thresholds, incorrect expected values, and difficulty labels that do not match fixture complexity.

#### Scenario: All suites are included in audit
- **WHEN** calibration tasks are complete
- **THEN** each of the 17 benchmark suites has been reviewed for scoring robustness and difficulty calibration

#### Scenario: Audit findings are acted on
- **WHEN** a fixture is found to reject valid equivalent answers
- **THEN** the fixture is migrated to a more appropriate scorer or corrected accepted alternatives

#### Scenario: Incorrect expectation is fixed
- **WHEN** a fixture expected value conflicts with the prompt's requested answer
- **THEN** the expected value or scoring method is corrected

### Requirement: Overly permissive conflict scoring is strengthened
Conflict-resolution fixtures SHALL avoid passing incomplete resolutions solely because a returned string is similar to one expected file.

#### Scenario: Multi-file conflict fixture validates relevant files
- **WHEN** a conflict fixture describes required resolutions across multiple files
- **THEN** scoring validates the required resolved content for each relevant file or explicitly scopes the fixture to one file

#### Scenario: Loose similarity threshold is replaced or justified
- **WHEN** a conflict fixture uses broad text similarity scoring
- **THEN** the fixture is either migrated to structured/file-aware scoring or documented as intentionally similarity-based

### Requirement: Saturated suites receive harder coverage
Suites with saturated or near-saturated stored pass rates SHALL be reviewed for harder variants or stronger assertions that test deeper Git reasoning.

#### Scenario: Saturated suite is strengthened
- **WHEN** a suite has recent stored results showing all or nearly all fixtures passing across multiple profiles
- **THEN** the suite gains harder fixture coverage or stricter scoring where appropriate

#### Scenario: Harder fixture remains domain-relevant
- **WHEN** a harder fixture is added
- **THEN** it tests the same benchmark capability rather than introducing unrelated Git behavior

### Requirement: Fixture authoring guidance is updated
Project documentation SHALL explain when to use command equivalence, state assertions, strict selection scoring, and similarity scoring.

#### Scenario: Command fixture guidance exists
- **WHEN** a contributor writes a fixture that asks for a Git command
- **THEN** documentation explains when to use `command_equivalence` and how to declare accepted alternatives

#### Scenario: Selection fixture guidance exists
- **WHEN** a contributor writes a fixture that asks for branches, commits, files, or stash refs to select
- **THEN** documentation explains that extra incorrect selections should fail unless partial credit is explicitly intended

### Requirement: Current zero-pass fixture defects are corrected
Fixtures with current stored zero-pass results that are caused by incorrect expectations, order-sensitive valid answers, or setup mismatches SHALL be corrected before they are treated as hard benchmark coverage.

#### Scenario: Order-insensitive log message lists pass
- **WHEN** a git-log fixture asks for all matching commit messages without requiring chronological or reverse-chronological order
- **THEN** the fixture accepts the correct set of messages in either order and rejects missing or extra messages

#### Scenario: Dynamic short hash fixture derives expected value
- **WHEN** a git-log fixture asks for the short hash of the commit with a known subject
- **THEN** scoring derives the expected hash from the fixture repository instead of comparing against a static commit message

#### Scenario: Merge-count setup creates merge commits
- **WHEN** a fixture expects `git log --merges` to count merge commits
- **THEN** the fixture setup creates non-fast-forward merge commits or the expected count is corrected to match the actual repository

### Requirement: Low-pass fixture audit is data-driven
Fixture calibration SHALL prioritize stored zero-pass and low-pass fixtures using current result data, grouped by benchmark, fixture, scoring type, and representative model outputs.

#### Scenario: Low-pass fixtures are ranked before audit
- **WHEN** calibration work begins
- **THEN** fixtures are ranked by observed pass rate and the audit starts with zero-pass fixtures followed by low-pass fixtures

#### Scenario: Suspicious exact-match counts are verified
- **WHEN** an exact-match counting fixture has very low pass rate and most failed outputs agree on a different number
- **THEN** the expected value is verified against the actual command output before changing prompts or difficulty

#### Scenario: Fixture bugs are separated from model weakness
- **WHEN** a low-pass fixture is reviewed
- **THEN** the audit records whether the primary issue is fixture setup, expected value, scoring brittleness, prompt ambiguity, or genuine task difficulty

### Requirement: Fixture self-checks validate expected answers
The calibration workflow SHALL include automated fixture self-checks that execute fixture setup and verify expected answers against generated repository state where the expected value is objectively derivable.

#### Scenario: Static expected hash is flagged
- **WHEN** a fixture asks for a commit hash but stores a non-hash expected value
- **THEN** the self-check flags the fixture before a benchmark run is accepted

#### Scenario: Multi-line exact match is flagged for order review
- **WHEN** a fixture uses exact match with multiple output lines
- **THEN** the self-check flags it unless the fixture explicitly documents that order is part of the requirement

#### Scenario: Git command-derived expected answer is checked
- **WHEN** a fixture has an expected answer that can be derived by running a Git command against the setup repository
- **THEN** the self-check compares the fixture expectation to the derived value and reports mismatches

### Requirement: Difficulty labels are recalibrated after corrections
Difficulty labels SHALL be reviewed after fixture and scoring corrections using observed pass rates and manual domain judgment.

#### Scenario: Difficulty review happens after defect fixes
- **WHEN** zero-pass and low-pass fixture defects have been corrected
- **THEN** difficulty labels are recalibrated from corrected fixture behavior rather than from known-broken historical results

#### Scenario: Observed pass-rate bands inform labels
- **WHEN** a fixture has enough stored results after correction
- **THEN** the difficulty review uses observed pass-rate bands as input while allowing documented manual overrides

#### Scenario: Suite version changes for comparability
- **WHEN** fixture expectations, prompts, or scoring rules are changed in a way that affects pass/fail outcomes
- **THEN** the benchmark suite version is bumped so new results are not treated as directly comparable to old results

### Requirement: Current fixture contract mismatches are corrected
The agreed fixture prompt/scorer mismatches SHALL be corrected before campaign results are used as model-quality signal.

#### Scenario: Date-range filtering is order-insensitive
- **WHEN** `git_log_format/f005` asks for commits between 2025-02-01 and 2025-03-31
- **THEN** the fixture accepts the set `February commit` and `March commit` in either order

#### Scenario: Submodule add commit does not require unstated message
- **WHEN** `submodule_usage/f005` asks the model to add and commit a submodule
- **THEN** scoring validates the submodule addition and committed final state without requiring a specific commit message

#### Scenario: Multi-file conflict f010 scores resolved file contents
- **WHEN** `merge_conflicts/f010`, `cherry_pick/f010`, or `rebase/f010` receives correct content for both `main.py` and `utils.py`
- **THEN** formatting differences in file headings or per-file fences do not cause failure

#### Scenario: Multi-file conflict f012 scores both files
- **WHEN** an `f012` conflict fixture describes required resolutions for `app.py` and `requirements.txt`
- **THEN** the prompt asks for both files and scoring validates both files

### Requirement: Ambiguous single-file conflict policy is clarified
Single-file conflict fixtures that remain on exact scoring SHALL state the intended resolution policy rather than relying on vague preference language.

#### Scenario: Most useful changes is replaced
- **WHEN** a conflict fixture expects one side or combination of a function-body conflict
- **THEN** the prompt identifies the intended policy explicitly instead of saying only `most useful changes`

#### Scenario: Scorer migration is deferred
- **WHEN** the single-file `f005` conflict prompts are clarified in this change
- **THEN** they remain on their existing single-file scorer until a separate validated migration proposal

### Requirement: Commit squash output contract is standardized
All `commit_squash` fixtures SHALL ask for selected commit subject lines and store expected values in that shape.

#### Scenario: Prompt asks for subject lines
- **WHEN** a `commit_squash` fixture asks the model to identify commits to squash
- **THEN** the prompt requests selected commit subject lines, one per line

#### Scenario: Expected values match prompt shape
- **WHEN** a `commit_squash` fixture expects multiple selected commits
- **THEN** `expected` stores the selected subject lines newline-separated

### Requirement: Local validation covers changed fixture contracts
Implementation SHALL validate the changed scorer and fixture contracts with local tests.

#### Scenario: Local tests run
- **WHEN** implementation is complete
- **THEN** local tests cover scorer behavior, fixture self-check behavior, command normalization, structured-output schema behavior, and affected benchmark expected-answer paths

#### Scenario: Campaign run is not required
- **WHEN** implementation is complete
- **THEN** no campaign rerun is required as part of this change

### Requirement: Historical assessment remains unchanged
The historical fixture assessment document SHALL remain unchanged by this proposal.

#### Scenario: Assessment is referenced as stale evidence
- **WHEN** the change references `docs/benchmark-fixture-assessment.md`
- **THEN** it treats the file as stale source evidence and not as current authoritative analysis

### Requirement: Single-file conflict calibration uses replay evidence
Single-file conflict calibration SHALL separate scorer brittleness from genuine task difficulty using local replay and manual review.

#### Scenario: Replay precedes calibration decision
- **WHEN** a single-file conflict fixture is considered for scorer migration
- **THEN** local replay of stored attempts is performed before changing the fixture

#### Scenario: Campaign rerun is not required
- **WHEN** migration decisions are made under this proposal
- **THEN** a full campaign rerun is not required as part of implementation

### Requirement: Suite-level self-check requires benchmark context
Fixture self-check execution for suite-level validation SHALL provide benchmark context so effective scorer behavior can be resolved accurately.

#### Scenario: Suite validation passes benchmark name
- **WHEN** validation iterates fixtures for a benchmark
- **THEN** it calls self-check with the benchmark name for each fixture

#### Scenario: Missing benchmark context is rejected or deprecated
- **WHEN** a suite-level caller invokes self-check without benchmark context
- **THEN** the system rejects the call or emits a deprecation warning according to the migration phase

#### Scenario: Generic fixture-only check remains explicit
- **WHEN** a caller intentionally performs a generic fixture-only check
- **THEN** the call path clearly identifies that benchmark-local scorer behavior is not represented
