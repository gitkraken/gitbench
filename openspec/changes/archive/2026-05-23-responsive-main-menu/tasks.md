## 1. Sidebar markup changes

- [x] 1.1 Add hidden `#sidebar-collapse-toggle` checkbox input to `Sidebar.astro` for tablet collapse/expand control
- [x] 1.2 Add hidden `#menu-toggle` checkbox input to `Sidebar.astro` for mobile hamburger control
- [x] 1.3 Add collapse/expand `<label>` with chevron icon at bottom of sidebar (visible only at 601–960px)
- [x] 1.4 Add hamburger `<label>` with three `<span>` bars inside `.sidebar-header` (visible only at ≤600px)

## 2. Tablet collapsible sidebar CSS (601–960px)

- [x] 2.1 Add CSS for `.sidebar-collapse-btn` visibility (hidden above 960px and below 600px, visible in between)
- [x] 2.2 Add `#sidebar-collapse-toggle:checked ~ .sidebar-nav` rule to hide labels and shrink sidebar to ~64px
- [x] 2.3 Add `#sidebar-collapse-toggle:checked ~ .app-main` margin-left adjustment to ~64px (or use a class on `.app-sidebar`)
- [x] 2.4 Add `#sidebar-collapse-toggle:checked` rule to hide `.sidebar-product` text in collapsed state
- [x] 2.5 Add `.sidebar-link` icon-only styling when collapsed (center icons, remove text)

## 3. Mobile hamburger menu CSS (≤600px)

- [x] 3.1 Replace existing ≤600px media query: remove horizontal nav row, make `.sidebar-nav` a vertical flex column
- [x] 3.2 Add `.sidebar-nav` max-height transition (0 → 400px) with `overflow: hidden` triggered by `#menu-toggle:checked`
- [x] 3.3 Add hamburger bar → X animation (bar 1 rotate +45°, bar 2 opacity 0, bar 3 rotate -45°)
- [x] 3.4 Add `.sidebar-header` flex layout for mobile: brand lockup left, hamburger right
- [x] 3.5 Add `padding: 0` to `.sidebar-nav` in collapsed state, restore padding when expanded

## 4. Branding text progressive hiding

- [x] 4.1 Add `@media (max-width: 380px)` rule to hide `.sidebar-product-subtitle`
- [x] 4.2 Add `@media (max-width: 320px)` rule to hide `.sidebar-product-title`

## 5. ARIA enhancement script

- [x] 5.1 Add inline `<script>` in `Layout.astro` to listen for `change` on both checkbox inputs
- [x] 5.2 Set `aria-expanded` on the checkbox and the adjacent `.sidebar-nav` based on `checked` state

## 6. Verification

- [x] 6.1 Verify desktop (>960px): sidebar fixed at 220px, no toggle buttons visible
- [x] 6.2 Verify tablet (768px): sidebar collapsible, collapse button works, collapsed state shows icons only
- [x] 6.3 Verify mobile (375px): hamburger visible, opens vertical nav, animates to X, branding visible
- [x] 6.4 Verify very narrow (320px): only logo visible, hamburger still works
- [x] 6.5 Verify JavaScript disabled: both toggles work CSS-only
- [x] 6.6 Verify JavaScript enabled: `aria-expanded` attributes update correctly
- [x] 6.7 Verify all 7 nav links are functional at each breakpoint
