# Adding a Provider Logo

When a new model provider is added to GitBench, follow this guide to give it a brand logo in the web UI.

## Decision: Does this provider need a custom logo?

Only **first-party model builders** (companies that train and serve their own frontier models) get custom logos. Infrastructure/proxy services (Ollama, OpenRouter, LiteLLM, etc.) use the automatic **colored initial circle** fallback — no code needed.

If the provider qualifies, proceed below.

## Two-tier fallback

The `ProviderIcon` component resolves logos in this order:

1. **Custom SVG** in `PROVIDER_ICONS` lookup table → renders the brand mark
2. **Automatic initial circle** → colored circle with first letter (happens automatically for any unmapped provider)

## Step 1: Create the SVG component

Open `web/src/lib/custom-provider-icons.ts`.

Add a new exported function component following this pattern for **monochrome** logos:

```tsx
export function NewProviderIcon({ size = 24, className, ...rest }: ProviderSvgProps) {
  return (
    <svg {...svgProps(size, className)} {...rest}>
      <path d="..." fill="currentColor" />
    </svg>
  );
}
```

Key conventions:
- Use `currentColor` for fill — the parent `ProviderIcon` controls color via `PROVIDER_COLORS`
- Keep the `viewBox="0 0 24 24"` (handled by `svgProps` helper)
- Keep paths simple — these render as small as 12×12 pixels
- Add a JSDoc comment identifying the provider and logo source

For **multi-color** logos (rare — currently only Google), hardcode the palette in the SVG paths instead of using `currentColor`.

## Step 2: Register in the lookup table

At the bottom of the same file, add an entry to `PROVIDER_ICONS`:

```tsx
export const PROVIDER_ICONS: Record<string, React.ComponentType<ProviderSvgProps>> = {
  // ... existing entries ...
  newprovider: NewProviderIcon,
};
```

The key must be the **lowercase provider slug** — this matches what `ProviderIcon` receives in its `provider` prop.

## Step 3: Add a palette color

Open `web/src/lib/provider-colors.ts`.

Add an entry to `PROVIDER_COLORS`:

```tsx
export const PROVIDER_COLORS: Record<string, string> = {
  // ... existing entries ...
  newprovider: '#HEXCOLOR',
};
```

Pick a color that represents the brand and is visible on dark backgrounds. Existing entries are good reference.

## Done

That's it. Rebuild with `npm run build` and the new provider will render its logo. No changes to `ProviderIcon.tsx` are needed.

## What if I skip this?

If no logo is added, the provider still renders — as a colored circle with its first letter. This is the automatic fallback and requires zero code changes. It's fine for infrastructure services or providers you haven't prioritized yet.
