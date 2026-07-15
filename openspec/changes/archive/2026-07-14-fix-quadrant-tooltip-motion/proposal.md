## Why

The quadrant chart tooltip currently animates from an off-screen or stale position on first hover, which makes the interaction feel broken and distracts from the hovered model point. The desired behavior is a local pop-in on first hover, followed by smooth movement only when the user moves between hovered models.

## What Changes

- Update `QuadrantComparisonChart` tooltip motion so the first hover in an inactive cycle appears in-place at the active point without translating from a previous/default location.
- Preserve smooth tooltip movement when the user moves directly from one hovered quadrant point to another.
- Keep existing quadrant tooltip content, scoping, keyboard-focus behavior, cursor behavior, and text/JSON pair semantics unchanged.
- Respect reduced-motion behavior and avoid adding a new animation dependency.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `chart-components`: Adds required motion behavior for `QuadrantComparisonChart` hover tooltips.

## Impact

- Affected code: `web/src/components/charts/QuadrantComparisonChart.tsx`.
- Affected specs: `openspec/specs/chart-components/spec.md`.
- No API, data model, dependency, or persistence changes.
