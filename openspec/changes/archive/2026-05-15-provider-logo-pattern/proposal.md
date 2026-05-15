## Why

The `ProviderIcon` component relies on `@icons-pack/react-simple-icons` for brand logos, but the library uses incorrect logos for key providers (e.g., Anthropic's "AI" mark instead of its asterisk/flower brand mark, and OpenAI/DeepSeek aren't available at all). Several providers render as generic colored-initial circles. Additionally, there is no documented pattern for adding logos when a new provider is introduced. This change replaces simple-icons with first-party custom SVGs, fills gaps, and codifies the pattern so future provider additions are trivial.

## What Changes

- **BREAKING**: Remove `@icons-pack/react-simple-icons` dependency from `gitbench/web/package.json`
- Replace all provider logos with custom inline React SVG components in a single `custom-provider-icons.ts` module
- Simplify `ProviderIcon` to a single two-tier fallback: custom SVG → colored initial circle
- Add proper logos for 13 providers: Anthropic, OpenAI, Google, Meta, Mistral, DeepSeek, Minimax, xAI, Moonshot, z.ai (01.AI), Qwen, Cohere, Perplexity
- Remove Ollama and OpenRouter (secondary infrastructure, not primary model providers worth logo real estate)
- Document a clear, step-by-step pattern in `docs/agents/provider-logos.md` for adding logos when new providers are introduced

## Capabilities

### New Capabilities
- `provider-logo-pattern`: A documented, repeatable process for adding a brand logo when a new model provider is introduced to GitBench, centered on custom inline SVGs.

### Modified Capabilities
- `provider-brand-icons`: Replace the simple-icons-based implementation with a custom SVG module. All existing requirements around icon rendering, sizing, background circles, and color behavior are preserved — only the icon source and provider list changes.

## Impact

- **Affected code**: `gitbench/web/src/components/ProviderIcon.tsx` (simplified), new file `gitbench/web/src/lib/custom-provider-icons.ts` (all custom SVGs)
- **Affected deps**: remove `@icons-pack/react-simple-icons` from `gitbench/web/package.json`
- **Affected docs**: new file `docs/agents/provider-logos.md` (pattern documentation)
