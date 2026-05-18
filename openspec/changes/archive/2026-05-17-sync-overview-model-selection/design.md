## Context

The Overview page is an Astro page composed of separate `client:load` React islands. Each chart currently loads `results.json`, owns a local `selectedModels` state array, and renders its own `ModelSelector`.

`ModelSelector` already persists selection to `localStorage` and broadcasts `model-selection-changed` on `window`. Other selector instances listen for that event and update their internal dropdown display. The missing piece is that external events do not update the parent chart state, so a selector can visually sync while its chart continues rendering stale data.

Current data flow:

```
Chart A selector change
        |
        v
localStorage + window event
        |
        v
Other ModelSelector internal state updates
        |
        x
Other chart selectedModels state remains unchanged
```

## Goals / Non-Goals

**Goals:**

- Make every graph on `/` derive rendered data from the same selected model set.
- Keep all existing Overview chart sections and chart-specific filtering behavior.
- Preserve localStorage persistence and the existing `model-selection-changed` event name.
- Keep charts synchronized even when a chart renders an empty/no-data state.
- Avoid duplicating event-listener and localStorage code across each chart.

**Non-Goals:**

- Redesigning the ModelSelector UI.
- Changing results JSON shape or aggregation behavior.
- Changing Compare page head-to-head semantics.
- Adding URL query parameter synchronization.

## Decisions

### 1. Centralize selection state in a shared hook

**Decision:** Add a shared client-side helper, such as `useSyncedModelSelection`, that owns:

- default selection derivation from loaded data
- reading/writing `gitbench-model-selection`
- listening for `model-selection-changed`
- dispatching `model-selection-changed` when local user selection changes
- exposing `[selectedModels, setSelectedModels]` to chart components

**Rationale:** The bug exists because synchronization is split between selector display state and parent chart state. Moving synchronization to the state owner makes the selector a controlled UI component and ensures chart rendering updates whenever selection changes.

**Alternative considered:** Have `ModelSelector` call `onChange` when it receives external events. This is the smallest patch, but it keeps cross-chart application state hidden inside a leaf UI component and risks feedback loops as more charts add custom selection behavior.

### 2. Keep one global selection set for Overview charts

**Decision:** Overview charts SHALL share one selected model array. Chart-specific availability filters still apply at render time. For example, Runtime excludes selected models with no runtime data, and Cost excludes selected models with no cost data.

**Rationale:** Users expect the model selector to mean "which models am I looking at on this overview page?" A chart may have no data for some selected models, but it should not maintain an independent selection that diverges from the rest of the page.

**Alternative considered:** Maintain per-chart default subsets, such as "all models with runtime data" for Runtime. This preserves current defaults, but it conflicts with the user's mental model that one selector action should affect all graphs.

### 3. Render selectors in empty states

**Decision:** Charts with no matching data SHALL still render their `ModelSelector` before the empty-state card.

**Rationale:** If a chart drops the selector in an empty state, it loses the user's obvious way to recover and makes synchronization harder to verify. Runtime already follows this pattern; Cost and Token Usage should match it.

### 4. Preserve the existing browser event contract

**Decision:** Keep using `model-selection-changed` with `event.detail` as the selected model name array.

**Rationale:** The existing selector spec and implementation already rely on this event, and preserving it avoids a broad migration. The shared hook can become the single place that emits and consumes the event.

## Risks / Trade-offs

- **[Risk] Event feedback loops when one chart receives the event it dispatched** -> The hook should update state idempotently and avoid rebroadcasting changes received from an external event.
- **[Risk] localStorage can contain model names absent from the current dataset** -> The hook should sanitize stored selections against the loaded `data.models` list before exposing them to charts.
- **[Risk] Empty selection can make all charts blank** -> Preserve current "Clear all" behavior, but empty-state cards should remain understandable and selectors should remain available.
- **[Risk] Compare page may have different selection semantics** -> Limit the shared Overview behavior to Overview chart usage first; do not change Compare unless tests show it depends on the same selector contract.
