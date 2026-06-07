## MODIFIED Requirements

### Requirement: Model adapters return full conversation transcript

The adapter SHALL check both `message.reasoning_content` (OpenAI native) and `message.reasoning` (OpenRouter) when building the transcript. The `reasoning_content` field SHALL take priority when both are present.

(All original scenarios remain unchanged.)

#### Scenario: OpenAI adapter captures reasoning_content from OpenRouter response
- **WHEN** `OpenAIAdapter.generate()` is called with a base URL pointing to OpenRouter
- **AND** the API returns `message.reasoning: "Let me think about this..."` but NOT `message.reasoning_content`
- **THEN** the assistant entry in `transcript` includes `"reasoning_content": "Let me think about this..."` (normalized to `reasoning_content` key)

#### Scenario: OpenAI adapter prefers native reasoning_content over OpenRouter reasoning
- **WHEN** the API returns both `message.reasoning_content: "native"` and `message.reasoning: "openrouter"`
- **THEN** the assistant entry uses `"reasoning_content": "native"` (native OpenAI field takes priority)
