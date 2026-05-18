## MODIFIED Requirements

### Requirement: Model selector is a searchable dropdown
The ModelSelector component SHALL render as a Popover-triggered Command menu instead of a flat row of pill checkboxes. On the Overview page, the trigger SHALL display the number of selected provider/base-model groups (e.g., "3 selected") or the names of selected base model groups when few are chosen. Clicking the trigger SHALL open a dropdown containing a search input, a selectable list of all available provider/base-model groups, and Select all / Clear all actions.

#### Scenario: Trigger shows selection count
- **WHEN** 3 model groups are selected
- **THEN** the trigger button displays "3 selected"

#### Scenario: Trigger shows model group names when few selected
- **WHEN** 1 or 2 model groups are selected
- **THEN** the trigger button displays the base model names (e.g., "gpt-5, claude-sonnet")

#### Scenario: Trigger shows placeholder when nothing selected
- **WHEN** no model groups are selected
- **THEN** the trigger button displays "Select models..."

### Requirement: Search filters the flat model list
When the user types in the search input, the model group list SHALL filter to entries whose provider, base model, full group ID, or child effort model names contain the search text (case-insensitive substring match). Filtering SHALL be immediate (no debounce). The list SHALL be flat at the selectable group level; child effort rows SHALL NOT appear as independently selectable options.

#### Scenario: Search narrows results by base model
- **WHEN** user types "gpt" in the search input
- **THEN** only model groups whose provider, base model, group ID, or child model names contain "gpt" are shown

#### Scenario: Search narrows results by effort level
- **WHEN** user types "high" in the search input
- **THEN** model groups containing a child effort model with "high" in its name or reasoning level are shown

#### Scenario: Search with no matches shows empty state
- **WHEN** user types a string matching no model groups
- **THEN** the dropdown shows "No models found"

#### Scenario: Clearing search restores full list
- **WHEN** user clears the search input
- **THEN** all model groups are shown again

### Requirement: Models are selectable by checkbox
Each model group entry in the list SHALL display a checkbox indicating selection state. Clicking an entry SHALL toggle the provider/base-model group selection. A provider brand icon (via `ProviderIcon` component, size 14) SHALL appear between the checkbox and the base model name. The group pass-rate range and effort count SHALL be displayed next to each entry as contextual information.

#### Scenario: Toggle a model group on
- **WHEN** user clicks an unselected model group entry
- **THEN** its checkbox fills and the group ID is added to the selected set

#### Scenario: Toggle a model group off
- **WHEN** user clicks a currently-selected model group entry
- **THEN** its checkbox clears and the group ID is removed from the selected set

#### Scenario: Provider icon shown per entry
- **WHEN** the model group list is displayed
- **THEN** each entry shows a provider brand icon next to the base model name

#### Scenario: Pass-rate range shown per entry
- **WHEN** the model group list is displayed
- **THEN** each entry shows the group's pass-rate range, such as "72-85%", or a single pass rate for one-effort groups

#### Scenario: Effort count shown per entry
- **WHEN** a model group contains 3 effort levels
- **THEN** the entry indicates that 3 efforts are included

### Requirement: Bulk actions are available
The dropdown SHALL include "Select all" and "Clear all" buttons at the top of the list, above the search input. "Select all" SHALL select every model group in the current filtered view. "Clear all" SHALL deselect everything.

#### Scenario: Select all on filtered results
- **WHEN** user searches "gpt" (showing 3 model groups) and clicks "Select all"
- **THEN** only the 3 filtered model groups are selected; other model groups remain unselected

#### Scenario: Clear all
- **WHEN** user clicks "Clear all"
- **THEN** all model groups are deselected, trigger shows "Select models..."

### Requirement: Selection changes notify parent
When the selected group set changes (via toggle, Select all, or Clear all), the component SHALL call the `onChange` callback with the updated array of selected group IDs. The callback SHALL be debounced — multiple rapid toggles within the same event loop tick SHALL result in a single callback.

