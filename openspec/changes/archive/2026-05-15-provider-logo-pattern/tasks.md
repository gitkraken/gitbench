## 1. Remove simple-icons dependency

- [x] 1.1 Remove `@icons-pack/react-simple-icons` from `gitbench/web/package.json` dependencies
- [x] 1.2 Run `npm install` in `gitbench/web/` to clean lockfile and node_modules

## 2. Create custom SVG icons for all 13 providers

- [x] 2.1 Create `gitbench/web/src/lib/custom-provider-icons.ts` with JSDoc header explaining its purpose
- [x] 2.2 Add `AnthropicIcon` — asterisk/flower brand mark, `currentColor`
- [x] 2.3 Add `OpenAIIcon` — interlocking hexagon/circle mark, `currentColor`
- [x] 2.4 Add `GoogleIcon` — multi-color "G" mark, hardcoded palette
- [x] 2.5 Add `MetaIcon` — infinity-loop "M" mark, `currentColor`
- [x] 2.6 Add `MistralIcon` — stylized "M" mark, `currentColor`
- [x] 2.7 Add `DeepSeekIcon` — whale/circle mark, `currentColor`
- [x] 2.8 Add `MinimaxIcon` — stylized mark, `currentColor`
- [x] 2.9 Add `XAIIcon` — X mark for xAI/Grok, `currentColor`
- [x] 2.10 Add `MoonshotIcon` — Kimi brand mark, `currentColor`
- [x] 2.11 Add `ZAIIcon` — 01.AI / Yi brand mark, `currentColor`
- [x] 2.12 Add `QwenIcon` — Alibaba Qwen brand mark, `currentColor`
- [x] 2.13 Add `CohereIcon` — stylized "C" mark, `currentColor`
- [x] 2.14 Add `PerplexityIcon` — stylized "P" mark, `currentColor`
- [x] 2.15 Export `PROVIDER_ICONS` lookup table mapping all provider slugs to their icon components

## 3. Rewrite ProviderIcon to use custom SVGs

- [x] 3.1 Remove all simple-icons imports and `PROVIDER_ICON_MAP` from `ProviderIcon.tsx`
- [x] 3.2 Import `PROVIDER_ICONS` from `custom-provider-icons.ts`
- [x] 3.3 Replace dual-map lookup with single `PROVIDER_ICONS` check → initial-circle fallback
- [x] 3.4 Apply background-circle visibility enhancement (size ≤ 14) to custom SVG renders
- [x] 3.5 Apply `PROVIDER_COLORS` via wrapping span `style={{ color }}` for monochrome icons

## 4. Document the logo pattern

- [x] 4.1 Create `docs/agents/provider-logos.md` with step-by-step instructions for adding provider logos
- [x] 4.2 Include code snippets for SVG component structure and `PROVIDER_ICONS` registration
- [x] 4.3 Document `currentColor` convention and first-party-only scope rule

## 5. Verify

- [x] 5.1 Run `npm run build` in `gitbench/web/` — build must succeed with no warnings
- [x] 5.2 Verify all 13 providers render correct logos in dev mode (`npm run dev`)
- [x] 5.3 Verify an unmapped provider (e.g., `ollama`) still renders initial-circle fallback
