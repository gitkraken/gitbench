## Purpose

Reasoning level config defines how GitBench parses model effort suffixes from configured model names and preserves base model identity for provider calls, display, validation, and capacity grouping.
## Requirements
### Requirement: Model name supports #level suffix
Model names in profiles, CLI, and all configuration contexts SHALL support an optional GitBench effort suffix that specifies the effort level for that run target. The suffix MAY use `#<level>` or `:<level>`. A final colon segment SHALL be treated as effort only when it exactly matches a valid GitBench effort value. Valid effort values SHALL be `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`.

#### Scenario: Model name with hash effort level
- **WHEN** a profile lists `"o3-mini#high"` as a model
- **THEN** the base model name is `"o3-mini"` and the reasoning level is `"high"`

#### Scenario: Model name with colon effort level
- **WHEN** a profile lists `"anthropic/claude-opus-4.7:max"` as a model
- **THEN** the base model name is `"anthropic/claude-opus-4.7"` and the reasoning level is `"max"`

#### Scenario: Model name without reasoning level
- **WHEN** a profile lists `"gpt-4o-mini"` as a model
- **THEN** the base model name is `"gpt-4o-mini"` and the reasoning level is `None`

#### Scenario: Model name with multiple # characters
- **WHEN** a model name is `"model#a#b"`
- **THEN** only the last `#` SHALL be used as delimiter: base model is `"model#a"` and reasoning level is `"b"`

#### Scenario: Colon model tag that is not an effort
- **WHEN** a model name is `"llama3.1:8b"`
- **THEN** the base model name is `"llama3.1:8b"` and the reasoning level is `None`

#### Scenario: Colon effort after model tag
- **WHEN** a model name is `"llama3.1:8b:high"`
- **THEN** the base model name is `"llama3.1:8b"` and the reasoning level is `"high"`

#### Scenario: Anthropic max effort is valid
- **WHEN** a profile lists `"anthropic/claude-opus-4.7:max"` as a model
- **THEN** model validation accepts the `max` effort level

### Requirement: Adapters parse model name
Each adapter SHALL parse the model name at construction time, storing the base model name for API calls and the reasoning level for forwarding or recording. Capacity grouping SHALL use the parsed base model name, not the full model name with effort.

#### Scenario: OpenAI adapter parses model with level
- **WHEN** `OpenAIAdapter(model="o3-mini#high")` is constructed
- **THEN** `self.model` is `"o3-mini"` and `self.reasoning_level` is `"high"`

#### Scenario: OpenRouter-compatible adapter parses colon effort
- **WHEN** `OpenAIAdapter(model="anthropic/claude-opus-4.7:max", base_url="https://openrouter.ai/api/v1")` is constructed
- **THEN** `self.model` is `"anthropic/claude-opus-4.7"` and `self.reasoning_level` is `"max"`

#### Scenario: Ollama adapter parses model with level
- **WHEN** `OllamaAdapter(model="llama3.1#medium")` is constructed
- **THEN** `self.model` is `"llama3.1"` and `self.reasoning_level` is `"medium"`

#### Scenario: Adapter preserves model name for display
- **WHEN** an adapter is constructed with `"o3-mini#high"`
- **THEN** the adapter SHALL store the original full model name for use in result metadata

#### Scenario: Capacity identity excludes effort
- **WHEN** an adapter is constructed with `"anthropic/claude-opus-4.7:max"`
- **THEN** scheduler capacity grouping uses `"anthropic/claude-opus-4.7"` as the base model ID

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

