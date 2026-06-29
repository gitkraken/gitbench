## ADDED Requirements

### Requirement: Report pages use URL-backed view state
Report pages with comparative model or output-mode controls SHALL resolve model selection and output mode from report URL state. Missing or invalid report URL state SHALL fall back to the page default instead of reading stale browser storage.

#### Scenario: Bare overview uses current defaults
- **WHEN** a user opens `/` with no report URL state
- **THEN** the Overview page selects all current model groups and defaults to both output modes when both are available

#### Scenario: Bare benchmark uses current defaults
- **WHEN** a user opens `/benchmarks/rebase` with no report URL state
- **THEN** the Benchmark Detail page selects all current model groups and defaults to both output modes when both are available

#### Scenario: Sidebar navigation resets view state
- **WHEN** a user has a narrowed model selection on Overview
- **AND** the user clicks a top-level sidebar link such as Compare or Methodology
- **THEN** the destination URL does not carry the narrowed model selection unless that link is explicitly an analytical drilldown

#### Scenario: Invalid state falls back
- **WHEN** a report page URL contains invalid compressed report view state
- **THEN** the page renders using its default model selection and output mode

### Requirement: Analytical drilldowns preserve report view state
Report pages SHALL preserve report view state only for links that continue the same comparative analysis context. Ordinary navigation links SHALL remain bare.

#### Scenario: Overview heatmap to benchmark preserves state
- **WHEN** a user has selected `["openai/gpt-5"]` and output mode `json_schema` on Overview
- **AND** the user follows a heatmap link to `/benchmarks/rebase`
- **THEN** the Benchmark Detail URL contains report view state resolving to the same selection and output mode

#### Scenario: Ordinary model directory link does not preserve state
- **WHEN** a user has selected `["openai/gpt-5"]` on Overview
- **AND** the user navigates to `/models` through the sidebar
- **THEN** the `/models` URL does not include model-selection report view state

### Requirement: Compare page accepts legacy with links
The Compare page SHALL accept existing `/compare?with=<model-or-group>` links as a backward-compatible seed for selected model groups. After resolving a valid legacy seed, Compare SHALL use the new report URL state for subsequent selection changes.

#### Scenario: Legacy with parameter still preselects
- **WHEN** navigating to `/compare?with=gpt-4o%23high`
- **THEN** `gpt-4o#high` is pre-selected in the model picker when it maps to a known model group

#### Scenario: URL state wins over legacy seed
- **WHEN** a Compare URL contains both valid report URL state and `with=gpt-4o%23high`
- **THEN** the report URL state determines the selected model groups

## MODIFIED Requirements

### Requirement: Model Detail page includes "Compare" button
The Model Detail page SHALL include a "Compare" button that navigates to `/compare` with report URL state pre-selecting the current model group. The Compare page SHALL also accept existing `/compare?with=<encoded-model-name>` links for backward compatibility.

#### Scenario: Compare button navigates to Compare page
- **WHEN** a user clicks "Compare" on `/models/gpt-4o%23high`
- **THEN** the browser navigates to `/compare` with report URL state that pre-selects that model's provider/base-model group

#### Scenario: Legacy Compare URL remains accepted
- **WHEN** a user opens `/compare?with=gpt-4o%23high`
- **THEN** the Compare page pre-selects the model group containing `gpt-4o#high`

### Requirement: Benchmark Detail page shows leaderboard and per-fixture comparison
The Benchmark Detail page (`benchmarks/[name].astro`) SHALL render the benchmark description, a model leaderboard bar chart (React island) showing pass rates for this specific benchmark only, a per-fixture comparison table (`FixtureComparisonTable` React island) showing pass/fail and similarity for each selected model with its own synced `ModelSelector`, and a tag breakdown chart. Model and output-mode selection SHALL initialize from report URL state when present, otherwise from the Benchmark Detail page defaults.

#### Scenario: Leaderboard shows per-benchmark pass rates for selected models
- **WHEN** navigating to `/benchmarks/commit_messages` with report URL state for model selection `["anthropic/claude-opus-4.7", "openai/gpt-4o"]`
- **THEN** the `PassRateBarChart` is rendered with `benchmarkName="commit_messages"` and displays pass rates computed only from the `commit_messages` fixture set for that selection

