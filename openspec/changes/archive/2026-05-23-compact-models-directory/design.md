## Context

The Models index page (`/models`) currently renders each base model inside a `.card` div, with each reasoning level inside a nested `.card` div. The `.card` CSS class applies a gradient background, 2px border, rounded corners, and box shadow — creating heavy visual weight when nested. Info-circle tooltips ("i" badges) appear on every level name and pass-rate badge via the `.has-tooltip::before` pseudo-element. Cost data ($0.xxxx) appears on every level chip. The page serves 23 providers with ~23 base models (1–3 per provider) and 5–6 levels each.

The page is a directory, not a comparison tool. Users come here to find a specific model and click through to its detail page.

## Goals / Non-Goals

**Goals:**
- Reduce vertical space consumed per base model by removing the outer `.card` wrapper
- Replace inner `.card` level chips with a lighter visual treatment (flat background, thin border, no shadow)
- Remove info-circle tooltips from this page
- Drop cost display from level chips
- Maintain all existing link targets and navigation behavior

**Non-Goals:**
- Changing the data model or `results.json` shape
- Changing routing or URL structure
- Redesigning the model detail page (`[provider]/[model]/index.astro`) or fixture gallery (`[provider]/[model]/[level].astro`)
- Adding sorting, filtering, or search
- Creating a reusable `NestedCard` component (scope is this single page)

## Decisions

### Decision 1: Drop outer `.card`, keep provider `<section>` as visual grouping

**Chosen**: Remove the `<div class="card p-5">` wrapper around each base model group. The provider `<section>` with its header already provides grouping. Model names become plain headings.

**Alternatives considered**:
- **Keep outer card but change to lighter variant**: Still creates unnecessary visual boundaries. A directory doesn't need each model in a box.
- **One card per provider wrapping all models**: Groups well but the card border+sizing gets awkward with multiple models. Simpler to just let sections breathe with spacing.

### Decision 2: Compact chip styling

**Chosen**: Inline Tailwind classes on the inner div (currently `.card p-3`):

```
bg-neutral-700 rounded-md border border-[#3E3E3E] p-2
transition-colors hover:border-[var(--color-border-accent)] cursor-pointer
```

No shadow, no gradient. The `bg-neutral-700` resolves to `#404040` — slightly lighter than the current `#272727` card surface but darker than `#333333`. This creates subtle contrast against the page background without feeling like a heavy card.

**Alternatives considered**:
- **`bg-[#333]` as the user suggested**: Slightly lighter than neutral-700. Both work; neutral-700 is a standard Tailwind token and easier to maintain.
- **Dedicated `.model-chip` CSS class**: Cleaner in the template but adds to global.css for a single page. Inline Tailwind is fine for this scope. If we later reuse the style, extract then.
- **Pill layout (inline text badges)**: Too compressed — loses the click-target size needed for touch/mobile.

### Decision 3: Remove info circles, keep `title` attributes

**Chosen**: Remove the `has-tooltip` class from elements. Replace `data-tooltip` with plain `title` attributes. Browser-native tooltips provide basic accessibility without the visual noise of the "i" circle.

**Rationale**: The `has-tooltip::before` pseudo-element generates a visible "i" circle on every data point. On this directory page, the tooltip content ("Percentage of 204 Git fixtures...") is repetitive and users either know what pass rate means or they'll see the explanation in the intro paragraph. If they don't, they'll see it on the detail page.

### Decision 4: Drop cost from level chips

**Chosen**: Remove the cost line (`${l.total_cost_usd.toFixed(4)}`) from the inner chip div.

**Rationale**: Costs range $0.001–$0.05 with 4 decimal places. At directory level this is noise — it doesn't help someone find a model. Cost is still available on the model detail page and in comparison views.

### Decision 5: Tighten provider section spacing

**Chosen**: Change `mb-10` to `mb-6` on provider `<section>` elements. Change gap between base model groups from `gap-4` to `gap-3`.

This further reduces vertical space without making sections feel cramped.

## Risks / Trade-offs

- **Click target size on mobile**: `p-2` (8px padding) plus content creates roughly 48px+ tall chips, which meets minimum touch target guidelines. If testing shows issues, increase to `p-2.5`.
- **Loss of visual hierarchy**: Without the outer card, model name + its chips could blend into the next model. Mitigated by keeping model name as a `font-semibold` heading with spacing below.
- **Color contrast**: `bg-neutral-700` (#404040) with white text meets WCAG AA contrast. Border `#3E3E3E` on #1C1C1C background also passes.
