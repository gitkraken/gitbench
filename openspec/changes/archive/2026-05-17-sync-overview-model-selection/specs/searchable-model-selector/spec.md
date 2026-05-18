## MODIFIED Requirements

### Requirement: ModelSelector listens for external selection changes
Each `ModelSelector` instance SHALL listen for `model-selection-changed` events on `window` and update its visible selected state to match the received selection. If the instance has an `onChange` callback, external selection changes SHALL also notify that callback with the received selection so the consuming chart or page state stays synchronized with the selector display. The listener SHALL ignore malformed event details that are not arrays of model names.

#### Scenario: Instance updates on receiving event
- **WHEN** `ModelSelector` instance #1 dispatches `model-selection-changed` with `["gpt-4o"]`
- **THEN** `ModelSelector` instance #2 on the same page updates to show only "gpt-4o" selected

#### Scenario: Parent state updates on receiving event
- **WHEN** `ModelSelector` instance #1 dispatches `model-selection-changed` with `["gpt-4o"]`
- **THEN** `ModelSelector` instance #2 calls its `onChange` callback with `["gpt-4o"]`

#### Scenario: Malformed event detail is ignored
- **WHEN** a `model-selection-changed` event fires with non-array detail
- **THEN** the `ModelSelector` selected state and parent callback are left unchanged

#### Scenario: Event listener is cleaned up on unmount
- **WHEN** a `ModelSelector` instance unmounts
- **THEN** its `model-selection-changed` event listener is removed from `window`
