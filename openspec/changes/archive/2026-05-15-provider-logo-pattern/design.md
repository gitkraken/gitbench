## Context

The GitBench web UI (`gitbench/web/`) has a `ProviderIcon` React component that renders brand logos for AI model providers. It currently uses `@icons-pack/react-simple-icons` (v13.13.0) as its icon source, with an initial-circle fallback for unknown providers.

The problem: simple-icons 13.x uses incorrect logos. Anthropic's icon is the "AI" wordmark, not the asterisk/flower brand mark. OpenAI and DeepSeek aren't in the library at all. The dependency adds ~100KB to the bundle for only 4 used icons.

The solution: drop simple-icons and use first-party custom inline SVGs for every provider. This guarantees logo accuracy, eliminates the dependency, and makes the system trivially extensible.

Provider scope is limited to first-party model builders (companies that train and serve their own frontier models), not proxy/infrastructure services. Ollama and OpenRouter are excluded on this basis.

## Goals / Non-Goals

**Goals:**
- Remove `@icons-pack/react-simple-icons` dependency entirely
- Provide accurate custom inline SVG logos for all 13 providers GitBench currently targets
- Simplify `ProviderIcon` to a single lookup table with one fallback
- Document the process for adding a logo when a new provider is introduced

**Non-Goals:**
- Adding any new npm dependency
- Redesigning the `ProviderIcon` component API or props
- Creating logos for providers GitBench does not yet support
- Pulling logos dynamically from CDN or external URLs
- Logos for proxy/infrastructure services (Ollama, OpenRouter, LiteLLM, etc.)

## Decisions

### Decision 1: Custom inline React SVG components in a single module

All provider logos live as named exports in `gitbench/web/src/lib/custom-provider-icons.ts`. Each is a React functional component accepting `size` (number) and `className` (string) props, rendering an `<svg>` element.

**Rationale:** A single file is the simplest structure for 13 icons. It's easy to scan, easy to edit, and easy to add to. Each component is ~10-20 lines of SVG markup. No build configuration needed — Astro/Vite handles TSX natively.

**Alternatives considered:**
- *Individual `.svg` files* — 13 files to manage, need Vite `?react` transform or `@astrojs/image`
- *Single SVG sprite sheet* — `<use href>` doesn't allow per-icon color overrides easily
- *Keep simple-icons + supplement* — still has wrong logos, still has the dependency

### Decision 2: Provider scope — first-party model builders only

Only companies that train and serve their own frontier models get custom logos. Infrastructure/proxy services (Ollama, OpenRouter) are excluded — they render automatic initial circles. This keeps the icon set focused and prevents bloat.

### Decision 3: Two-tier fallback

The `ProviderIcon` lookup order:
1. `PROVIDER_ICONS` (custom SVG lookup table)
2. Initial-circle fallback (automatic, requires no entry)

**Rationale:** With simple-icons gone, there's only one icon source. The initial-circle fallback is automatic for any provider slug, so adding a new provider with no logo still renders something reasonable.

### Decision 4: Colors via PROVIDER_COLORS, not hardcoded in SVGs

SVG components use `currentColor` for their fill, and `ProviderIcon` passes the color via a wrapping `<span style={{ color }}>`. This keeps color definitions centralized in `provider-colors.ts`.

**Exception:** Multi-color logos (Google's 4-color "G") use hardcoded fill colors in the SVG paths, since `currentColor` can only represent one color.

### Decision 5: Documentation in `docs/agents/provider-logos.md`

Covers:
- Where to add a new logo (`custom-provider-icons.ts`)
- SVG component shape (props interface, `currentColor` usage)
- How to register the icon in `ProviderIcon.tsx`
- What happens if no logo is added (automatic initial circle)

## Risks / Trade-offs

- **Logo accuracy burden**: We own correctness now. Mitigation: use official brand asset pages as sources. SVG markup is auditable in PR.
- **Rebrand drift**: If a provider rebrands, we must update manually. Mitigation: rebrands are rare and loud; custom SVGs are trivial to replace.
- **Bundle size**: 13 custom SVGs total ~6-10KB before gzip vs simple-icons' ~100KB for 4 used icons. Net bundle shrink.

## Migration Plan

1. Remove `@icons-pack/react-simple-icons` from `package.json`
2. Run `npm install` to clean `node_modules`
3. Create `custom-provider-icons.ts` with all 13 provider SVGs
4. Rewrite `ProviderIcon.tsx` to use the new module
5. Build and verify: `npm run build`
6. Rollback: revert commit, reinstall simple-icons — old logos return, no data loss

## Open Questions

None.
