# provider-brand-icons Specification

## Purpose

ProviderIcon renders brand SVG icons for AI model providers, sourced from `@thesvg/react`, with `currentColor` coloring and visibility enhancements for dark backgrounds.

## Requirements

### Requirement: ProviderIcon maps provider slugs to custom SVG icons

A `ProviderIcon` React component SHALL render the appropriate brand icon from a custom SVG lookup table for a given provider slug. The component SHALL accept a `provider` prop (lowercase string, e.g. `"anthropic"`, `"openai"`) and a `size` prop (number, default 16).

The component SHALL look up the provider in a single `PROVIDER_ICONS` map. If found, it SHALL render the corresponding SVG component at the requested size. If not found, it SHALL render a colored circle with the provider's first letter.

For icons rendered at sizes ≤ 14 pixels, the component SHALL apply a subtle background circle (`rgba(255,255,255,0.08)`) behind the icon to ensure visibility of dark brand colors against dark backgrounds.

#### Scenario: Claude icon renders for Anthropic provider

- **WHEN** `<ProviderIcon provider="anthropic" size={16} />` renders
- **THEN** the Claude brand mark is displayed at 16×16 pixels in the Anthropic palette color (#D97757)

#### Scenario: OpenAI icon renders

- **WHEN** `<ProviderIcon provider="openai" size={20} />` renders
- **THEN** the OpenAI brand logo is displayed at 20×20 pixels in the OpenAI brand color (#10A37F)

#### Scenario: Small icon receives background circle

- **WHEN** `<ProviderIcon provider="google" size={12} />` renders
- **THEN** a subtle `rgba(255,255,255,0.08)` background circle appears behind the icon

#### Scenario: Large icon does not receive background circle

- **WHEN** `<ProviderIcon provider="meta" size={20} />` renders
- **THEN** no background circle is rendered behind the icon

#### Scenario: Unknown provider falls back to initial circle

- **WHEN** `<ProviderIcon provider="unknown-provider" size={16} />` renders
- **THEN** a colored circle with the first letter "U" is displayed at 16×16 pixels

### Requirement: ProviderIcon supports known providers list

The component SHALL include SVG icons for the following provider slugs: `anthropic`, `openai`, `google`, `meta`, `mistral`, `deepseek`, `minimax`, `xai`, `moonshot`, `zai`, `qwen`, `cohere`, `perplexity`. Each provider's icon SHALL be an SVG component registered in the `PROVIDER_ICONS` lookup table in `web/src/lib/custom-provider-icons.tsx`, sourced from `@thesvg/react`. The mapping SHALL be extensible by adding new imports and table entries.

Providers that are proxy/infrastructure services rather than first-party model builders (e.g., Ollama, OpenRouter) SHALL NOT receive custom logos — they render the automatic initial-circle fallback.

#### Scenario: All known providers render without error

- **WHEN** each provider in the known list is rendered
- **THEN** none throw an error; each displays its corresponding brand logo

#### Scenario: New provider added to mapping

- **WHEN** a developer adds an import from `@thesvg/react` to `custom-provider-icons.tsx` and an entry to the `PROVIDER_ICONS` table
- **THEN** the new provider renders its icon without changes to `ProviderIcon.tsx` resolution logic

### Requirement: SVG icon components use currentColor for monochrome logos

SVG icon components for monochrome providers SHALL use `currentColor` for their fill, allowing the parent `ProviderIcon` to control color via CSS. Multi-color logos (Google) MAY use hardcoded fill colors within the SVG paths. Each SVG component SHALL accept standard SVG props (`width`, `height`, `className`) and render an `<svg>` element with a 24×24 viewBox.

#### Scenario: Monochrome icon inherits color

- **WHEN** `<ProviderIcon provider="openai" size={16} />` renders inside a span with `color: #10A37F`
- **THEN** the OpenAI SVG paths render in #10A37F via `currentColor`

#### Scenario: Multi-color icon uses own palette

- **WHEN** `<ProviderIcon provider="google" size={16} />` renders
- **THEN** the Google "G" renders with its multi-color palette (blue, red, yellow, green) regardless of the parent color
