## Why

A width audit of the deployed site (see `docs/audit-web-widths.md`) found
four defects on desktop/tablet widths that hurt readability of charts
and pages, even though every page renders without errors. One defect
turns chart data into scientific notation, one leaves ~40% of the model
detail page empty, one ships the Compare page with no useful
information on first paint, and one lets page content stretch past
~1700px on wide monitors. All four are isolated CSS/React fixes; the
wide-viewport cap is intentionally designed so flipping back to full
bleed later is a single CSS-variable change.

## What Changes

- **`src/components/charts/CostValueChart.tsx`** — replace the recharts
  default y-axis tick formatter with a USD formatter that never emits
  scientific notation (`$0.00e+0` → `$0.01`). Use `Intl.NumberFormat`
  with `notation: "decimal"` and `maximumFractionDigits` sized to the
  value range so very small values still resolve.
- **`src/pages/models/[provider]/[model]/[level].astro`** — restructure
  the two horizontal `section` rows that today leave a ~40% empty
  column between the left metadata block and the right summary block
  (the model-summary header row and the Text-vs-JSON comparison row).
  Collapse each into either a stacked single-column layout at all
  widths, or a `grid-cols-[1fr_2fr]` so the wider block occupies the
  reclaimed space.
- **`src/components/ComparePage.tsx` + `ModelSelector`** — make the
  Compare page default-select the top-two model groups by pass rate on
  first render (and on render with no stored selection) so the
  reliability-delta and overall-pass-rate cards/charts are populated on
  first paint instead of waiting for a user click.
- **`src/styles/global.css`** — introduce `--main-max-width` CSS custom
  property on `:root`, apply `max-width: var(--main-max-width);
  margin-inline: auto;` to `.app-main`. Default value `1440px`. The
  `responsive-sidebar` spec already covers sidebar width; this only
  caps the *content* area at the desktop breakpoint so wide viewports
  (≥1440px) center instead of stretching to 1900+px.

No breaking changes to public URLs, components consumed by other pages,
or data shapes. All changes are local to one or two files each.

## Capabilities

### New Capabilities

_None._ Each fix maps to an existing capability as a delta spec.

### Modified Capabilities

- `cost-value-chart`: add a Requirement that the y-axis tick formatter
  never emits scientific notation and always renders USD with at least
  two significant digits.
- `report-pages`: add a Requirement that the model detail page
  (`/models/[provider]/[model]/[level]`) lays out its metadata and
  comparison blocks without leaving an empty central column at
  desktop/tablet widths.
- `searchable-model-selector`: add a Requirement that when the Compare
  page renders with no persisted selection, the selector defaults to
  the top-two model groups by pass rate (descending) so the page is
  informative on first paint.
- `astro-site`: add a Requirement that `.app-main` is capped at a
  configurable `--main-max-width` (default 1440px) and centered at
  desktop widths ≥960px.

## Impact

- **Files touched**:
  - `gitbench/web/src/components/charts/CostValueChart.tsx`
  - `gitbench/web/src/pages/models/[provider]/[model]/[level].astro`
  - `gitbench/web/src/components/ComparePage.tsx`
  - `gitbench/web/src/components/charts/ModelSelector.tsx` (read only;
    new default-selection helper lives here)
  - `gitbench/web/src/styles/global.css` (new CSS variable + `.app-main`
    rule)
- **Dependencies**: none. No new npm packages.
- **Tests**: existing `pnpm test:api` covers API behavior only; visual
  fixes are not currently unit-tested. A short manual checklist (see
  tasks.md) covers visual verification.
- **Risk**: low. Each change is local; none alters public URLs, the
  data layer, or shared utilities. The `ComparePage` default-selection
  is the only behavior change visible to returning users (their stored
  selection still wins), and the wide-viewport cap is opt-out via the
  CSS variable.
