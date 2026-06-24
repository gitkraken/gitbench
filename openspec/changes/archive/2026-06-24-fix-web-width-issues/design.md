## Context

Width audit (`docs/audit-web-widths.md`) found four defects that hurt
the dashboard's readability on desktop and tablet viewports. Each is
isolated to one or two files. None touches the data layer, public
URLs, or shared utilities consumed outside the immediate fix site.

The four defects and where they live in the codebase today:

1. **Cost chart y-axis ticks** — `formatCost()` in
   `src/components/charts/CostValueChart.tsx:20-24` falls through to
   `value.toExponential(1)` whenever `value < 0.0001`. Axis tick
   value `0` therefore renders as `$0.0e+0`. Recharts passes raw tick
   values to the formatter, so this hits on every chart render.

2. **Level page dead column** — the model-summary header section and
   the Text-vs-JSON comparison section in
   `src/pages/models/[provider]/[model]/[level].astro` each lay out a
   left block (~30%) and a right block (~30%) with no rule binding
   them, leaving ~40% empty whitespace between. Both sections use the
   same pattern; both need the same fix.

3. **Compare page first paint** —
   `src/components/ComparePage.tsx` initializes its selected-model
   state from `useSyncedModelSelection(data)`, which returns an empty
   selection when no localStorage value exists. The page renders
   "1 selected" / no charts until the user clicks a model. Returning
   users with a stored selection are unaffected; only the cold-load
   path is broken.

4. **No content-area cap on wide viewports** —
   `src/styles/global.css:159-166` defines `.app-main` with
   `margin-left: var(--sidebar-width); flex: 1; min-width: 0;` and no
   `max-width`. On a 1920px monitor, content stretches to ~1700px.
   The `responsive-sidebar` spec covers sidebar width only; nothing
   caps `.app-main`.

## Goals / Non-Goals

**Goals:**

- All four defects resolved with the minimum change footprint.
- Wide-viewport cap uses a single CSS variable so flipping to
  full-bleed later is one line (`--main-max-width: none`).
- No public URL changes, no data-shape changes, no new dependencies.
- Behavior remains backward-compatible for returning users (Compare
  page still honors a stored selection if one exists).

**Non-Goals:**

- Mobile / narrow-viewport fixes (≤600px). Parked per round-1
  decision #1; addressed in a follow-up audit cycle.
- Redesigning the Compare page beyond initial selection.
- Replacing Recharts with another library.
- Changing the heatmap, the history chart, or any other chart
  component outside the four listed fixes.

## Decisions

### D1 — Cost chart formatter: use a real USD formatter

Replace the hand-rolled `formatCost()` with `Intl.NumberFormat`
configured for USD-style decimals (`style: "decimal"`,
`minimumFractionDigits: 0`, `maximumFractionDigits` set to a value
derived from the magnitude so the smallest tick stays readable):

```ts
const costFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 0,
  maximumFractionDigits: 4,
});

function formatCost(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return costFormatter.format(value);
}
```

`Intl.NumberFormat` never emits scientific notation. Four fraction
digits is enough for the smallest seen values (`$0.0052`). Three
fraction digits is acceptable for `≥$0.01` because the formatter
trims trailing zeros automatically.

The `formatCost` export stays in `CostValueChart.tsx` so the change is
local. It is also reused by the tooltip renderer.

**Alternatives considered:**

- Fix the `value < 0.0001` guard to handle `value === 0` explicitly.
  Doesn't address the underlying issue (any small positive number
  would still get a `toExponential` rendering if the threshold were
  changed).
- Use `d3-format` (`d3.format("$.4")`). Adds a dependency and brings
  locale handling baggage.
- Switch the y-axis to `LogAxis`. Changes the visual model
  meaningfully; not approved.

### D2 — Level page sections: collapse to a stacked column at desktop

Replace each `grid-cols-[A_B]` (with whitespace between) with a
single stacked column inside the existing `.card` wrapper. The
"Reliability by Benchmark" table is the only data-dense block; it
moves above the text-vs-JSON comparison card so the visual reading
order is metadata → reliability table → comparison delta. At
tablet widths the layout is already single-column because of the
existing `flex-wrap`, so this fix only changes desktop.

Concretely:

- Section A (`section-label > "Reliability by Benchmark"`) keeps its
  right-hand table card but the table moves to its own `.card`
  below the metadata, not alongside.
