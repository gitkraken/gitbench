## MODIFIED Requirements

### Requirement: Initial selection is respected
The component SHALL accept an `initialSelected` prop (array of model names) and pre-select those models on mount. If `initialSelected` is empty or undefined, the component SHALL read from `localStorage` key `gitbench-model-selection`. If localStorage is also empty, all models SHALL be selected by default.

#### Scenario: Pre-selection from URL parameter
- **WHEN** ComparePage mounts with `?with=gpt-4o`
- **THEN** "gpt-4o" is pre-selected in the dropdown

#### Scenario: Pre-selection from localStorage
- **WHEN** localStorage contains `["gpt-4o", "claude-sonnet"]` and no `initialSelected` prop is set
- **THEN** those two models are pre-selected

#### Scenario: Default all-selected when no initial value and no localStorage
- **WHEN** the component mounts with no `initialSelected` prop and localStorage is empty
- **THEN** all available models are selected

## ADDED Requirements

### Requirement: Selection changes persist to localStorage
When the selected set changes, the component SHALL write the array of selected model names to `localStorage` under the key `gitbench-model-selection` as a JSON string.

#### Scenario: localStorage updated on selection change
- **WHEN** a user toggles a model off, resulting in selected models `["gpt-4o"]`
- **THEN** `localStorage.getItem("gitbench-model-selection")` returns `'["gpt-4o"]'`

### Requirement: Selection changes broadcast via CustomEvent
When the selected set changes, the component SHALL dispatch a `CustomEvent` named `model-selection-changed` on `window`, with the new selection array in `event.detail`.

#### Scenario: CustomEvent dispatched on selection change
- **WHEN** a user toggles a model
- **THEN** a `model-selection-changed` event fires on `window` with the updated selection array in `detail`

### Requirement: ModelSelector listens for external selection changes
Each `ModelSelector` instance SHALL listen for `model-selection-changed` events on `window` and update its internal state to match the received selection. This enables same-page synchronization across multiple instances.

#### Scenario: Instance updates on receiving event
- **WHEN** `ModelSelector` instance #1 dispatches `model-selection-changed` with `["gpt-4o"]`
- **THEN** `ModelSelector` instance #2 on the same page updates to show only "gpt-4o" selected

#### Scenario: Event listener is cleaned up on unmount
- **WHEN** a `ModelSelector` instance unmounts
- **THEN** its `model-selection-changed` event listener is removed from `window`
