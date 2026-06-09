# reasoning-token-measurement Specification

## Purpose
TBD - created by archiving change record-model-metadata. Update Purpose after archive.
## Requirements
### Requirement: Model adapters extract reasoning tokens from API usage

The `ModelInterface.generate()` return dict's `usage` key SHALL include an optional `reasoning_tokens` field extracted from provider-specific API response data. When the API response does not include reasoning token data, the field SHALL be absent from the usage dict or set to `None`.

#### Scenario: OpenAI adapter extracts reasoning tokens
- **WHEN** `OpenAIAdapter.generate()` receives a response where `response.usage.completion_tokens_details.reasoning_tokens` is 150
- **THEN** the return dict's `usage` contains `"reasoning_tokens": 150`

#### Scenario: OpenAI adapter handles missing reasoning token details
- **WHEN** `OpenAIAdapter.generate()` receives a response where `response.usage.completion_tokens_details` is `None`
- **THEN** the return dict's `usage` does NOT contain a `reasoning_tokens` key, or its value is `None`

#### Scenario: OpenAI adapter handles missing usage entirely
- **WHEN** `OpenAIAdapter.generate()` receives a response with no `usage` attribute
- **THEN** the return dict's `usage` is `None`

#### Scenario: Ollama adapter omits reasoning tokens
- **WHEN** `OllamaAdapter.generate()` receives a response from Ollama's `/api/chat`
- **THEN** the return dict's `usage` does NOT contain a `reasoning_tokens` key (Ollama does not report reasoning tokens in its standard API)

#### Scenario: Mock adapter returns hardcoded reasoning tokens
- **WHEN** `MockModelClient.generate()` is called
- **THEN** the return dict's `usage` contains `"reasoning_tokens": 20`

### Requirement: Score dataclass stores reasoning tokens

The `Score` dataclass SHALL have an optional `reasoning_tokens: int | None` field with a default of `None`. The `to_dict()` method SHALL omit the field when it is `None`. The `from_dict()` method SHALL accept `reasoning_tokens` when present and default to `None` when absent.

#### Scenario: reasoning_tokens defaults to None
- **WHEN** a `Score` is created without specifying `reasoning_tokens`
- **THEN** `score.reasoning_tokens` is `None`

#### Scenario: to_dict omits None reasoning_tokens
- **WHEN** `score.to_dict()` is called on a `Score` with `reasoning_tokens=None`
- **THEN** the resulting dict does NOT contain a `reasoning_tokens` key

#### Scenario: to_dict includes non-None reasoning_tokens
- **WHEN** `score.to_dict()` is called on a `Score` with `reasoning_tokens=150`
- **THEN** the resulting dict contains `"reasoning_tokens": 150`

#### Scenario: from_dict handles missing reasoning_tokens
- **WHEN** `Score.from_dict()` is called with a dict that has no `reasoning_tokens` key
- **THEN** the returned `Score` has `reasoning_tokens=None`

### Requirement: Runner maps reasoning tokens from response to Score

The `BenchmarkRunner._run_fixture()` method SHALL extract `reasoning_tokens` from the model response's `usage` dict and assign it to `score.reasoning_tokens`. When the usage dict is `None` or lacks the key, the score field SHALL remain `None`.

#### Scenario: Reasoning tokens mapped from successful response
- **WHEN** `_run_fixture()` receives a response with `usage={"reasoning_tokens": 150, ...}`
- **THEN** `score.reasoning_tokens` is `150`

#### Scenario: Reasoning tokens None when usage missing
- **WHEN** `_run_fixture()` receives a response with `usage=None`
- **THEN** `score.reasoning_tokens` is `None`

### Requirement: Token summaries include reasoning tokens

The model token summaries query in `node-sqlite-report-store.ts` SHALL include `COALESCE(SUM(reasoning_tokens), 0) AS reasoning_tokens` alongside the existing `input_tokens`, `output_tokens`, and `total_tokens` aggregations. The `ModelTokenSummary` type SHALL include a `reasoning_tokens: number` field.

#### Scenario: Reasoning tokens aggregated per model
- **WHEN** a model has 3 fixture results with reasoning_tokens [50, null, 100]
- **THEN** the model's token summary has `reasoning_tokens: 150`

#### Scenario: Model with no reasoning data
- **WHEN** a model has no fixture results with non-null reasoning_tokens
- **THEN** the model's token summary has `reasoning_tokens: 0`

## ADDED Requirements

### Requirement: Output token decomposition preserves provider totals
GitBench SHALL retain `output_tokens` as the raw provider-reported completion-token total. When reasoning tokens are reported as part of completion tokens, presentation code SHALL derive non-reasoning visible output as `max(output_tokens - reasoning_tokens, 0)` and SHALL NOT add reasoning tokens to `output_tokens` or `total_tokens`.

#### Scenario: Reasoning is included in provider output
- **WHEN** a result reports `output_tokens: 1349` and `reasoning_tokens: 1343`
- **THEN** GitBench SHALL retain total output as 1349 and derive visible output as 6

#### Scenario: Result has no reasoning token data
- **WHEN** a result reports `output_tokens: 200` and `reasoning_tokens: null`
- **THEN** GitBench SHALL derive visible output as 200

#### Scenario: Result has no output token data
- **WHEN** a result has no `output_tokens`
- **THEN** visible output SHALL remain unavailable regardless of reasoning token data

#### Scenario: Provider reasoning exceeds output
- **WHEN** a provider reports `output_tokens: 100` and `reasoning_tokens: 120`
- **THEN** GitBench SHALL preserve both raw values and derive visible output as 0 rather than a negative number

#### Scenario: Total tokens are not double-counted
- **WHEN** input is 500, provider output is 200, reasoning is 150, and total is 700
- **THEN** report and chart calculations SHALL continue to use total 700 rather than calculating 850

