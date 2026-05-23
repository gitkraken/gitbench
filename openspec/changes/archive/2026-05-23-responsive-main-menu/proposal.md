## Why

The sidebar is 220px of fixed real estate that doesn't adapt to smaller screens. At tablet widths (601–960px) it consumes up to 23% of the viewport with cramped text labels and no way to reclaim that space. At phone widths (≤600px) the nav becomes a horizontal scroll row and the "GitBench by GitKraken" branding text is unconditionally hidden. Both breakpoints need a proper responsive pattern.

## What Changes

- **Tablet (601–960px)**: Sidebar becomes collapsible — toggles between a 220px expanded state (icons + labels) and a ~64px collapsed state (icons only). Default is expanded. Uses a CSS checkbox hack with JS-enhanced `aria-expanded`.
- **Mobile (≤600px)**: Sidebar becomes a sticky top bar with a hamburger toggle. The nav drops down vertically when open. Branding text remains visible down to 380px; only the "by GitKraken" subtitle hides at the narrowest widths.
- **No horizontal scrolling** — nav is always a vertical list in both collapsed states.
- **Both toggles work without JS** — core show/hide uses the CSS checkbox hack (`:checked ~ sibling`). A small JS snippet adds `aria-expanded` for accessibility but is non-essential.
- **Dark, minimal aesthetic preserved** throughout.

## Capabilities

### New Capabilities
- `responsive-sidebar`: Collapsible sidebar at tablet widths (601–960px) and hamburger menu at mobile widths (≤600px), both using CSS checkbox hacks with JS-enhanced ARIA.

### Modified Capabilities
- `astro-site`: The "Static Layout component with sidebar" requirement is expanded to cover responsive behavior at two breakpoints. The sidebar must support collapsed (icon-only) and expanded (icon + label) states, plus a top-bar hamburger mode on mobile.

## Impact

- `gitbench/web/src/components/Sidebar.astro` — add hidden checkbox inputs, hamburger label with three-bar icon, collapse/expand label
- `gitbench/web/src/styles/global.css` — replace existing ≤600px and ≤960px media query blocks with new responsive rules for both breakpoints
- `gitbench/web/src/components/Layout.astro` — may need a `<script>` block for the non-essential JS ARIA enhancement
