## 1. Shared grouped chart label rendering

- [x] 1.1 Update `VerticalGroupTick` in `web/src/components/charts/grouped-chart-ui.tsx` to render the full `baseModel` text without calling `truncateName`
- [x] 1.2 Remove the tick label CSS that intentionally clips or ellipsizes the base model text
- [x] 1.3 Increase the rotated tick label drawing area, X-axis height, and chart bottom margin so current long labels fit vertically
- [x] 1.4 Add an adaptive minimum chart width or overflow wrapper so dense selected-model sets keep full labels readable instead of overlapping or clipping

## 2. Chart coverage

- [x] 2.1 Verify `PassRateBarChart` inherits the full-label behavior through `VerticalGroupedMetricChart`
- [x] 2.2 Verify `CostValueChart` inherits the full-label behavior through `VerticalGroupedMetricChart`
- [x] 2.3 Verify `RuntimeBarChart` inherits the full-label behavior through `VerticalGroupedMetricChart`
- [x] 2.4 Verify `TokenUsageChart` inherits the full-label behavior through `VerticalGroupedMetricChart`
- [x] 2.5 Leave non-axis compact labels, including the quadrant ranked list, unchanged unless visual verification shows they are part of the reported chart-label problem

## 3. Verification

- [x] 3.1 Run the relevant web tests for chart data/model grouping behavior
- [x] 3.2 Run the web build or typecheck command used by this repo
- [x] 3.3 Visually verify the overview page at desktop width with all default selected model groups
- [x] 3.4 Visually verify a narrow/mobile viewport and confirm the chart preserves full labels through spacing or horizontal scrolling
- [x] 3.5 Specifically verify long labels such as `gemini-3.1-flash-lite-preview`, `nemotron-3-super-120b-a12b`, and `trinity-large-thinking` render in full
