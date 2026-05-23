## 1. Tooltip Infrastructure

- [x] 1.1 Add `.has-tooltip` CSS class to `global.css` with `::after` pseudo-element, icon indicator, positioning, transitions, and dark theme styling
- [x] 1.2 Verify `Layout.astro` imports `global.css` (already does — confirm tooltip styles are available site-wide)

## 2. Overview Page

- [x] 2.1 Expand About section from 1 paragraph to 3-4 paragraphs: mission, what it tests, who it's for, what the page shows
- [x] 2.2 Add section blurbs above each of the 5 charts (Pass Rate, Cost, Runtime, Token Usage, Benchmark Matrix) explaining what each chart shows and how to read it
- [x] 2.3 Add `.has-tooltip` spans with `data-tooltip` and `title` attributes on all 5 section labels

## 3. Models Pages

- [x] 3.1 Add organizational blurb to `models/index.astro` explaining provider → base model → reasoning level hierarchy and what reasoning levels mean
- [x] 3.2 Add `.has-tooltip` on reasoning level badges and pass rate badges in model cards
- [x] 3.3 Add fixture gallery blurb to `models/[provider]/[model]/[level].astro` explaining what each card represents and how to use filters
- [x] 3.4 Add `.has-tooltip` on PASS/FAIL badges, similarity percentages, token badges, and filter selects on the model level page
- [x] 3.5 Add section blurb to `models/[provider]/[model]/index.astro` (base model overview) explaining the level cards

## 4. Benchmarks Pages

- [x] 4.1 Add intro blurb to `benchmarks/index.astro` explaining the 17 benchmark categories and what Best % means
- [x] 4.2 Add `.has-tooltip` on Best % badges and fixture count labels
- [x] 4.3 Add leaderboard blurb to `benchmarks/[name].astro` explaining the ranking and what it reveals about model strengths
- [x] 4.4 Add table blurb explaining the per-fixture comparison table and what the percentages mean
- [x] 4.5 Add `.has-tooltip` on table headers (Fixture, Difficulty) and on difficulty values

## 5. Explore, Compare, and History Pages

- [x] 5.1 Add usage blurb to `explore.astro` explaining the page as a fixture index and how to filter
- [x] 5.2 Add `.has-tooltip` on tag pills, difficulty filter, benchmark filter, and search input
- [x] 5.3 Add usage blurb to `compare.astro` header and head-to-head explanation
- [x] 5.4 Add section blurbs to `history.astro` above Time Series chart and Run Log table
- [x] 5.5 Add `.has-tooltip` spans on all Run Log table headers (Profile, Reasoning, Suite, Δ prev, Git SHA, Compare)

## 6. Fixture Detail Pages

- [x] 6.1 Add Model Outputs blurb to `fixtures/[benchmark]/[fixture].astro` explaining the sorted output list and PASS/FAIL criteria
- [x] 6.2 Add `.has-tooltip` on Prompt and Expected section labels in `PromptBlock.astro` and `ExpectedBlock.astro`
- [x] 6.3 Add `.has-tooltip` on PASS/FAIL badges, similarity percentages, and token badges in `ModelOutputCard.astro`
- [x] 6.4 Add `.has-tooltip` on PASS/FAIL badge and similarity % in `FixtureCard.astro`

## 7. React Chart Tooltips

- [x] 7.1 Enhance `PassRateBarChart` Recharts Tooltip: add separator + explanatory text about pass rate metric
- [x] 7.2 Enhance `CostValueChart` Recharts Tooltip: add separator + explanatory text about cost (OpenRouter vs Ollama)
- [x] 7.3 Enhance `RuntimeBarChart` Recharts Tooltip: add separator + explanatory text about wall-clock time
- [x] 7.4 Enhance `TokenUsageChart` Recharts Tooltip: add separator + explanatory text about token usage
- [x] 7.5 Enhance `ScatterPlot` Recharts Tooltip: add separator + explanatory text about color coding and agreement
- [x] 7.6 Enhance `TimeSeriesChart` Recharts Tooltip: add separator + explanatory text about pass rate over time
- [x] 7.7 Add `title` attribute to each chart's outermost wrapper div with chart description
- [x] 7.8 Add enhanced `title` attributes to `BenchmarkHeatmap` `<td>` cells with model×benchmark×pass rate×descriptor format

## 8. Methodology Page

- [x] 8.1 Add `.has-tooltip` on key technical terms (SequenceMatcher, OpenRouter, Ollama, benchmark suite, pass@k) for quick-reference definitions

## 9. Review and Polish

- [x] 9.1 Review all tooltip text for consistency of tone, terminology, and technical accuracy
- [x] 9.2 Review all section blurbs for accessibility to non-technical readers
- [x] 9.3 Verify all `title` attributes are present as fallbacks on every tooltip trigger
- [x] 9.4 Build and visually inspect all pages to ensure tooltips render correctly and blurbs align with charts
