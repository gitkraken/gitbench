# Web UI Width Issues — Audit Checklist

Crawled every page at desktop (1440×900), wide (1920×1080), tablet (800×1100),
and mobile (390×1200) viewports. Screenshots: `/tmp/gitbench-crawl/`.

Stack: Astro 6 + React 19, Tailwind v4, fixed 220px sidebar, sidebar
collapses to 64px icons ≤960px, sticky mobile header ≤600px.
Global layout: `web/src/styles/global.css:138-166`.

## Decisions (round 1)

| # | Topic              | Decision                                                            |
|---|--------------------|---------------------------------------------------------------------|
| 1 | Mobile             | **Ignore for now.** Park all mobile-only items under `~~mobile~~`.  |
| 2 | Wide viewport      | **Cap `.app-main`** with a CSS var so flipping to full-width later is a one-line change. |
| 3 | Compare page       | **Default-select top 2 models** so the chart is useful on first load. |
| 4 | History chart      | **Leave the line chart alone.** Only fix the *width* of the chart container if it's clipping. |

These decisions shift the priority of several items below. Anything marked
`~~mobile~~` is deferred, not closed.

Each item has a priority, the file/line where the offending layout lives,
and a one-line description. Approve items individually before any change
becomes a proposal.

---

## P0 — Critical (visible breakage)

