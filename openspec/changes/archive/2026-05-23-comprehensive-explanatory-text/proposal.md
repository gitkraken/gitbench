## Why

The GitBench web dashboard presents rich benchmarking data across 10 pages, but provides almost no explanatory text, tooltips, or contextual help. A first-time visitor cannot understand what any chart shows, what any metric means, or how to use the interface without reading the methodology page first. This change adds comprehensive, accessible explanatory text and hover cards everywhere — so nobody at any technical level can say they don't understand what they're looking at.

## What Changes

- **New CSS tooltip system**: A reusable `.has-tooltip` CSS class with `data-tooltip` attributes, ⓘ icon indicators, and `title` fallbacks for accessibility. Works across all Astro pages with zero JavaScript.
- **Section blurbs on all 10 pages**: Every chart, table, and page section gets a 1-2 sentence prose blurb explaining what it shows, how to read it, and any important caveats. "Learn more →" links connect to relevant methodology sections.
- **Enhanced React chart tooltips**: All six Recharts-based chart components (PassRateBarChart, CostValueChart, RuntimeBarChart, TokenUsageChart, ScatterPlot, TimeSeriesChart) get enriched tooltip content with explanatory text below the existing data display.
- **Heatmap cell tooltips**: BenchmarkHeatmap `<td>` elements get enhanced `title` attributes with detailed cell descriptions (model × benchmark, pass rate, passed/total counts).
- **Expanded overview introduction**: The landing page About section grows from 1 paragraph to 3-4 paragraphs explaining why GitBench exists, what it tests, and who it's for.
- **Empty state improvements**: Existing empty state messages in Cost, Runtime, and Token charts are reviewed for clarity and completeness.
- **Consistent ⓘ icon pattern**: Every tooltip trigger uses a small ⓘ icon rather than dotted underlines, making hover targets visually obvious across the app.

## Capabilities

### New Capabilities
- `tooltip-system`: Reusable CSS-based tooltip/hover-card infrastructure with icon indicators, `title` fallbacks, and dark-themed visual design matching the app aesthetic.
- `page-help-text`: Section-level explanatory prose blurbs on all Astro pages, providing page-specific context, reading guidance, and "Learn more →" links to methodology.

### Modified Capabilities
- `chart-components`: All six React chart components get enriched Recharts `<Tooltip>` content with explanatory text separators. BenchmarkHeatmap gets enhanced `title` attributes on cells.
- `astro-site`: All Astro page templates (`index.astro`, `models/index.astro`, `models/[provider]/[model]/index.astro`, `models/[provider]/[model]/[level].astro`, `benchmarks/index.astro`, `benchmarks/[name].astro`, `explore.astro`, `compare.astro`, `history.astro`, `fixtures/[benchmark]/[fixture].astro`) get section blurbs and tooltip triggers. `Layout.astro` imports the tooltip CSS. `global.css` adds the `.has-tooltip` utility class.
- `methodology-page`: Minor tooltip additions to technical sections for consistency with the rest of the site.

## Impact

- **Affected code**: 8 Astro page files, 6 React chart components, `global.css`, `Layout.astro`, `grouped-chart-ui.tsx`, fixture components (`PromptBlock.astro`, `ExpectedBlock.astro`, `ModelOutputCard.astro`, `FixtureCard.astro`), `Sidebar.astro`
- **No API changes, no backend changes, no new dependencies**
- **Breaking**: None — all changes are additive (new text, new tooltips, existing behavior preserved)
