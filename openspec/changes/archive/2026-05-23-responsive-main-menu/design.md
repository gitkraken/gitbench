## Context

The GitBench site uses Astro with a `Layout.astro` shell and a `Sidebar.astro` component. The sidebar is currently 220px fixed, narrowing to 180px at ≤960px, then converting to a sticky top bar with horizontal-scroll nav at ≤600px. The branding text ("GitBench by GitKraken") is hidden at ≤600px. The horizontal-scroll nav is hard to use with 7 items. There is no way to reclaim sidebar space on tablets.

## Goals / Non-Goals

**Goals:**
- Tablet (601–960px): Sidebar becomes collapsible — toggle between expanded (220px, labels visible) and collapsed (~64px, icons only). Default is expanded.
- Mobile (≤600px): Sidebar becomes sticky top bar with hamburger toggle. Nav drops down vertically. Branding visible down to 380px.
- Both toggles work CSS-only (checkbox hack). JS adds `aria-expanded` as a non-essential enhancement.
- No horizontal scrolling on any breakpoint.
- Dark, minimal aesthetic preserved — no new dependencies.

**Non-Goals:**
- Changing the 960px or 600px breakpoint thresholds.
- Animating the tablet sidebar width (instant snap, not a transition — keeps it simple).
- Overlay/drawer pattern on mobile (nav pushes content down).
- Auto-close on link click (requires JS; user taps hamburger to close).
- Touch-drag or swipe gestures.
- Changing any page content or chart components.

## Decisions

### 1. Two independent checkbox hacks, not one

We use separate checkboxes for tablet collapse and mobile hamburger. They target different elements and media queries so there's no conflict:

- `#sidebar-collapse-toggle` — visible only at 601–960px, toggles `.sidebar-nav` between expanded/collapsed
- `#menu-toggle` — visible only at ≤600px, toggles `.sidebar-nav` open/closed below the header

A single checkbox would need to serve two very different layouts, making the CSS fragile and hard to read.

**Alternatives considered:**
- Single checkbox + media-query-dependent behavior: CSS gets tangled, selector specificity wars.
- JS-only solution: Breaks without JS, adds complexity.
- `<details>` element: Not stylable enough for the hamburger → X animation.

### 2. `max-height` transition for nav open/close

The `.sidebar-nav` transitions `max-height: 0` → `max-height: 400px` with `overflow: hidden`. This is the most reliable CSS-only height animation — `grid-template-rows: 0fr → 1fr` would require an inner wrapper div.

Trade-off: Closing has a slight visual delay because it animates from 400px, not the actual computed height. At 7 items this is imperceptible (~80ms difference).

**Alternatives considered:**
- `grid-template-rows` trick: Requires inner wrapper, cleaner animation curve, but more HTML change.
- `transform: scaleY(0)`: Visually compresses text, looks bad.
- `opacity` + `pointer-events`: No height animation, layout gap remains.

### 3. Tablet sidebar snaps (no width transition)

The sidebar switches instantly between 220px and 64px. Animating `width` would require transitioning from `auto` (impossible in CSS) or using a fixed 220px width with `overflow: hidden`, which complicates the icon-only layout.

**Alternatives considered:**
- Width transition: Needs fixed width on expanded state + overflow hidden, icons would need `white-space: nowrap` and would look clipped during transition.
- `transform: translateX`: Would overlap content, needs z-index management.

### 4. Mobile nav pushes content (not overlay)

The nav expands below the sticky header, pushing `<main>` content down. No z-index layering, no backdrop, no scroll-lock needed.

**Alternatives considered:**
- Absolute-positioned overlay: Cleaner UX (content doesn't jump), but requires z-index management with the chart library and `position: absolute` relative to a positioned ancestor.
- Slide-in drawer from left: Same z-index concerns, plus the drawer feels wrong for a top bar.

### 5. Branding visibility: subtitle hides at ≤380px, title at ≤320px

Using `@media (max-width: 380px)` and `(max-width: 320px)` to progressively hide branding text. The logo (gitkraken-icon.svg) is always visible.

| Width | Logo | "GitBench" | "by GitKraken" |
|-------|------|------------|----------------|
| >600px | ✅ | ✅ | ✅ |
| 381–600px | ✅ | ✅ | ✅ |
| 321–380px | ✅ | ✅ | ❌ |
| ≤320px | ✅ | ❌ | ❌ |

### 6. JS enhancement: `aria-expanded` only

A small inline `<script>` in `Layout.astro` listens for `change` on both checkbox inputs and updates `aria-expanded` on the associated nav. The menu works without JS — `aria-expanded` is purely additive for screen readers.

```js
document.querySelectorAll('.menu-toggle').forEach(input => {
  input.addEventListener('change', () => {
    const nav = input.parentElement.querySelector('.sidebar-nav');
    input.setAttribute('aria-expanded', input.checked);
    if (nav) nav.setAttribute('aria-expanded', input.checked);
  });
});
```

## Risks / Trade-offs

- **[No auto-close on link click]** → User must tap hamburger/collapse button again to close. Acceptable for 7 items. Could be added later with JS if it becomes a pain point.
- **[`max-height: 400px` magic number]** → If nav items are added later, the max-height must be bumped or the last items get clipped. A comment in CSS will note this.
- **[Two checkboxes in DOM]** → Both are `display: none` on desktop, but they're always in the markup. Negligible — it's two hidden inputs.
- **[Tablet collapse button discoverability]** → Users may not realize the sidebar is collapsible. The collapse button (chevron icon) sits at the bottom of the sidebar, similar to how VS Code and other tools handle it.
