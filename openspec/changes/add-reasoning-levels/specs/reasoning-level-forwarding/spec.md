## ADDED Requirements

### Requirement: OpenAIAdapter forwards reasoning level as reasoning_effort
When an `OpenAIAdapter` was constructed with a reasoning level, calls to `generate()` SHALL forward it as `reasoning_effort` to the OpenAI API.

#### Scenario: OpenAI call with reasoning level from model name
- **WHEN** `OpenAIAdapter(model="o3-mini#high")` calls `generate()`
- **THEN** the `client.chat.completions.create()` call SHALL include `reasoning_effort="high"`

#### Scenario: OpenAI call without reasoning level
- **WHEN** `OpenAIAdapter(model="o3-mini")` calls `generate()`
- **THEN** the `client.chat.completions.create()` call SHALL NOT include `reasoning_effort`

### Requirement: OllamaAdapter ignores reasoning level
When an `OllamaAdapter` was constructed with a reasoning level, calls to `generate()` SHALL log a debug message and NOT include the level in the request.

#### Scenario: Ollama call with reasoning level from model name
- **WHEN** `OllamaAdapter(model="llama3.1#medium")` calls `generate()`
- **THEN** a debug-level log message SHALL be emitted and the request body SHALL NOT include reasoning parameters

#### Scenario: Ollama call without reasoning level
- **WHEN** `OllamaAdapter(model="llama3.1")` calls `generate()`
- **THEN** no debug message about reasoning SHALL be logged and the request SHALL proceed normally

### Requirement: MockModelClient ignores reasoning level
The `MockModelClient` SHALL silently accept and ignore the `#level` suffix in model names.

#### Scenario: Mock with reasoning level
- **WHEN** `MockModelClient()` or `get_model_client("mock#high")` is used
- **THEN** mock behavior SHALL be unchanged and `call_count` SHALL increment normally
