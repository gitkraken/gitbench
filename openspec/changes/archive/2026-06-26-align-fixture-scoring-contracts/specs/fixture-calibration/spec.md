## ADDED Requirements

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
