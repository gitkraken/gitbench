## ADDED Requirements

### Requirement: Fixture YAML supports optional metadata fields
Fixture YAML files SHALL support three new optional top-level fields: `purpose`, `difficulty`, and `tags`. All three fields are optional — a fixture without them MUST load without error.

- `purpose` (string): A 1-3 sentence description of what Git skill this fixture tests and why it matters for evaluating model competency.
- `difficulty` (string, enum): One of `trivial`, `easy`, `medium`, `hard`, or `expert`, representing the relative difficulty of this fixture.
- `tags` (list of strings): Searchable keywords that describe the fixture's domain, operations, or concepts (e.g., `["conflict-resolution", "rebase"]`).

#### Scenario: Fixture with all metadata fields loads successfully
- **WHEN** a fixture YAML file contains `purpose`, `difficulty`, and `tags` fields
- **THEN** the `FixtureLoader` parses all three fields and stores them on the `Fixture` object

#### Scenario: Fixture without metadata fields loads successfully
- **WHEN** a fixture YAML file does not contain `purpose`, `difficulty`, or `tags`
- **THEN** the `FixtureLoader` loads the fixture without error and sets the metadata fields to their defaults (`""`, `""`, `[]`)

#### Scenario: Fixture with invalid difficulty value
- **WHEN** a fixture YAML file has `difficulty` set to a value not in the enum (`trivial`, `easy`, `medium`, `hard`, `expert`)
- **THEN** the `FixtureLoader` emits a warning and treats the difficulty as an empty string

### Requirement: Fixture dataclass stores metadata fields
The `Fixture` dataclass SHALL have three new optional fields: `purpose: str`, `difficulty: str`, and `tags: list[str]`. Their default values SHALL be empty string, empty string, and empty list respectively.

#### Scenario: Fixture object created with metadata
- **WHEN** a `Fixture` is instantiated with `purpose="Tests basic rebase conflict resolution"`, `difficulty="medium"`, `tags=["rebase", "conflict"]`
- **THEN** all three fields are accessible on the object

#### Scenario: Fixture object created without metadata
- **WHEN** a `Fixture` is instantiated without `purpose`, `difficulty`, or `tags`
- **THEN** the fields default to `""`, `""`, and `[]`

### Requirement: Fixture metadata appears in JSON results output
The JSON results output SHALL include fixture metadata alongside scores so consumers can interpret results. Each score entry in the JSON output SHALL include `purpose`, `difficulty`, and `tags` fields when the fixture has them.

#### Scenario: Score includes fixture metadata in JSON output
- **WHEN** a benchmark run completes and a fixture has `purpose="Tests rebase conflict resolution"`, `difficulty="medium"`, `tags=["rebase"]`
- **THEN** the score entry in the JSON output includes those fields

#### Scenario: Score omits empty metadata fields in JSON output
- **WHEN** a benchmark run completes and a fixture has empty metadata fields
- **THEN** the score entry in the JSON output omits those fields (or includes them as empty/null)

### Requirement: Loader warns on missing metadata
The `FixtureLoader` SHALL emit a `logging.warning` when a fixture is loaded without one or more of the metadata fields (`purpose`, `difficulty`, `tags`). This is a soft warning — the fixture still loads successfully.

#### Scenario: Warning emitted for fixture without purpose
- **WHEN** a fixture YAML file has `difficulty` and `tags` but no `purpose`
- **THEN** a `logging.warning` is emitted indicating the missing `purpose` field

#### Scenario: No warning emitted for fixture with all metadata
- **WHEN** a fixture YAML file has all three metadata fields
- **THEN** no warning is emitted

### Requirement: Fixture metadata is excluded from model prompts
Fixture metadata (`purpose`, `difficulty`, `tags`) SHALL NOT be included in the prompt sent to the model. The model MUST only receive the `prompt` field from the fixture YAML.

#### Scenario: Model receives only the prompt field
- **WHEN** a benchmark runs a fixture with metadata fields
- **THEN** the model receives only the content of the `prompt` field, not `purpose`, `difficulty`, or `tags`

### Requirement: Difficulty levels are consistently defined
The difficulty enum values SHALL be defined as follows so all fixtures use a consistent calibration:

- `trivial`: Single straightforward git command with no edge cases
- `easy`: Simple multi-step operation with clear expected output
- `medium`: Requires understanding of Git concepts or multi-branch workflows
- `hard`: Complex scenarios, conflict resolution, or subtle Git behavior
- `expert`: Rare Git operations, advanced workflows, or scenarios requiring deep Git internals knowledge

#### Scenario: Difficulty rubric is documented
- **WHEN** a contributor reads CONTRIBUTING.md
- **THEN** they find the difficulty level definitions with descriptions and examples
