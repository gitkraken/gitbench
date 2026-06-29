## Purpose

The searchable model selector provides a multi-select dropdown for choosing which models to display in the overview charts.
## Requirements
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
The component SHALL accept an `initialSelected` prop (array of group IDs) and pre-select those model groups on mount. If `initialSelected` is empty or undefined, the component SHALL read from report URL state. URL values MAY be provider/base-model group IDs or old model+effort names; old model+effort names SHALL be mapped to matching provider/base-model group IDs. If URL state is empty or no valid selections remain after sanitization, the component SHALL use the page default selection.

#### Scenario: Pre-selection from URL parameter
- **WHEN** ComparePage mounts with `?with=gpt-5`
- **THEN** "gpt-5" is pre-selected in the dropdown when that value maps to a known option

#### Scenario: Pre-selection from compressed URL state
- **WHEN** the URL contains compressed report view state for `["openai/gpt-5", "anthropic/claude-sonnet"]`
- **THEN** those two model groups are pre-selected

#### Scenario: Pre-selection migrates model effort names
- **WHEN** URL state contains `["openai/gpt-5:high"]`
- **THEN** the `openai/gpt-5` model group is pre-selected

#### Scenario: Default all-selected when no URL state
- **WHEN** the component mounts with no `initialSelected` prop and no report URL state on an overview or benchmark page
- **THEN** all available model groups are selected

### Requirement: Selection changes persist to URL state
When the selected group set changes, the model selection experience SHALL update the current URL's report view state instead of writing the selection as the source of truth in localStorage.

#### Scenario: URL updated on selection change
- **WHEN** a user toggles a model group off, resulting in selected groups `["openai/gpt-5"]`
- **THEN** the current URL contains report view state that resolves to `["openai/gpt-5"]`

#### Scenario: Same-page selectors receive updated selection
- **WHEN** a selector writes updated URL state
- **THEN** other selector instances on the page update to the same selected group set

#### Scenario: localStorage selection is ignored
- **WHEN** localStorage contains `gitbench-model-selection`
- **AND** the URL contains no report view state
- **THEN** the selector initializes from the page default rather than localStorage

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

### Requirement: Output mode selection is separate from model group selection
The model selection experience SHALL keep provider/base-model group selection separate from output-mode selection. Changing output mode SHALL NOT change the selected model group IDs encoded in report URL state.

#### Scenario: Switching output mode preserves selected models
- **WHEN** the user changes from text mode to JSON-schema mode
- **THEN** the selected provider/base-model groups remain unchanged

#### Scenario: Model selection state does not encode output mode in group IDs
- **WHEN** selected model groups are persisted to report URL state
- **THEN** the persisted model group list does not encode output mode in model group IDs

### Requirement: Output mode state synchronizes across charts
Output mode selection SHALL synchronize across report components on the same page similarly to model selection, so charts and tables use the same selected output-mode state. Output mode changes SHALL update report URL state, and missing output-mode state SHALL resolve to `both` when both output modes are available.

#### Scenario: Output mode change updates charts
- **WHEN** the user selects JSON-schema mode next to a model selector
- **THEN** other charts and tables on the page update to JSON-schema results

#### Scenario: Both mode exposes variants
- **WHEN** the user selects both output modes
- **THEN** model group expansion returns separate text and JSON-schema variants where available

#### Scenario: Missing output mode defaults to both
- **WHEN** a report page loads with no output-mode URL state
- **AND** both text and JSON-schema output modes are available
- **THEN** output mode controls initialize to `Both`


### Requirement: Compare page defaults to the top-two model groups by pass rate on cold load

When the Compare page (`/compare`) initializes its selected model groups and no report URL state exists, the `ModelSelector` SHALL default to the two provider/base-model groups with the highest mean pass rate across their visible output modes, sorted descending. The default SHALL only apply to bare Compare URLs. A copied Compare URL with report view state SHALL restore that state.

#### Scenario: Cold load selects the top two by pass rate
- **WHEN** a user navigates to `/compare` with no report URL state
- **AND** the data has model groups with pass rates `[0.92, 0.88, 0.71, 0.55]`
- **THEN** the first two groups (pass rates `0.92` and `0.88`) are selected on first render

#### Scenario: Shared URL restores encoded selection
- **WHEN** a user opens `/compare` with report URL state for `[group_c, group_a]`
- **THEN** those two groups are pre-selected and the cold-load default does NOT override the URL state

#### Scenario: Fewer than two groups available
- **WHEN** only one model group exists in the data
- **THEN** the cold-load default selects that single group
- **AND** the page surfaces its existing "Select at least two models to compare fixture reliability" copy
