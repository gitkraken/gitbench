## MODIFIED Requirements

### Requirement: ProviderIcon supports known providers list
The component SHALL include SVG icons for the following provider slugs: `anthropic`, `openai`, `google`, `meta`, `mistral`, `deepseek`, `minimax`, `xai`, `moonshot`, `zai`, `qwen`, `cohere`, `perplexity`. Each provider's icon SHALL be an SVG component registered in the `PROVIDER_ICONS` lookup table in `web/src/lib/custom-provider-icons.tsx`, sourced from `@thesvg/react`. The mapping SHALL be extensible by adding new imports and table entries.

Providers that are proxy/infrastructure services rather than first-party model builders (e.g., Ollama, OpenRouter) SHALL NOT receive custom logos — they render the automatic initial-circle fallback.

#### Scenario: All known providers render without error
- **WHEN** each provider in the known list is rendered
- **THEN** none throw an error; each displays its corresponding brand logo

#### Scenario: New provider added to mapping
- **WHEN** a developer adds an import from `@thesvg/react` to `custom-provider-icons.tsx` and an entry to the `PROVIDER_ICONS` table
- **THEN** the new provider renders its icon without changes to `ProviderIcon.tsx` resolution logic
