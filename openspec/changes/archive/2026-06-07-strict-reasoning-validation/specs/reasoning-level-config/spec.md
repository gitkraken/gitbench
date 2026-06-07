## ADDED Requirements

### Requirement: Run command validates all model-effort combinations
The `run` command SHALL validate every configured model-effort combination before any benchmarks execute. Validation SHALL use the merged capabilities resolver (cache + matrix). If ANY combination is invalid, the run SHALL abort with exit code 1 and a diagnostic message listing every invalid combination.

#### Scenario: All models pass validation
- **WHEN** all configured models have valid effort levels according to the capability resolver
- **THEN** the run SHALL proceed to execute benchmarks normally

#### Scenario: Single invalid model aborts run
- **WHEN** one model has an invalid effort level
- **THEN** the run SHALL abort before any API calls with a message identifying the model and the reason

#### Scenario: Multiple invalid models listed in error
- **WHEN** three models have invalid effort levels
- **THEN** the run SHALL abort with a message listing all three models and their specific validation failures

#### Scenario: Mock models bypass validation
- **WHEN** a model name starts with `mock` or `mock#` or `mock:`
- **THEN** validation SHALL skip that model without error

#### Scenario: Model without effort suffix passes
- **WHEN** a model has no effort level suffix
- **THEN** validation SHALL pass for that model regardless of capability state

### Requirement: Validation failure produces actionable error messages
Validation failure messages SHALL include the model name, the requested effort level, and the specific reason for failure. For unsupported effort levels, the message SHALL list the valid levels for that model. For models that don't support reasoning, the message SHALL clearly state that reasoning is not supported.

#### Scenario: Error for unsupported effort level
- **WHEN** `o3-mini#xhigh` is validated and the matrix says o3-mini supports `["minimal", "low", "medium", "high"]`
- **THEN** the error message SHALL contain: model name `o3-mini`, requested effort `xhigh`, and the list of supported levels

#### Scenario: Error for model without reasoning support
- **WHEN** `some-model#high` is validated and the model is not in the reasoning-capable set from the API
- **THEN** the error message SHALL indicate that the model does not support reasoning

### Requirement: Validation respects adapter-level effort handling
Models configured with an effort level that are routed through the Ollama adapter SHALL produce a warning rather than an error, since the adapter logs and ignores the level. OpenRouter-routed models SHALL be validated according to capability resolution.

#### Scenario: Ollama model with effort produces warning
- **WHEN** an Ollama model (localhost base_url) has an effort level suffix
- **THEN** the system SHALL emit a warning that the effort level will be ignored by Ollama but SHALL NOT abort the run

#### Scenario: OpenRouter model with effort is validated strictly
- **WHEN** an OpenRouter-routed model has an effort level suffix
- **THEN** the system SHALL apply full capability validation