- Section B (`section-label > "Text vs JSON Schema Comparison"`)
  becomes a single full-width `.card` containing the `+7/-66/119/12`
  summary tiles + the benchmark delta table.

**Alternatives considered:**

- `grid-cols-[1fr_2fr]` to bias the layout. Looks better in
  isolation but the right block already wants full width; this
  postpones the same problem.
- Make the empty column into a TOC or "next steps" panel. Out of
  scope for a width fix.
- A two-column layout where the LEFT is wider and the RIGHT is a
  sidebar. Same problem: too much empty space on first inspection.

### D3 — Compare page default selection: top two by pass rate

Add a single helper in `ModelSelector.tsx` (or a co-located module):

```ts
export function defaultSelectionForCompare(
  data: GitBenchData,
): string[] {
  // Returns provider/base-model group ids, sorted by group pass_at_k
  // desc, top two. Skips groups without a measurable pass rate.
}
```

`ComparePage.tsx` calls it when initializing `selectedGroups` from
`useSyncedModelSelection`, only when the hook returns an empty
array AND no stored selection is being restored. Returning users
with a stored selection keep their selection (existing behavior).

**Alternatives considered:**

- Default-select ALL model groups. The chart becomes unreadable
  with more than ~3 series.
- Default-select the first two alphabetically. Doesn't match user
  intent ("who's best?"); pass-rate ordering is more useful.
- Defer to a server-side default. The page is static; client-side
  default is the only option without changing the data layer.

### D4 — `.app-main` cap via CSS custom property

Add to `src/styles/global.css`:

```css
:root {
  --main-max-width: 1440px;
}

.app-main {
  /* …existing rules… */
  max-width: var(--main-max-width);
  margin-inline: auto;
}
```

At desktop (`> 960px`) the `.app-main` is centered with a 1440px
ceiling. Tablet and mobile retain their existing full-bleed
behavior. Flipping to full-bleed later is changing the var to
`none` (or removing the rule).

The `responsive-sidebar` spec already handles sidebar width, so
`.app-main`'s left margin at desktop is still `var(--sidebar-width)`.
The `max-width` applies to the box but the sidebar is `position:
fixed`, so it overlaps nothing — the main content area simply
centers within whatever space remains after the fixed sidebar.

**Alternatives considered:**

- `max-width` on the `.page-content` inside `.app-main` instead.
  Would cap the body padding rhythm; feels less surgical and breaks
  the section-label `::after` rule's stretch behavior at the cap.
- `clamp(0, 1440px, 100vw - 220px)`. More clever but harder to flip
  to full-bleed without rewriting.

## Risks / Trade-offs

- [Cost formatter] → Recharts may pass `undefined` ticks in edge
  cases. Mitigated by `Number.isFinite` guard.
- [Level page stacking] → Section reading order changes for desktop
  users. Mitigated by keeping the metadata header visible above the
  fold; the table that moves below already lives below the fold
  today because of the empty column.
- [Compare default selection] → A returning user who previously
  cleared their stored selection sees two auto-selected models. This
  is intentional but should be communicated in the existing
  "Compare" intro blurb (already says "Pick 2+ models to compare
  side by side").
- [.app-main cap] → On a 1920px monitor the content now sits in a
  centered 1440px block with ~240px gutters on each side. Users
  used to the stretched layout may notice; this is the requested
  behavior. Easy to revert via the var.
- [CSS variable cascade] → The new `--main-max-width` is on
  `:root`. If any other component scopes its own `:root` rules
  (none in the current codebase), the var could be overridden.
  Verified no other `:root` rule defines `--main-max-width`.

## Migration Plan

No migration. All four fixes are forward-compatible:

- Cost formatter: only changes a presentation string.
- Level page stacking: only changes layout.
- Compare default: only triggers on cold load with no stored
  selection.
- `.app-main` cap: only kicks in at viewport widths ≥ 1440px; below
  that width the content fills the available space as before.

Rollback for each is a single git revert.

## Open Questions

- _None blocking._ All four were explicitly approved in the audit
  round-1 decisions.
- Future: should `--main-max-width` move from a CSS var into a
  Tailwind theme token so utility classes (`max-w-app-main`) can
  opt child elements into the same cap? Out of scope here; revisit
  if/when any nested element needs to inherit the cap.
