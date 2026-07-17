# chart-model-presets Specification

## Purpose
Define shared chart model presets, their membership rules, selection semantics, defaults, and consistent selector presentation across report surfaces.

## Requirements

### Requirement: Shared chart model presets
Every in-scope chart model selector SHALL expose Top Performers, Frontier Models, Open Weights, Context: Up to 200K, Context: 200K–499K, Context: 500K–999K, and Context: 1M+ presets with membership resolved consistently for the active campaign.

#### Scenario: Presets appear on an in-scope chart
- **WHEN** a user opens a model selector on an overview, benchmark, model-detail, or fixture chart surface
- **THEN** the selector displays the same ordered preset controls and definitions used by other in-scope chart selectors

#### Scenario: Scoped chart lacks a preset member
- **WHEN** a centrally resolved preset contains a group that is unavailable in the current scoped chart response
- **THEN** the selector applies the preset using only members available to that chart without changing the central preset definition

### Requirement: Top Performers ranking
The Top Performers preset SHALL contain exactly the 20 highest-ranked measurable base-model groups from the active campaign's overall results, or all measurable groups when fewer than 20 exist.

For each output mode, the system SHALL calculate the median of the distinct overall pass rates across the group's effort variants. When both text and JSON-schema modes are measurable, it SHALL average those mode medians. It SHALL rank the resulting values descending and break ties by canonical `provider/baseModel` ascending.

#### Scenario: More than 20 groups have measurable results
- **WHEN** the active campaign has measurable overall pass rates for more than 20 base-model groups
- **THEN** Top Performers contains the first 20 groups under the specified ranking and tie-break rules

#### Scenario: A group has no measurable pass rate
- **WHEN** a base-model group has no measurable overall pass rate in any output mode
- **THEN** the group is excluded from Top Performers

#### Scenario: Chart response is benchmark scoped
- **WHEN** Top Performers is displayed by a benchmark- or fixture-scoped chart
- **THEN** its ordering and membership are derived from the active campaign's overall results rather than scoped pass rates

### Requirement: Metadata-based preset membership
The system SHALL derive Frontier Models, Open Weights, and context-window presets from normalized model metadata using the defined boundaries and explicit unknown handling.

#### Scenario: Closed-weight model belongs to a frontier provider
- **WHEN** a model's provider is `openai`, `anthropic`, or `google` and its weight access is `closed`
- **THEN** Frontier Models includes the model

#### Scenario: Open or unknown model belongs to a frontier provider
- **WHEN** a model from a frontier provider has `open` or `unknown` weight access
- **THEN** Frontier Models excludes the model

#### Scenario: Model has open weights
- **WHEN** a model's reviewed weight access is `open`
- **THEN** Open Weights includes the model

#### Scenario: Context-window boundary is classified
- **WHEN** a model has a known context window
- **THEN** exactly one context preset includes it using `<= 200000`, `> 200000 and < 500000`, `>= 500000 and < 1000000`, or `>= 1000000` tokens

#### Scenario: Context window is unknown
- **WHEN** a model has no known context-window size
- **THEN** every context-window preset excludes the model

### Requirement: Preset application semantics
Applying a preset SHALL replace the current selection with that preset's available concrete base-model group IDs, and the selector SHALL identify a preset as active only while its available membership exactly equals the current selection.

#### Scenario: User applies a preset
- **WHEN** the user activates Frontier Models
- **THEN** the current selection is replaced by the available Frontier Models member IDs

#### Scenario: User customizes an applied preset
- **WHEN** the user adds or removes an individual model after applying a preset
- **THEN** the selection remains valid and the preset is no longer presented as an exact active match

#### Scenario: Applied preset is shared by URL
- **WHEN** selection state is written after a preset is applied
- **THEN** the URL encodes the concrete selected group IDs rather than only the preset ID

### Requirement: Top Performers default and URL precedence
In-scope charts SHALL initialize to Top Performers when the URL contains no explicit model-selection state. Any valid explicit URL model-selection state, including an explicit empty selection, SHALL take precedence.

#### Scenario: User opens an unparameterized chart page
- **WHEN** no explicit model-selection state exists in the URL
- **THEN** the chart initializes with the available Top Performers members selected

#### Scenario: User opens a shared explicit selection
- **WHEN** the URL contains valid concrete model-selection state
- **THEN** the chart restores that state without replacing it with Top Performers

#### Scenario: URL explicitly selects no models
- **WHEN** the URL encodes an explicit empty model selection
- **THEN** the chart preserves the empty selection rather than applying Top Performers

### Requirement: Consistent enhanced selector presentation
All in-scope model-selector triggers SHALL use a uniform responsive width, and all corresponding dropdown panels SHALL use a second uniform responsive width that may be wider than the trigger. The dropdown SHALL expose search, preset controls with available-member counts, select-all and clear actions, and model rows with provider identity and available context/weight metadata.

#### Scenario: Selectors render in different chart layouts
- **WHEN** model selectors appear in chart layouts with different surrounding column widths
- **THEN** their triggers match other in-scope trigger widths and their dropdowns match other in-scope dropdown widths on the same responsive breakpoint

#### Scenario: Dropdown is wider than its trigger
- **WHEN** the selector opens on a viewport with sufficient room
- **THEN** the dropdown may use its wider shared panel width without being constrained to the trigger width

#### Scenario: Selector opens on a narrow viewport
- **WHEN** the shared trigger or panel width would overflow the available viewport
- **THEN** the component clamps its width and placement to remain usable without horizontal page overflow

#### Scenario: Metadata is unknown
- **WHEN** a model row lacks known context or weight metadata
- **THEN** the row communicates the unknown value without hiding or misclassifying the model