#### Scenario: onChange fires after selection change
- **WHEN** user toggles a model group on
- **THEN** `onChange(selectedGroupIds)` is called with the updated array

#### Scenario: onChange fires once for Select all
- **WHEN** user clicks "Select all" on 50 model groups
- **THEN** `onChange` is called exactly once with all 50 group IDs, not 50 separate calls

### Requirement: Initial selection is respected
The component SHALL accept an `initialSelected` prop (array of group IDs) and pre-select those model groups on mount. If `initialSelected` is empty or undefined, the component SHALL read from `localStorage` key `gitbench-model-selection`. If localStorage contains old model+effort names, they SHALL be mapped to matching provider/base-model group IDs. If localStorage is empty or no valid selections remain after sanitization, all model groups SHALL be selected by default.

#### Scenario: Pre-selection from URL parameter
- **WHEN** ComparePage mounts with `?with=gpt-5`
- **THEN** "gpt-5" is pre-selected in the dropdown when that value maps to a known option

#### Scenario: Pre-selection from localStorage group IDs
- **WHEN** localStorage contains `["openai/gpt-5", "anthropic/claude-sonnet"]` and no `initialSelected` prop is set
- **THEN** those two model groups are pre-selected

#### Scenario: Pre-selection migrates model effort names
- **WHEN** localStorage contains `["openai/gpt-5:high"]` and no `initialSelected` prop is set
- **THEN** the `openai/gpt-5` model group is pre-selected

#### Scenario: Default all-selected when no initial value and no localStorage
- **WHEN** the component mounts with no `initialSelected` prop and localStorage is empty
- **THEN** all available model groups are selected

### Requirement: Selection changes persist to localStorage
When the selected group set changes, the component SHALL write the array of selected group IDs to `localStorage` under the key `gitbench-model-selection` as a JSON string.

#### Scenario: localStorage updated on selection change
- **WHEN** a user toggles a model group off, resulting in selected groups `["openai/gpt-5"]`
- **THEN** `localStorage.getItem("gitbench-model-selection")` returns `'["openai/gpt-5"]'`

### Requirement: Selection changes broadcast via CustomEvent
When the selected group set changes, the component SHALL dispatch a `CustomEvent` named `model-selection-changed` on `window`, with the new group ID array in `event.detail`.

#### Scenario: CustomEvent dispatched on selection change
- **WHEN** a user toggles a model group
- **THEN** a `model-selection-changed` event fires on `window` with the updated group ID array in `detail`

### Requirement: ModelSelector listens for external selection changes
Each `ModelSelector` instance SHALL listen for `model-selection-changed` events on `window` and update its visible selected state to match the received group ID selection. If the instance has an `onChange` callback, external selection changes SHALL also notify that callback with the received selection so the consuming chart or page state stays synchronized with the selector display. The listener SHALL ignore malformed event details that are not arrays of model group IDs.

#### Scenario: Instance updates on receiving event
- **WHEN** `ModelSelector` instance #1 dispatches `model-selection-changed` with `["openai/gpt-5"]`
- **THEN** `ModelSelector` instance #2 on the same page updates to show only "openai/gpt-5" selected

#### Scenario: Parent state updates on receiving event
- **WHEN** `ModelSelector` instance #1 dispatches `model-selection-changed` with `["openai/gpt-5"]`
- **THEN** `ModelSelector` instance #2 calls its `onChange` callback with `["openai/gpt-5"]`

#### Scenario: Malformed event detail is ignored
- **WHEN** a `model-selection-changed` event fires with non-array detail
- **THEN** the `ModelSelector` selected state and parent callback are left unchanged

#### Scenario: Event listener is cleaned up on unmount
- **WHEN** a `ModelSelector` instance unmounts
- **THEN** its `model-selection-changed` event listener is removed from `window`
