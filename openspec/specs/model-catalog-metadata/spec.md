# model-catalog-metadata Specification

## Purpose
Define the normalized model metadata catalog, its explicit synchronization workflow, validation guarantees, and reviewed weight-access classification.

## Requirements

### Requirement: Normalized model metadata catalog
The system SHALL provide a committed metadata catalog keyed by canonical base-model group ID, with each record containing a nullable context-window token count, a weight-access value of `open`, `closed`, or `unknown`, source provenance, and a refresh timestamp.

#### Scenario: Catalog record is consumed by the frontend
- **WHEN** a chart response contains a base-model group that exists in the catalog
- **THEN** the frontend receives normalized metadata for that canonical group ID without contacting an upstream service

#### Scenario: Metadata is unavailable
- **WHEN** a current base-model group has no verified context-window or weight-access value
- **THEN** the catalog represents the missing value as null or `unknown` rather than guessing

### Requirement: Explicit metadata synchronization
The system SHALL provide an explicit synchronization command that fetches upstream model metadata, normalizes it, applies reviewed aliases and overrides, and writes the committed catalog deterministically.

#### Scenario: Exact upstream identifier matches
- **WHEN** an upstream model ID exactly matches a current canonical base-model group ID
- **THEN** the synchronization command normalizes the supported upstream fields into that group's catalog record

#### Scenario: Renamed or ambiguous model is overridden
- **WHEN** a reviewed alias or field override exists for a model
- **THEN** the synchronization command applies the override in preference to the fetched value

#### Scenario: Ordinary build runs offline
- **WHEN** the application performs a normal build using an existing catalog snapshot
- **THEN** the build completes without fetching the upstream model catalog

### Requirement: Metadata validation and diagnostics
The synchronization command MUST validate canonical-ID uniqueness, allowed weight-access values, non-negative context-window values, stable output ordering, and coverage of current report base-model groups.

#### Scenario: Current model remains unresolved
- **WHEN** a current report base-model group cannot be matched after aliases and overrides
- **THEN** the command reports the canonical ID and retains an explicit unknown classification

#### Scenario: Generated value is invalid
- **WHEN** normalization or an override would produce an invalid catalog value
- **THEN** the command exits unsuccessfully without replacing the last valid committed catalog

### Requirement: Open-weights classification is distinct from licensing
The system SHALL treat weight access as a tri-state reviewed classification and MUST NOT classify a model as open solely because an upstream Hugging Face identifier is present.

#### Scenario: Hugging Face identifier lacks reviewed classification
- **WHEN** upstream metadata supplies a Hugging Face identifier but no reviewed rule or override establishes weight access
- **THEN** the model remains `unknown` rather than being automatically labeled `open`
