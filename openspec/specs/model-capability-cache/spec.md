# model-capability-cache Specification

## Purpose
TBD - created by archiving change strict-reasoning-validation. Update Purpose after archive.
## Requirements
### Requirement: Cache model capabilities from OpenRouter
The system SHALL maintain a local cache of model capabilities fetched from the OpenRouter `/api/v1/models` endpoint with `supported_parameters=reasoning` filter. The cache SHALL be stored as JSON at `~/.cache/gitbench/model-capabilities.json` with a `fetched_at` ISO timestamp. The cache SHALL be considered fresh if fetched within the last 7 days.

#### Scenario: Cache miss triggers API fetch
- **WHEN** the cache file does not exist
- **THEN** the system SHALL fetch the model list from OpenRouter and write the cache file

#### Scenario: Stale cache triggers API fetch
- **WHEN** the cache file exists but `fetched_at` is older than 7 days from the current time
- **THEN** the system SHALL fetch a fresh model list and overwrite the cache file

#### Scenario: Fresh cache skips API fetch
- **WHEN** the cache file exists and `fetched_at` is less than 7 days old
- **THEN** the system SHALL use the cached data without making an API call

#### Scenario: API fetch failure with stale cache
- **WHEN** the API fetch fails (network error, timeout) AND a cache file exists
- **THEN** the system SHALL log a warning and use the stale cached data

#### Scenario: API fetch failure with no cache
- **WHEN** the API fetch fails AND no cache file exists
- **THEN** the system SHALL abort with an error message indicating that capabilities could not be resolved

### Requirement: Cache stores reasoning-capable model identifiers
The cache SHALL contain a `reasoning_models` key whose value is a list of model identifiers (strings) that support the `reasoning` parameter.

#### Scenario: Cache contains only reasoning-capable models
- **WHEN** the API returns 341 models
- **THEN** the cache `reasoning_models` list SHALL contain only the ~183 models whose `supported_parameters` includes `reasoning`

### Requirement: Effort matrix is shipped data file
The system SHALL ship a comprehensive effort matrix at `gitbench/data/effort_matrix.json` mapping model identifiers to arrays of valid effort level strings. The matrix SHALL be the authoritative source for which effort levels are valid for each model.

#### Scenario: Matrix covers known models
- **WHEN** the matrix is loaded
- **THEN** it SHALL provide valid effort levels for all models listed in the project's `.gitbench.json` profiles

#### Scenario: Matrix includes max where supported
- **WHEN** a model is known to support the `max` effort level (e.g., `openai/gpt-5`)
- **THEN** the matrix SHALL include `max` in the valid levels for that model

#### Scenario: Matrix excludes max by default
- **WHEN** a model is not known to support `max`
- **THEN** the matrix SHALL NOT include `max` as a valid level for that model

### Requirement: Capability resolver merges cache and matrix
The system SHALL provide a function that resolves model capabilities by merging the API cache (which models support reasoning) with the shipped matrix (which effort levels are valid per model). A model SHALL be considered valid for an effort level only when both sources confirm compatibility.

#### Scenario: Model with reasoning support and known effort levels
- **WHEN** `openai/gpt-4o` is in the reasoning set AND the matrix lists `["minimal", "low", "medium", "high", "xhigh"]` AND effort is `"high"`
- **THEN** validation SHALL pass

#### Scenario: Model with reasoning support but unknown effort level
- **WHEN** a model is in the reasoning set AND the matrix lists valid levels BUT the requested effort is NOT in that list
- **THEN** validation SHALL fail with a message listing the supported levels

#### Scenario: Model without reasoning support but effort configured
- **WHEN** a model has an effort level suffix (e.g., `#high`) but is NOT in the reasoning set from the API
- **THEN** validation SHALL fail with a message indicating the model does not support reasoning

#### Scenario: Model not in matrix and no effort configured
- **WHEN** a model has no effort level suffix
- **THEN** validation SHALL pass regardless of whether the model is in the matrix or reasoning set

#### Scenario: Model with reasoning support and max effort validated
- **WHEN** a model is in the reasoning set AND the matrix includes `max` as a valid level AND effort is `"max"`
- **THEN** validation SHALL pass

#### Scenario: Model with reasoning support but max effort not in matrix
- **WHEN** a model is in the reasoning set AND the matrix does NOT include `max` as a valid level AND effort is `"max"`
- **THEN** validation SHALL fail with a message listing the supported levels and noting that `max` is not among them