#### Scenario: Bare benchmark selects all model groups
- **WHEN** navigating to `/benchmarks/commit_messages` without report URL state
- **THEN** the model leaderboard and fixture comparison table select all current model groups

#### Scenario: Per-fixture table uses synced model selection
- **WHEN** navigating to `/benchmarks/commit_messages` with model selection `["anthropic/claude-opus-4.7", "openai/gpt-4o"]`
- **THEN** the fixture comparison table shows only those model groups' efforts as columns

#### Scenario: Per-fixture table has its own ModelSelector
- **WHEN** viewing the per-fixture comparison section
- **THEN** a `ModelSelector` widget appears above the table; changing it updates the table columns and syncs across all other selectors on the page

#### Scenario: Clicking a fixture row navigates
- **WHEN** a user clicks a fixture row in the comparison table
- **THEN** the browser navigates to `/fixtures/<benchmark>/<fixture-id>`

#### Scenario: Fixture cells show similarity scores with pass/fail coloring
- **WHEN** a model passed a fixture with 100% similarity
- **THEN** the cell shows "100.0%" in a pass-colored badge

#### Scenario: Missing fixture results show dash
- **WHEN** a model has no result for a fixture
- **THEN** the cell displays "-" in dim text

### Requirement: Model level drill-down page shows fixture gallery
The model level page (`/models/[provider]/[model]/[level]/`) SHALL display: the full model identity (provider icon, base model, level), a reasoning level tab bar linking to sibling levels of the same base model and sorted by effort order, a summary stats area (pass rate, total cost, input/output token counts), a "Compare" button linking to `/compare` with report URL state for the current model group, and a fixture gallery with filter controls (benchmark, difficulty, tag). Fixture gallery filter controls SHALL be implemented using plain JavaScript (no TypeScript syntax) so they execute correctly in the browser. Difficulty values in the filter dropdown SHALL be sorted by difficulty order (trivial, easy, medium, hard, expert), not alphabetically. The token summary in the header SHALL display separate input and output token counts (e.g., "15.2K in / 48.7K out tokens") rather than a single total.

The page SHALL include a page-wide output mode toggle (Text, JSON, Both) in the fixture gallery filter bar. This toggle SHALL control the header stats, reliability summary, and fixture gallery. The toggle SHALL initialize from report URL state, write report URL state when changed, and default to Both when both modes exist and no valid URL mode is present. When the model has no JSON-schema variant, the toggle SHALL be hidden and the page SHALL display text-mode results only.

The fixture gallery SHALL pre-render three card sets at build time: text-mode cards, JSON-schema cards, and "both" compact cards. The toggle SHALL control which card set is visible via client-side visibility toggling. Existing filter controls (benchmark, difficulty, tag) SHALL apply to whichever card set is visible.

In single-mode view (Text or JSON), fixture cards SHALL display fixture ID, benchmark, pass/fail status, similarity percentage, and token counts (current `FixtureCard` behavior). In Both view, fixture cards SHALL display fixture ID, benchmark, and stacked text and JSON scores (e.g., "T 87% pass" / "J 91% pass") without token details. When a fixture exists in one mode but not the other, the missing mode SHALL show "-" for its score.

The header stats area SHALL pre-render both text and JSON summary blocks at build time. In single-mode view, the matching stats block SHALL be visible. In Both view, both stat blocks SHALL be shown stacked (text first, then JSON). The `ModelReliabilitySummary` React island SHALL read output mode from report URL state for its initial fetch and SHALL listen for the `output-mode-change` custom event to refetch when the toggle changes. In Both mode, the reliability summary SHALL show text-mode results (the "Text vs JSON Comparison" section below already covers cross-mode deltas).

The "Text vs JSON Schema Comparison" section SHALL remain unchanged. It is inherently about both modes and continues to render only when both variants exist.

#### Scenario: Tabs link to sibling levels sorted by effort order
- **WHEN** viewing `/models/anthropic/claude-opus-4.7/low/`
- **THEN** a tab bar shows sibling levels in effort order [default, low, medium, high, xhigh, max] with "low" visually active; clicking "high" navigates to `/models/anthropic/claude-opus-4.7/high/`

#### Scenario: Fixture gallery filters work
- **WHEN** user selects benchmark "git_grep" in the filter bar
- **THEN** only fixture cards for git_grep remain visible

