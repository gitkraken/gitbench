## MODIFIED Requirements

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

#### Scenario: Non-finite parsed value is rejected
- **WHEN** a structured response parses to a payload containing a non-finite numeric value
- **THEN** the fixture result fails as a structured-output parse failure
- **AND** the non-finite value is not stored as the parsed payload

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
- **AND** the score payload does not include the invalid value as `parsed_payload`

#### Scenario: Invalid payload keeps raw output visible
- **WHEN** a structured response fails strict parse or schema validation
- **THEN** the score payload's `model_output` contains the raw provider output string
- **AND** `raw_structured_output` contains the raw provider output string
