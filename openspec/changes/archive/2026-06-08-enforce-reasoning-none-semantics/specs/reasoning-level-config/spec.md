## MODIFIED Requirements

### Requirement: Run command validates all model-effort combinations
The `run` command SHALL validate every configured model-effort combination before any benchmarks execute. Static validation SHALL use the merged capabilities resolver (cache + matrix). OpenRouter targets configured with `none` that pass static validation SHALL also complete behavioral preflight validation before fixture execution. If ANY static combination is invalid or ANY `none` target is unsupported or unverifiable, the complete run SHALL abort with exit code 1 and an actionable diagnostic.

#### Scenario: All models pass validation
- **WHEN** all configured models have valid effort levels and every configured OpenRouter `none` target passes behavioral preflight
- **THEN** the run SHALL proceed to execute benchmarks normally

#### Scenario: Single invalid model aborts run
- **WHEN** one model has an invalid effort level
- **THEN** the run SHALL abort before any model API calls with a message identifying the model and the reason

#### Scenario: Multiple invalid models listed in error
- **WHEN** three models have invalid effort levels
- **THEN** the run SHALL abort with a message listing all three models and their specific validation failures

#### Scenario: Mock models bypass validation
- **WHEN** a model name starts with `mock` or `mock#` or `mock:`
- **THEN** validation SHALL skip that model without error

#### Scenario: Model without effort suffix passes
- **WHEN** a model has no effort level suffix
- **THEN** validation SHALL pass for that model regardless of capability state

#### Scenario: Listed none target passes preflight
- **WHEN** an OpenRouter model lists `none` as supported and its preflight reports `reasoning_tokens: 0` with no reasoning content
- **THEN** validation SHALL accept the target and allow benchmark fixture execution

#### Scenario: Listed none target emits reasoning
- **WHEN** an OpenRouter model lists `none` as supported but its preflight reports non-zero reasoning tokens or non-empty reasoning content
- **THEN** the complete run SHALL abort immediately before benchmark fixture execution

#### Scenario: Listed none target lacks telemetry
- **WHEN** an OpenRouter model lists `none` as supported but its preflight does not explicitly report reasoning token usage
- **THEN** the complete run SHALL abort as unverifiable before benchmark fixture execution

#### Scenario: Duplicate none targets share preflight
- **WHEN** the same effective OpenRouter model and routing configuration appears multiple times in the scheduled run
- **THEN** the run SHALL perform one behavioral preflight for that routing identity
