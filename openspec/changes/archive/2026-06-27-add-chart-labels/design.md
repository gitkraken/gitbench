## Context

The GitBench overview page renders six chart sections. Four of them (PassRateBarChart, CostValueChart, RuntimeBarChart, TokenUsageChart) share a common rendering component called `VerticalGroupedMetricChart` in `grouped-chart-ui.tsx`. This component renders a Recharts `BarChart` with provider-colored bars, diagonal X-axis model labels, tooltips, and legends — but no Y-axis label. Each chart's metric (pass rate %, cost $, runtime seconds, tokens) is communicated only by the section heading above the chart in `index.astro`.

The `TimeSeriesChart` renders two variants — a campaign-history line chart and a per-model-over-time line chart. Neither has a Y-axis label. The Y-axis is always pass rate percentage (0–100%).

The `QuadrantComparisonChart` renders a Recharts `ScatterChart` with two user-selectable metrics on X and Y. It already has axis labels (e.g., "Cost", "Intelligence (Pass Rate)"). It shades the "optimal quadrant" using a `ReferenceArea` and shows a text line reading "Optimal quadrant: lower cost + higher pass rate". However, the four quadrants themselves are unlabeled — a user must infer which quadrant is "good" from the shading and the text, rather than seeing it spatially.

The `ScatterPlot` component on the Compare page already has X and Y axis labels and does not need changes.

## Goals / Non-Goals

**Goals:**
- Make every chart self-describing — a viewer should know what the Y-axis represents without reading external context
- Make the quadrant chart's spatial layout instantly readable via in-chart quadrant labels
- Minimal code change surface — leverage the shared `VerticalGroupedMetricChart` for bar charts

**Non-Goals:**
- Data labels (values on bars/points) — deferred due to clutter risk with 20+ bars
- Chart-level titles within chart components — the page section labels already serve this purpose
- Reference lines or median markers — separate concern, not part of this change
- Changes to the ScatterPlot (Compare page) — it already has axis labels
- Changes to the BenchmarkHeatmap — it's a data table, not a chart with axes

## Decisions

### Decision 1: Y-axis label via prop on shared component

**Choice:** Add a `yAxisLabel?: string` prop to `VerticalGroupedMetricChart`. Each consumer passes its own label string.

**Rationale:** All four bar charts already route through this single component. Adding one prop and passing it to the Recharts `<YAxis label={...} />` is a one-line change in the shared component, plus one prop added to each of the four call sites. No structural refactoring needed.

**Alternative considered:** Add labels independently in each chart component. Rejected because they all use the same shared rendering path — duplicating the label configuration would be unnecessary.

### Decision 2: Y-axis label format

**Choice:** Use concise unit-aware labels: "Pass Rate (%)", "Cost (USD)", "API Time (s)", "Tokens", "Pass Rate (%)".

**Rationale:** The Y-axis tick formatter already shows formatted values (e.g., `$0.12`, `87.5%`, `12.3s`, `1.2K`). The label should complement the ticks by naming the metric and its unit, not duplicate the format. Short labels avoid vertical space waste.

### Decision 3: Generic directional quadrant labels

**Choice:** Use generic directional labels that adapt to the selected metrics:
- Optimal quadrant: "Better on both"
- Two trade-off quadrants: "Better {xShort} / Worse {yShort}" and "Worse {xShort} / Better {yShort}"
- Worst quadrant: "Worse on both"

Where `{xShort}` and `{yShort}` are the metric `shortLabel` values (e.g., "Cost", "Pass Rate", "Tokens", "API Time").

**Rationale:** The quadrant chart allows any pairing of four metrics (pass rate, cost, tokens, runtime) on either axis. Hardcoded labels like "Smart & Cheap" only work for cost-vs-pass-rate. Generic directional labels are always correct regardless of metric selection. The existing "Optimal quadrant:" text line already provides the specific metric context — the quadrant labels add the spatial layer.

**Alternative considered:** Descriptive contextual labels (e.g., "Smart & Cheap", "Smart & Pricey"). Rejected because they require mapping all 12 possible metric pairings to sensible adjective pairs, and any future metric addition would need new label mappings.

### Decision 4: Quadrant label positioning

**Choice:** Render quadrant labels as Recharts `Label` components inside each `ReferenceArea`, positioned at the corner of each quadrant farthest from the chart center.

**Rationale:** Recharts `ReferenceArea` supports child `Label` elements. Positioning at the outer corner (away from the crosshair lines) keeps labels from overlapping the data cluster near the center. Labels use small font size (10px mono) and dim color (`var(--text-dim)`) to stay unobtrusive.

**Alternative considered:** Overlay HTML divs positioned absolutely over the chart container. Rejected because they would not track the chart's coordinate system and would misalign on resize or domain changes.

## Risks / Trade-offs

- **Risk:** Y-axis label may crowd the Y-axis tick values on narrow viewports → **Mitigation:** The Y-axis already has `width={72}` reserved. The label renders rotated -90° inside that space. If it overlaps, the margin can be adjusted by 4–8px.
- **Risk:** Quadrant labels may overlap data points near quadrant boundaries → **Mitigation:** Labels are positioned at the outer corners of each quadrant, farthest from the median crosshair where points tend to cluster. Small font and dim color keep them visually subordinate to data.
- **Risk:** Quadrant labels add visual noise to an already information-dense chart → **Mitigation:** Use 10px font, `var(--text-dim)` color, and keep labels to 2–4 words. The existing "Optimal quadrant:" text line above the chart can potentially be removed once quadrant labels are in place, reducing net text.