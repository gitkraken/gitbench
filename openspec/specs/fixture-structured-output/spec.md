# fixture-structured-output Specification

## Purpose
Defines structured-output contracts for fixtures using a named schema registry with benchmark-level defaults and fixture-level overrides, enabling schema-enforced JSON runs with canonical text rendering for scoring.

## Requirements

### Requirement: Named schema registry provides all output schemas
GitBench SHALL maintain a registry of named structured-output schemas, each a complete `StructuredOutputContract` (JSON Schema, primary path, canonicalization strategy, display label) identified by a unique string name. Every schema in the registry SHALL set `additionalProperties` to false for every object shape sent to a provider.

#### Scenario: Schema looked up by name
- **WHEN** a fixture or benchmark references a schema by name (e.g., `commit_message`)
- **THEN** the registry returns the complete `StructuredOutputContract` for that name
- **AND** the contract's JSON Schema has semantically meaningful key names matching the expected output type

#### Scenario: Commit message schema uses explicit key
- **WHEN** the `commit_message` schema is resolved
- **THEN** its contract exposes a string field named `commit_message`
- **AND** canonicalization renders the `commit_message` value as the scorer text

#### Scenario: Conflict resolution content is semantically distinct from file content
- **WHEN** the `resolved_content` schema is resolved (for merge conflicts, cherry-pick, rebase)
- **THEN** its contract exposes a string field named `resolved_content`
- **WHEN** the `file_content` schema is resolved (for reading file content from history)
- **THEN** its contract exposes a string field named `content`
- **AND** the two schemas are distinct entries in the registry despite both canonicalizing as strings

### Requirement: Benchmark-level default schemas
Each benchmark SHALL have a default schema name in `BENCHMARK_DEFAULT_SCHEMAS` that applies to all fixtures in that benchmark unless overridden by a per-fixture `output_schema` field. Benchmarks with heterogeneous output shapes (where different fixtures expect different output types) SHALL NOT have a benchmark-level default and MUST rely on per-fixture overrides.

#### Scenario: Homogeneous benchmark uses default
- **WHEN** a fixture in `blame_forensics` has no `output_schema` field
- **THEN** the benchmark default `commit_message` is used
- **AND** the contract uses key `commit_message`

#### Scenario: Heterogeneous benchmark has no default
- **WHEN** a fixture in `git_show` has no `output_schema` field
- **THEN** resolution falls through to the scoring-type fallback
- **AND** if no scoring-type fallback applies, resolution errors with a clear message

### Requirement: Fixture-level output_schema override
Fixtures MAY declare an `output_schema` field containing a string referencing a named schema from the registry. This field SHALL take precedence over benchmark defaults and scoring-type fallbacks.

#### Scenario: Fixture overrides benchmark default
- **WHEN** a fixture in `worktree_usage` declares `output_schema: command_list`
- **THEN** the `command_list` schema is used for that fixture
- **AND** the benchmark default `command` is not used

#### Scenario: Fixture overrides scoring-type fallback
- **WHEN** a fixture in `git_grep` with `unordered_line_set` scoring declares `output_schema: file_list`
- **THEN** the `file_list` schema is used (key `files`, array type)
- **AND** the scoring-type fallback `string_list` is not used
- **AND** scoring still uses `unordered_line_set` logic on the canonicalized output

### Requirement: Scoring-type fallbacks for natural output shapes
Scoring types that have a natural output shape SHALL have a fallback schema in `SCORING_TYPE_FALLBACKS`. The scoring type `exact_match` SHALL NOT have a fallback — it is polymorphic and MUST be resolved via benchmark default or fixture-level override.

#### Scenario: Scoring type with natural shape falls back
- **WHEN** a fixture with `numeric_exact` scoring has no `output_schema` and no benchmark default
- **THEN** the `count` schema is used as a fallback

#### Scenario: exact_match errors without explicit configuration
- **WHEN** a fixture with `exact_match` scoring has no `output_schema` field and its benchmark has no default
- **THEN** resolution raises a configuration error
- **AND** the error message identifies the fixture ID, benchmark name, and suggests adding `output_schema` to the fixture YAML

