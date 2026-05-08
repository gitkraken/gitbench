## ADDED Requirements

### Requirement: Model name supports #level suffix
Model names in profiles, CLI, and all configuration contexts SHALL support an optional `#<level>` suffix that specifies the reasoning level for that model.

#### Scenario: Model name with reasoning level
- **WHEN** a profile lists `"o3-mini#high"` as a model
- **THEN** the base model name is `"o3-mini"` and the reasoning level is `"high"`

#### Scenario: Model name without reasoning level
- **WHEN** a profile lists `"gpt-4o-mini"` as a model
- **THEN** the base model name is `"gpt-4o-mini"` and the reasoning level is `None`

#### Scenario: Model name with multiple # characters
- **WHEN** a model name is `"model#a#b"`
- **THEN** only the last `#` SHALL be used as delimiter: base model is `"model#a"` and reasoning level is `"b"`

### Requirement: Adapters parse model name
Each adapter SHALL parse the model name at construction time, storing the base model name for API calls and the reasoning level for forwarding.

#### Scenario: OpenAI adapter parses model with level
- **WHEN** `OpenAIAdapter(model="o3-mini#high")` is constructed
- **THEN** `self.model` is `"o3-mini"` and `self.reasoning_level` is `"high"`

#### Scenario: Ollama adapter parses model with level
- **WHEN** `OllamaAdapter(model="llama3.1#medium")` is constructed
- **THEN** `self.model` is `"llama3.1"` and `self.reasoning_level` is `"medium"`

#### Scenario: Adapter preserves model name for display
- **WHEN** an adapter is constructed with `"o3-mini#high"`
- **THEN** the adapter SHALL store the original full model name for use in result metadata