- [ ] ~~**Mobile horizontal overflow on every page**~~ **(DEFERRED per decision #1)**
  Sidebar becomes sticky top-bar ≤600px, but page content has no
  `overflow-x: hidden` and chart components force their own intrinsic
  width. Visible at `screenshots/_home_mobile.png`,
  `_home_mobile.png` (text clipped on right, chart bars cut off).
  Likely culprit: `ResponsiveContainer` width="100%" inheriting a parent
  that itself has no `min-w-0` somewhere up the chain.
  Files: `web/src/styles/global.css:323-326` (`.page-content`),
  all chart components in `src/components/charts/`.

- [ ] **Cost per Full Run chart: y-axis shows "$0.00e+0"**
  Scientific notation when the value is very small (e.g. $0.005160).
  Confusing default. Tick formatter needs `Intl.NumberFormat` or a
  custom `toFixed(4)` instead of recharts' default.
  Visible at `screenshots/full/_home_tall.png` (Cost Per Full Run card).
  File: `src/components/charts/CostValueChart.tsx`.

- [ ] **Level page (`/[provider]/[model]/[level]`) has a giant dead column**
  The model summary header row + the Text-vs-JSON comparison row each
  put the left block (~30%) and right block (~30%) with ~40% empty in
  between. Looks like an unfinished `grid-cols-2` that should be a
  side-by-side `grid-cols-[1fr_2fr]` or stacked.
  Visible at `screenshots/full/_level_tall.png`.
  File: `src/pages/models/[provider]/[model]/[level].astro` (search
  for `section-label` — there are three in the file).

---

## P1 — High (clearly broken, not blocking)

- [ ] **Compare page: model labels overflow into chart area**
  Vertical bar chart shows full IDs like
  "deepseek/deepseek-v4-flash:high" — they run into the bar geometry.
  `maxWidth: 118` in chart-ui limits but label content is longer.
  Visible at `screenshots/_compare.png`.
  File: `src/components/charts/grouped-chart-ui.tsx:197-206`
  (`maxWidth: 118`).

- [ ] **Compare page: default-select top 2 models on first load**
  Currently shows "1 selected" until the user clicks, leaving the
  page useless on first paint. **Approved per decision #3.**
  Visible at `screenshots/_compare.png`.
  File: `src/components/charts/ModelSelector.tsx` +
  `src/components/ComparePage.tsx` (initial state).

- [ ] **Benchmark Matrix heatmap column headers wrap awkwardly**
  Long model IDs like `deepseek/deepseek-v4-flash:none` wrap to 2 lines
  and visually compete with row labels. Truncate or rotate.
  Visible at `screenshots/full/_home_extra_tall.png` (bottom card).
  File: `src/components/charts/BenchmarkHeatmap.tsx`.

- [ ] **Model Summary bar chart truncates every x-axis label to "~"**
  `truncateName(name, 16)` makes "deepseek-v4-flash" → "deepseek-…",
  "devstral-2512" → "devstral-…", "nemotron-3-nano-30b-a3b" → "nemotron~".
  The provider icon is right there; the text is what gets dropped.
  Increase `maxLen` or rely on icon + tooltip.
  Visible at `screenshots/_home.png`, `_compare.png`.
  File: `src/components/charts/grouped-chart-ui.tsx:30-33`.

- [ ] **Fixture detail (`/fixtures/[benchmark]/[fixture]`): baseline
  repo commands rendered as 16 separate cards**
  Each git command gets its own bordered card with a line number. The
  data is contiguous — render as one `<pre>` block with line numbers.
  Visible at `screenshots/full/_fixture_tall.png` (lines 01–16).
  File: `src/pages/fixtures/[benchmark]/[fixture].astro` (Baseline
  Repository section).

- [ ] **No max-width on `.app-main` — wide viewports stretch content**
  **Approved per decision #2.** Add a `--main-max-width` CSS var
  (default e.g. `1440px`) on `.app-main` with `margin: 0 auto`, so
  flipping to full-width later is changing the var. Methodology and
  History tables both look stretched on 1920px.
  Visible at `screenshots/_home_wide.png`.
  File: `src/styles/global.css:159-166`.

---

## P2 — Medium (works but ugly / wasteful)

- [ ] **Page title (h1) is 49px / line-height 61px and wraps to two
  lines on long paths**
  "Deepseek / deepseek-v4-flash / high" overflows on tablet (~800px)
  and wraps awkwardly. Either clamp with a `min-width: 0` breadcrumb
  or shrink at tablet.
  Visible at `screenshots/_models_tablet.png`,
  `dynamic/_models_deepseek_deepseek-v4-flash_high.png`.
  File: `src/styles/global.css:307-312` (`.page-header h1`),
  Layout: `src/components/Layout.astro`.

- [ ] **Methodology page: card spans full width but text is
  `max-w-3xl`**
  Result: ~600px wide text block centered inside a 1200px card,
  leaving ~600px of dead space. Either drop the card and use the
  text width, or pull the card narrower with `max-w-3xl` on `.card`.
  Visible at `screenshots/_methodology.png`.
  Files: `src/pages/methodology.astro:10`,
  `src/styles/global.css:396-402`.

- [ ] **Quadrant chart: Y-axis title "Intelligence (Pass Rate)" sits
  INSIDE the plot area**
  Rotated label takes up chart space and overlaps the topmost y-tick.
  Move outside via recharts `label` prop on `YAxis` or a positioned
  div.
  Visible at `screenshots/full/_home_tall.png` (Quadrant Comparison
  card).
  File: `src/components/charts/QuadrantComparisonChart.tsx`.

- [ ] **Quadrant chart: tick labels `61.6%` show a stray `0.009` value**
  Looks like an axis-domain bug where the lower bound leaks through.
  Visible at `screenshots/full/_home_tall.png`.
  File: `src/components/charts/QuadrantComparisonChart.tsx`.

- [ ] **Models index cards: provider icon at size 22 + base-model name
  uses very different type scales**
  Provider header (Deepseek, Mistralai, …) is `text-lg font-bold`,
  base-model (deepseek-v4-flash) is `text-base font-semibold`,
  reasoning-level label (none / high) is `text-xs font-mono`. The
  three weights look unrelated. Pick one scale ramp.
  Visible at `screenshots/_models.png`.
  File: `src/pages/models/index.astro:36-92`.

- [ ] **History "Evaluation Timeline" table: git SHAs (40 chars) eat
  the right half of every row**
  Visible at `screenshots/_history.png`. Truncate to 7-char SHA +
  copy button, or `font-mono text-[0.65rem]`.
  File: `src/pages/history.astro`.

- [ ] **Compare page reliability cards: tiny full model ID under each
  number is unreadable (`text-[0.55rem]` opacity-50)**
  "deepseek/deepseek-v4-flash:high" runs past the card width.
  Visible at `screenshots/_compare.png`.
  File: `src/components/ComparePage.tsx:184-223`.

- [ ] **Explore tag list: 301 tags wrap into many rows on tablet**
  At 800px the popular tag row is fine (10 tags), but if the user
  clicks "Show all 301 tags" the wrap becomes chaotic.
  Visible at `screenshots/_explore.png`,
  `_explore_tablet.png`.
  File: `src/pages/explore.astro:50-89`.

---

## P3 — Low (cosmetic / consistency)

- [ ] **Section labels are inline pill + horizontal rule; rule
  length varies by available width and looks unstable on tablet**
  `flex: 1` `::after` on `.section-label` creates a rule that
  stretches to fill. At 800px with the model-output-controls row
  it can hit the right column at a weird spot.
  File: `src/styles/global.css:367-394`.

- [ ] **History chart container: verify width doesn't clip** *(per decision #4)*
  Don't redesign the chart; only ensure the `<ResponsiveContainer>`
  wrapper has enough horizontal room on desktop. If it already does,
  close as no-op.
  File: `src/components/charts/TimeSeriesChart.tsx`,
  `src/pages/history.astro`.

- [ ] **Compare page table header "more reliable" repeats twice with
  different colors**
  Both `aMore` and `bMore` use the same label "More reliable". The
  color differentiates but the label doesn't. Add "(model A)" /
  "(model B)" or move the model name above.
  File: `src/components/ComparePage.tsx:185-206`.

- [ ] **Per-fixture gallery cards (level page) have labels "TOKENS
  / INPUT / TOTAL OUTPUT / REASONING WITHIN OUTPUT" that wrap into
  4 narrow columns**
  At 320px card width, the labels wrap. They should be a single
  line each, or use icons. **The user opened `FixtureCardBoth.astro`
  which is the same component family — confirm if it's Both or the
  single-output variant that needs the fix.**
  Visible at `screenshots/full/_level_tall.png` (Fixture Gallery).
  File: `src/components/fixtures/FixtureCard.astro` and/or
  `src/components/fixtures/FixtureCardBoth.astro`.

- [ ] **Heatmap cells: numeric value + "Stable pass" / "Flaky" label
  repeats in every cell — busy when scannable "what's broken?"**
  File: `src/components/charts/BenchmarkHeatmap.tsx`.

- [ ] **Sidebar brand lockup: `subtitle "by GitKraken"` truncates
  oddly at narrow tablet (180px)**
  Visible at `screenshots/_home_tablet.png` (subtitle looks fine,
  but `gap: 0.8rem` could compress).
  File: `src/styles/global.css:174-207`.

---

## Pages crawled (so we know what's covered)

| Route                          | Desktop | Tablet | Mobile | Wide |
|--------------------------------|---------|--------|--------|------|
| `/`                            | ✓       | ✓      | ✓      | ✓    |
| `/models`                      | ✓       | ✓      |        |      |
| `/models/[provider]/[model]/`  | ✓       |        |        |      |
| `/models/[provider]/[model]/[level]/` | ✓ (tall) |   |        |      |
| `/benchmarks`                  | ✓       |        |        |      |
| `/benchmarks/[name]`           | ✓       |        |        |      |
| `/explore`                     | ✓       | ✓      |        |      |
| `/compare`                     | ✓       |        |        |      |
| `/history`                     | ✓       |        |        |      |
| `/methodology`                 | ✓       |        |        |      |
| `/fixtures/[benchmark]/[fixture]` | ✓ (tall) |    |        |      |

Not yet crawled: `/fixtures/[benchmark]/[benchmark2]/...` (none
exist), error pages, build-time 404 styling beyond Astro default.

---

## Decision round 1 — resolved

| # | Decision                                                            |
|---|---------------------------------------------------------------------|
| 1 | Mobile: **ignore for now** (park under `~~mobile~~` until later)    |
| 2 | Wide viewport: **cap** with a CSS var so it's one-line to flip      |
| 3 | Compare page: **default-select top 2 models** on first load         |
| 4 | History chart: **leave alone**, only verify width isn't clipping    |

## Decision round 2 — pending

These are still open. None are blocking any proposal, but worth a call:

- **A.** "More reliable" repeated label on Compare page cards — reword
  to include the model name, or move model name above and keep the
  short label?
- **B.** Fixture detail baseline-repo section — collapse 16 cards
  into one `<pre>` block (P1), or leave as-is?
- **C.** Per-fixture gallery card token labels (P3) — only matters if
  the user is looking at the Fixture Gallery regularly. Confirm scope:
  just `FixtureCard.astro`, or also `FixtureCardBoth.astro`?

Want me to draft OpenSpec change proposals for the four approved items?

| Approved item                                  | Severity | File(s)                                                                 |
|------------------------------------------------|----------|-------------------------------------------------------------------------|
| Cost chart y-axis `$0.00e+0` ticks             | P0       | `src/components/charts/CostValueChart.tsx`                              |
| Level page dead column                         | P0       | `src/pages/models/[provider]/[model]/[level].astro`                     |
| Compare page default-select top 2 models       | P1       | `src/components/ComparePage.tsx` + `ModelSelector.tsx`                   |
| `.app-main` max-width via CSS var              | P1       | `src/styles/global.css:159-166`                                         |

The other P1/P2 items (compare chart labels overflowing, benchmark
matrix header wrap, model summary x-axis truncation, 16 baseline cards)
are still pending your sign-off in this doc before they become changes.
