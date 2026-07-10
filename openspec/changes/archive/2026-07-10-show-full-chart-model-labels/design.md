## Context

The grouped overview charts share their X-axis model tick rendering through `VerticalGroupedMetricChart` in `web/src/components/charts/grouped-chart-ui.tsx`. The current tick renderer displays a provider icon plus `truncateName(baseModel, 10)` inside a small rotated `foreignObject`, with CSS ellipsis as a second clipping layer.

This behavior is also part of the current OpenSpec requirements: `chart-components`, `cost-value-chart`, `runtime-chart`, and `token-usage-chart` all describe truncated base model labels. Current report data includes several base model names longer than 20 characters, with `gemini-3.1-flash-lite-preview` at 29 characters, so the truncation hides meaningful distinguishing text.

## Goals / Non-Goals

**Goals:**

- Show full base model names on grouped bar chart model-axis labels.
- Preserve the provider icon and rotated label visual language.
- Avoid clipping and avoid intentional ellipsis for the current long-label dataset.
- Keep the fix centralized in the shared chart UI where possible.

**Non-Goals:**

- Redesign chart sorting, bars, legends, tooltips, or data aggregation.
- Change model names, provider names, or report API data.
- Rework non-chart model labels such as selector rows, heatmap table headers, or model detail pages.
- Replace Recharts.

## Decisions

### Use full text in the shared vertical tick renderer

`VerticalGroupTick` should render `row.baseModel` directly instead of passing it through `truncateName(..., 10)`. The tick should also remove `maxWidth`, `textOverflow: "ellipsis"`, and other styling whose purpose is to clip the label.

Alternative considered: increase the truncation limit from 10 to 20 or 30. That would improve some labels but preserve the same failure mode when model names grow again, and it would still contradict the product goal of full-length labels.

### Allocate chart space rather than hiding overflow

The chart should reserve enough label room by increasing the rotated tick box width, X-axis height, and bottom margin. Dense selections should remain readable by giving the chart an adaptive minimum width and allowing horizontal overflow at the chart-card level when the viewport is too narrow for every selected group.

Alternative considered: only increase the bottom margin. That prevents vertical clipping but does not solve horizontal label collisions when many model groups are selected.

### Keep the fixed plot height

The plot area can remain 350px high. Extra label room should be handled by chart margin/axis height and horizontal overflow rather than changing the metric plotting height.

Alternative considered: scale chart height with selected model count. That would create very tall overview sections and make comparisons across charts harder.

### Leave Compare and quadrant ranked-list labels out of this change

The direct truncation found during exploration is the grouped chart tick helper. The quadrant ranked list also calls `truncateName(point.baseModel, 20)`, but it is not an axis label and lives in a compact list below the quadrant chart. Compare overall labels currently use full canonical labels with a fixed Y-axis width; that is a separate layout concern.

Alternative considered: remove every use of `truncateName` in chart components. That broadens the visual scope and risks changing compact list/table surfaces that are not part of the reported axis-label problem.

## Risks / Trade-offs

- Dense all-model selections may require horizontal scrolling. → Use an obvious chart-card overflow container and verify all currently selected groups remain readable at desktop and mobile widths.
- Longer labels may push legends farther below the chart. → Keep legend placement unchanged and verify the chart section still scans cleanly.
- Recharts `ResponsiveContainer` can behave poorly inside arbitrary overflow layouts. → Prefer a stable inner chart width derived from selected group count and max label length, with the responsive container attached to that inner element.
- Specs can drift if only code changes. → Update all existing requirements that currently mandate truncated labels.
