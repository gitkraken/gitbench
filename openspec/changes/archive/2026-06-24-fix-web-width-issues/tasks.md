## 1. Cost chart y-axis tick formatter

- [x] 1.1 In `gitbench/web/src/components/charts/CostValueChart.tsx`, replace the hand-rolled `formatCost()` (lines 20–24) with an `Intl.NumberFormat` USD formatter that never emits scientific notation and handles `0`, small values, and non-finite inputs
- [x] 1.2 Export `formatCost` from the same file so the tooltip renderer on line 107 can import it (currently uses the local closure)
- [x] 1.3 Verify the Cost per Full Run card on `/` (desktop 1440×900): y-axis ticks read `$0`, `$0.01`, `$0.02`, etc. with no `$0.00e+0` or `$5.2e-3` strings

## 2. Level page layout — no dead central column

- [x] 2.1 In `gitbench/web/src/pages/models/[provider]/[model]/[level].astro`, restructure the "Reliability by Benchmark" section (the section containing the `Reliability by Benchmark (Text)` table card) so the table renders full-width within the `.card` wrapper instead of leaving ~40% empty space to the left of the metadata block
- [x] 2.2 In the same file, restructure the "Text vs JSON Schema Comparison" section so the four summary tiles (`+7 / -66 / 119 / 12`) and the benchmark delta table render inside a single full-width `.card` instead of as two side-by-side groups with empty space between
- [x] 2.3 Verify `/models/deepseek/deepseek-v4-flash/high/` (desktop 1440×900 and tablet 800×1100): both sections are full-width; no ~40% empty column at desktop; tablet layout unchanged

## 3. Compare page default selection

- [x] 3.1 Add a `defaultSelectionForCompare(data: GitBenchData): string[]` helper in `gitbench/web/src/components/charts/ModelSelector.tsx` (or co-located module) that returns the top two provider/base-model group IDs sorted by mean pass rate descending, skipping groups without a measurable pass rate
- [x] 3.2 In `gitbench/web/src/components/ComparePage.tsx`, call the helper only when the initial selection from `useSyncedModelSelection` is empty AND no stored selection is being restored; otherwise keep existing behavior
- [x] 3.3 Verify `/compare` on cold load (clear local storage, hard reload): two model groups are pre-selected; the "Fixture Reliability Delta" and "Overall Pass Rates" cards/charts render with data on first paint; the "1 selected" copy is replaced by the actual count

## 4. App main content area cap

- [x] 4.1 In `gitbench/web/src/styles/global.css`, add `--main-max-width: 1440px;` to the existing `:root` block (around line 92 where the other CSS variables live)
- [x] 4.2 In the same file, add `max-width: var(--main-max-width); margin-inline: auto;` to the `.app-main` rule (around line 159)
- [x] 4.3 Verify at desktop 1440×900: `.app-main` width caps at 1440px and the content is centered; verify at desktop 1920×1080: ~240px gutter on each side of the content; verify at tablet 800×1100 and mobile 390×1200: no regression — content still fills the available space below the sidebar

## 5. Verification pass

- [x] 5.1 Take screenshots at desktop (1440×900) and wide (1920×1080) of `/`, `/compare`, `/models/deepseek/deepseek-v4-flash/high/` after all four fixes are applied; compare to `/tmp/gitbench-crawl/_home.png`, `_compare.png`, and `full/_level_tall.png` baselines to confirm the four specific defects are resolved
- [x] 5.2 Confirm no new console warnings/errors on any of the touched pages
- [x] 5.3 Run `pnpm fmt` against touched files (per `AGENTS.md` web package rule)
