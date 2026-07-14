## Context

The three resource-usage charts build provider/base-model rows with a numeric `sortValue`, then sort those rows in their React components before passing them to the shared vertical chart UI. A single selected output mode uses that mode's representative median as `sortValue`; `Both` mode uses the mean of the available Text and JSON representative medians. Cost, API Time, and Token Usage currently sort this value ascending, while Pass Rate already sorts it descending.

The same three components render overall, benchmark-scoped, and fixture-scoped data, so a component-level ordering change covers every supported scope without changing data aggregation or APIs.

## Goals / Non-Goals

**Goals:**

- Display the largest API cost, API time, and token usage values at the left edge of their charts.
- Retain the existing representative-value and `Both`-mode calculations.
- Keep ordering responsive to model selection, output mode, and report scope changes.
- Add regression coverage or verification that distinguishes descending from ascending order.

**Non-Goals:**

- Changing metric aggregation, normalization, or range-whisker calculations.
- Changing the Pass Rate, quadrant comparison, or time-series charts.
- Adding an interactive sort-direction control.
- Changing axes, labels, tooltips, colors, or API payloads.

## Decisions

### Reverse ordering at each resource chart's presentation boundary

Each affected component will sort its completed rows by descending `sortValue` immediately before rendering. This is the smallest change and preserves `buildGroupedMetricRows` and `buildTokenUsageRows` as order-neutral data builders that other consumers can arrange independently.

Alternative considered: reverse the output inside the shared row builders. That would silently change every consumer and couple reusable data preparation to one presentation preference.

### Continue using the existing `sortValue`

Single-mode charts will rank by that mode's representative median. `Both` mode will continue ranking by the arithmetic mean of available Text and JSON representatives, including the current fallback to the available mode when its sibling is missing.

Alternative considered: rank `Both` mode by the maximum sibling value. That would be a metric-semantics change beyond the requested direction reversal and could reorder categories for reasons unrelated to this proposal.

### Preserve stable ordering for equal values

The descending numeric comparison will return zero for ties, preserving the input order under JavaScript's stable sort behavior. No additional alphabetical tie-breaker will be introduced because that would alter existing tie behavior.

## Risks / Trade-offs

- [API Time now emphasizes the slowest models even though lower is better] → Keep the existing tooltip explanation that lower is faster; the requested goal is to surface the highest values first consistently across resource charts.
- [A future chart could accidentally reintroduce ascending ordering with another inline comparator] → Cover the three affected charts in focused ordering verification and state the descending requirement explicitly in their capability specs.
- [Changing output mode can reorder categories] → This is expected and retained because ordering is based on the currently visible representative values.

## Migration Plan

Deploy as a client-only presentation update with no data migration. Rollback consists of restoring the three ascending comparators.

## Open Questions

None.
