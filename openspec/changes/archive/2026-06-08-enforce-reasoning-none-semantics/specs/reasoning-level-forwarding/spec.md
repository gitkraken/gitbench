## MODIFIED Requirements

### Requirement: OpenAIAdapter forwards reasoning level as reasoning_effort
When an `OpenAIAdapter` was constructed with a reasoning level, calls to `generate()` SHALL forward it using the transport-appropriate request shape. For the first-party OpenAI API, the adapter SHALL forward the value as `reasoning_effort`. For OpenRouter-compatible base URLs, non-`none` levels SHALL be forwarded as `reasoning.effort`, while `none` SHALL be forwarded as an explicit disabled reasoning configuration.

#### Scenario: OpenAI call with reasoning level from model name
- **WHEN** `OpenAIAdapter(model="o3-mini#high")` calls `generate()`
- **THEN** the `client.chat.completions.create()` call SHALL include `reasoning_effort="high"`

#### Scenario: OpenAI call with none
- **WHEN** `OpenAIAdapter(model="gpt-5.4#none")` calls `generate()` against the first-party OpenAI API
- **THEN** the call SHALL include `reasoning_effort="none"`

#### Scenario: OpenRouter call with max effort from model name
- **WHEN** `OpenAIAdapter(model="anthropic/claude-opus-4.7:max", base_url="https://openrouter.ai/api/v1")` calls `generate()`
- **THEN** the call SHALL include `reasoning={"effort": "max"}`

#### Scenario: OpenRouter call explicitly disables reasoning
- **WHEN** `OpenAIAdapter(model="some/model:none", base_url="https://openrouter.ai/api/v1")` calls `generate()`
- **THEN** the call SHALL include `reasoning={"enabled": false}` and SHALL NOT send `reasoning.effort="none"`

#### Scenario: OpenRouter reasoning preserves extra body
- **WHEN** an OpenRouter call includes caller-provided `extra_body` routing fields
- **THEN** the adapter SHALL merge the reasoning configuration without removing routing fields or mutating the caller-owned object

#### Scenario: OpenAI call without reasoning level
- **WHEN** `OpenAIAdapter(model="o3-mini")` calls `generate()`
- **THEN** the `client.chat.completions.create()` call SHALL NOT include reasoning controls

## ADDED Requirements

### Requirement: None responses contain verifiable zero reasoning
Every response produced by a model configured with reasoning level `none` SHALL explicitly report zero reasoning tokens and SHALL contain no non-empty reasoning content. A violation or missing reasoning telemetry SHALL raise a fatal reasoning-disable error rather than being converted into an ordinary failed fixture score.

#### Scenario: None response reports zero reasoning
- **WHEN** a `none` response reports `reasoning_tokens: 0` and has no reasoning content
- **THEN** the response SHALL be accepted

#### Scenario: None response reports reasoning tokens
- **WHEN** a `none` response reports `reasoning_tokens` greater than zero
- **THEN** the adapter SHALL raise a fatal reasoning-disable error identifying the model and observed token count

#### Scenario: None response contains reasoning content
- **WHEN** a `none` response contains non-empty `reasoning`, `reasoning_content`, or equivalent normalized reasoning text
- **THEN** the adapter SHALL raise a fatal reasoning-disable error

#### Scenario: None response omits reasoning telemetry
- **WHEN** a `none` response has no explicit reasoning-token count
- **THEN** the adapter SHALL raise a fatal reasoning-disable error stating that the no-reasoning invariant could not be verified

#### Scenario: Runtime violation aborts target
- **WHEN** a benchmark fixture response violates the `none` invariant after preflight succeeded
- **THEN** GitBench SHALL stop scheduling work for the target, cancel pending work best-effort, omit the violating response from normal scores, and exit the run non-zero