#### Scenario: Multiple filters combine with AND logic
- **WHEN** user selects benchmark "git_grep" and difficulty "medium"
- **THEN** only fixture cards matching BOTH benchmark "git_grep" AND difficulty "medium" remain visible

#### Scenario: Reset button clears all filters
- **WHEN** user clicks the Reset button after applying filters
- **THEN** all filter dropdowns reset to "All" and all fixture cards become visible

#### Scenario: Difficulty dropdown sorted by difficulty
- **WHEN** the page renders with fixtures of difficulties "hard", "easy", "medium"
- **THEN** the difficulty filter dropdown options appear in order: easy, medium, hard

#### Scenario: Token summary shows input/output split
- **WHEN** a model level has fixtures totaling 15,200 input tokens and 48,700 output tokens
- **THEN** the header summary displays "15.2K in / 48.7K out tokens" (or similar formatting)

#### Scenario: Token summary with zero tokens
- **WHEN** a model level has no token data (all null)
- **THEN** no token summary is displayed

#### Scenario: Compare button navigates correctly
- **WHEN** user clicks "Compare" on the page for `anthropic/claude-opus-4.7:low`
- **THEN** the browser navigates to `/compare` with report URL state pre-selecting `anthropic/claude-opus-4.7`

#### Scenario: Output mode toggle defaults to both
- **WHEN** the page loads with no report output-mode URL state
- **AND** the model has both text and JSON-schema variants
- **THEN** compact both-mode cards are visible and the toggle shows "Both" as active

#### Scenario: Output mode toggle reads URL state
- **WHEN** the page loads and report URL state contains output mode `json_schema`
- **THEN** JSON fixture cards are visible and the toggle shows "JSON" as active

#### Scenario: Output mode toggle writes URL state
- **WHEN** user clicks "Both" on the toggle
- **THEN** the page URL contains report view state resolving to output mode `both` and compact both-mode cards are visible

#### Scenario: Toggle hidden when no JSON variant exists
- **WHEN** the model has no JSON-schema variant (`jsonModelName` is null)
- **THEN** the output mode toggle is not rendered and the gallery shows text cards only

#### Scenario: Both-mode card shows stacked scores
- **WHEN** the toggle is set to "Both" and fixture f001 has text similarity 87% (pass) and JSON similarity 91% (pass)
- **THEN** the card displays "T 87% pass" and "J 91% pass" stacked, without token details

#### Scenario: Both-mode card shows dash for missing mode
- **WHEN** the toggle is set to "Both" and fixture f001 has text results but no JSON results
- **THEN** the card displays "T 87% pass" and "J -"

#### Scenario: Header stats toggle between modes
- **WHEN** the user switches the toggle from "Text" to "JSON"
- **THEN** the header stats area swaps from showing text pass rate/tokens/cost to showing JSON pass rate/tokens/cost

#### Scenario: Header stats show both stacked
- **WHEN** the toggle is set to "Both"
- **THEN** the header stats area shows text stats block first, then JSON stats block below

#### Scenario: Reliability summary refetches on toggle change
- **WHEN** the user switches the toggle from "Text" to "JSON"
- **THEN** the `ModelReliabilitySummary` React island refetches from the API with `output_mode=json_schema`

#### Scenario: Reliability summary shows text in both mode
- **WHEN** the toggle is set to "Both"
- **THEN** the `ModelReliabilitySummary` shows text-mode reliability results (the comparison section below covers cross-mode deltas)

#### Scenario: Filters apply to visible card set
- **WHEN** the toggle is set to "JSON" and the user selects benchmark "merge_conflicts"
- **THEN** only JSON fixture cards for merge_conflicts remain visible

### Requirement: Report pages support output-mode selection
Report pages with model selection SHALL provide an output-mode control that lets users view text results, JSON-schema results, or both when both modes exist in the report data. Missing output-mode URL state SHALL default to both modes when both modes are available.

#### Scenario: Output mode defaults to both
- **WHEN** a report page loads and no output mode is selected
- **AND** both text and JSON-schema modes are available
- **THEN** both output modes are shown by default

#### Scenario: Both modes expand selected models
- **WHEN** the user selects both output modes
- **THEN** charts and tables show separate text and JSON-schema variants for each selected model effort

#### Scenario: Single-mode report falls back
- **WHEN** a report page loads and only text-mode results are available
- **THEN** text-mode results are shown
