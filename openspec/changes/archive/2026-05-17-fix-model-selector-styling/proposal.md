## Why

The ModelSelector dropdown has two UX pain points: (1) the "Select all" and "Clear" action buttons scroll away with the list, making them unreachable when many models are selected, and (2) pass-rate percentage badges become unreadable against the accent-colored hover/selection background because the colored text (green/orange/red) clashes with the cyan highlight.

## What Changes

- Move "Select all" and "Clear" buttons above the scrollable list so they remain sticky at the top of the dropdown
- Adjust pass-rate badge styling on hover/selection to maintain readability against the accent background

## Capabilities

### New Capabilities

None. This is a UI refinement of existing functionality.

### Modified Capabilities

- `chart-components`: The ModelSelector quick-select controls ("Select all" / "Clear") change position from inside the scrollable list to a sticky header above the list. Pass-rate badge text rendering adapts to hover/selection states for readability.

## Impact

- Affected files: `gitbench/web/src/components/charts/ModelSelector.tsx`, `gitbench/web/src/components/ui/multi-select.tsx`
- No API changes, no breaking changes
- Visual-only changes — no data or behavior impact
