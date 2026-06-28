## ADDED Requirements

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

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Selection changes persist to localStorage
**Reason**: Report view state must be shareable and must not cause stale selections on bare URLs as new models are benchmarked.

**Migration**: Use report URL state as the source of truth. Existing `gitbench-model-selection` values MAY remain in users' browsers but SHALL NOT initialize report/chart page model selection.
