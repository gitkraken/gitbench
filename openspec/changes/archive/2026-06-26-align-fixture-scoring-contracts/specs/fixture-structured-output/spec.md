## ADDED Requirements

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
