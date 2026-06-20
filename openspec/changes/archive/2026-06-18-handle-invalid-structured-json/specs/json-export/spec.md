## ADDED Requirements

### Requirement: JSON export emits strict standard JSON
Generated report JSON artifacts SHALL be valid standard JSON that can be parsed by browser-compatible `JSON.parse` implementations. Report JSON serialization MUST NOT emit bare `NaN`, `Infinity`, or `-Infinity` constants.

#### Scenario: Non-finite value cannot be serialized
- **WHEN** report generation attempts to serialize aggregate data containing a non-finite numeric value
- **THEN** report generation fails with a clear serialization error
- **AND** the generated report JSON artifact does not contain bare non-finite JSON constants

#### Scenario: Browser parser can read generated report
- **WHEN** `render_json(data, "web/public/results.json")` completes successfully
- **THEN** the written file can be parsed by a browser-compatible JSON parser

## MODIFIED Requirements

### Requirement: JSON export includes structured-output result metadata
Fixture results in aggregated JSON SHALL include structured-output metadata when available, including raw structured output, parsed payload, and structured-output error details. Parsed payloads SHALL be included only for structured responses that parsed as strict JSON and validated against the fixture contract. Invalid structured responses SHALL be represented through raw structured output and structured-output error fields rather than invalid or non-finite parsed payload values.

#### Scenario: Valid structured result exported
- **WHEN** a structured fixture result has a parsed payload
- **THEN** the aggregated fixture result includes the parsed structured payload and canonical `model_output`

#### Scenario: Invalid structured result exported
- **WHEN** a structured fixture result has a structured-output error
- **THEN** the aggregated fixture result includes the structured-output error
- **AND** the aggregated fixture result includes the raw structured output where available
- **AND** the aggregated fixture result does not include the invalid response as `parsed_payload`

#### Scenario: Invalid structured result keeps report JSON valid
- **WHEN** a structured fixture result failed because the raw response was invalid JSON or failed schema validation
- **THEN** the aggregated fixture result represents the raw model response as a string
- **AND** `results.json` remains valid standard JSON