### Requirement: Structured-output contracts are validated for all fixtures
GitBench SHALL provide a validation path that checks every fixture resolves to a named schema in the registry and that the fixture's expected answer roundtrips through the resolved contract's schema and canonicalization.

#### Scenario: Missing schema resolution blocks validation
- **WHEN** the fixture validation path checks a fixture that cannot resolve to any named schema
- **THEN** validation fails and identifies the benchmark and fixture id

#### Scenario: Invalid schema blocks validation
- **WHEN** a fixture contract has an invalid JSON Schema, missing required property definition, or object schema that allows undeclared additional properties
- **THEN** validation fails and identifies the contract problem

#### Scenario: Canonical expected answer is representable
- **WHEN** validation checks a fixture contract
- **THEN** the fixture's expected answer can be represented as a structured payload and canonicalized back into scorer-compatible text

### Requirement: Structured responses canonicalize before scoring
For schema-enforced JSON runs, GitBench SHALL strictly parse the model response as standard JSON, validate the parsed payload against the fixture contract, render canonical scorer text from the declared field or path, and pass that canonical text to the existing benchmark scorer. The strict parse step MUST reject non-standard JSON constants such as `NaN`, `Infinity`, and `-Infinity`, and MUST reject parsed non-finite numeric values.

#### Scenario: Valid structured payload is scored through canonical text
- **WHEN** a structured response contains a valid payload for the fixture contract
- **THEN** `model_output` is set to the canonical text rendered from the structured payload
- **AND** the existing scorer receives that canonical text

#### Scenario: Parse failure is recorded as fixture failure
- **WHEN** a structured response cannot be parsed as strict standard JSON
- **THEN** the fixture result fails
- **AND** the result records a structured-output error without invoking a different scoring mode

#### Scenario: Schema validation failure is recorded as fixture failure
- **WHEN** a structured response parses as JSON but does not match the fixture contract schema
- **THEN** the fixture result fails
- **AND** the result records a structured-output schema error without invoking the benchmark scorer

### Requirement: Raw structured data is preserved
Structured-output fixture results SHALL preserve the raw provider output, parsed structured payload when the payload parses and validates successfully, and structured-output error details when parsing or validation fails.

#### Scenario: Parsed payload stored
- **WHEN** a structured response parses and validates successfully
- **THEN** the score payload includes the parsed structured payload
- **AND** the score payload includes the canonical `model_output`

#### Scenario: Invalid payload stored for debugging
- **WHEN** a structured response is invalid
- **THEN** the score payload includes the raw structured output where available
- **AND** the score payload includes a structured-output error message

### Requirement: Model adapters support provider-neutral structured output requests
The runner SHALL pass a provider-neutral structured-output contract to model adapters. Each adapter SHALL translate the contract to the provider's supported structured-output request shape or fail early with a clear unsupported-provider error.

#### Scenario: OpenAI-compatible structured request
- **WHEN** an OpenAI-compatible adapter receives `output_mode=json_schema`
- **THEN** it sends the fixture JSON Schema using the provider's structured-output response format

#### Scenario: Ollama structured request
- **WHEN** an Ollama adapter receives `output_mode=json_schema`
- **THEN** it sends the fixture JSON Schema using Ollama's native structured-output format support

### Requirement: Multi-file resolved-content structured output
GitBench SHALL provide a structured-output schema for fixtures that expect resolved content for multiple named files.

#### Scenario: Multi-file schema captures file map
- **WHEN** a fixture uses the multi-file resolved-content schema
- **THEN** the structured payload represents file names mapped to resolved file content

#### Scenario: Canonicalization preserves file-block scoring input
- **WHEN** a valid multi-file structured payload is canonicalized
- **THEN** the canonical text can be scored by `resolved_file_blocks` without losing file names or content

#### Scenario: Existing single resolved content schema remains valid
- **WHEN** a fixture still uses the existing `resolved_content` schema
- **THEN** its structured-output behavior is unchanged
