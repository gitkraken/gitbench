## Purpose

Report pages provide the page-level structure for the benchmark report, including grouped model listings, drill-down fixture galleries, comparison views, and supporting informational pages.
## Requirements
### Requirement: Dashboard includes overview charts
The Dashboard SHALL include React island charts: an overall pass rate bar chart, a pass-by-difficulty stacked bar chart, and an interactive benchmark × model heatmap. Charts SHALL be accompanied by a shared `ModelSelector` island.

#### Scenario: Pass rate bar chart renders
- **WHEN** the Dashboard loads and React hydrates
- **THEN** a horizontal bar chart displays pass rate per selected model

#### Scenario: Heatmap renders with model and benchmark axes
- **WHEN** the Dashboard loads and React hydrates
- **THEN** a heatmap displays benchmarks as rows, selected models as columns, with cells colored by pass rate

#### Scenario: Clicking a heatmap cell navigates
- **WHEN** a user clicks a cell in the heatmap
- **THEN** the browser navigates to the corresponding Benchmark Detail page

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

### Requirement: Model Detail page includes "Compare" button
The Model Detail page SHALL include a "Compare" button that navigates to `/compare` with report URL state pre-selecting the current model group. The Compare page SHALL also accept existing `/compare?with=<encoded-model-name>` links for backward compatibility.

#### Scenario: Compare button navigates to Compare page
- **WHEN** a user clicks "Compare" on `/models/gpt-4o%23high`
- **THEN** the browser navigates to `/compare` with report URL state that pre-selects that model's provider/base-model group

#### Scenario: Legacy Compare URL remains accepted
- **WHEN** a user opens `/compare?with=gpt-4o%23high`
- **THEN** the Compare page pre-selects the model group containing `gpt-4o#high`

### Requirement: Model Detail page shows reasoning level comparison when applicable
When a base model has been run at multiple reasoning levels, the Model Detail page SHALL display a reasoning level comparison section showing the pass rate delta per benchmark between levels, sorted by delta magnitude.

#### Scenario: Reasoning comparison renders when multiple levels exist
- **WHEN** navigating to a model detail page for a base model with runs at `high`, `medium`, and `low`
- **THEN** a comparison table or chart shows per-benchmark pass rates for each reasoning level

#### Scenario: No reasoning comparison for single-level models
- **WHEN** navigating to a model detail page for a model with only one reasoning level
- **THEN** no reasoning comparison section is displayed

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

### Requirement: Fixture Detail page shows full prompt, expected, and all model outputs
The Fixture Detail page (`fixtures/[fixture].astro`) SHALL render the fixture metadata (id, description, purpose, difficulty, tags), the full prompt text in a monospace block, the full expected text in a monospace block, and all model outputs as static `ModelOutputCard` components showing model name, pass/fail badge, similarity score, and full output text. Each block SHALL include a copy-to-clipboard button. For JSON-schema mode outputs with structured-output parse or schema errors, the output card SHALL display a clear structured-output failure message that includes the raw model output.

#### Scenario: Full prompt is displayed in monospace
- **WHEN** navigating to `/fixtures/f001`
- **THEN** the complete prompt text is displayed in a monospace block with a copy button

#### Scenario: All model outputs are displayed
- **WHEN** navigating to `/fixtures/f001`
- **THEN** a card is rendered for each model that ran this fixture, showing the model name, similarity, pass/fail, and full output

#### Scenario: Copy button copies text to clipboard
- **WHEN** a user clicks the copy button on the prompt block
- **THEN** the full prompt text is copied to the system clipboard

#### Scenario: Invalid structured JSON message is displayed
- **WHEN** a JSON-schema mode fixture result has a structured-output parse error and raw structured output
- **THEN** the model output card displays `Invalid JSON. Output: <raw structured output>`
- **AND** the page remains renderable because the report artifact is valid JSON

#### Scenario: Invalid structured schema message is displayed
- **WHEN** a JSON-schema mode fixture result has a structured-output schema error and raw structured output
- **THEN** the model output card displays `Invalid structured output. Output: <raw structured output>`
- **AND** the raw structured output is available through the output card copy behavior

### Requirement: Explore page provides tag-based fixture search
The Explore page (`explore.astro`) SHALL render a tag cloud showing all tags with fixture counts, and filter controls for tag, difficulty, and benchmark. Difficulty filter dropdown options SHALL be sorted by difficulty order (trivial, easy, medium, hard, expert), not alphabetically. Selecting tags or difficulty levels SHALL filter the fixture list to show matching fixtures.

#### Scenario: Tag cloud displays all tags
- **WHEN** navigating to `/explore`
- **THEN** all tags from the dataset are displayed with fixture counts

#### Scenario: Clicking a tag filters results
- **WHEN** a user clicks a tag in the tag cloud
- **THEN** the filtered results list shows only fixtures matching that tag

#### Scenario: Multiple filters combine with AND logic
- **WHEN** a user selects tag "rename" and difficulty "medium"
- **THEN** only fixtures matching BOTH criteria are displayed

#### Scenario: Difficulty dropdown sorted by difficulty order
- **WHEN** navigating to `/explore`
- **THEN** the difficulty filter dropdown options appear in order: trivial, easy, medium, hard, expert

### Requirement: Compare page enables multi-model analysis
The Compare page (`compare.astro`) SHALL be a React island component that provides: a multi-select model picker at the top, an overall pass rate comparison bar chart, a per-benchmark grouped comparison chart, a head-to-head scatter plot for two chosen models, an agreement matrix for the same two models, and a per-fixture detail table across all selected models. When `Both` output modes are selected, both bar charts SHALL pair text and JSON-schema results under canonical model-effort identities rather than presenting `__json_schema` variants as unrelated models. Text bars SHALL use each chart's solid base color and JSON bars SHALL use the same base color with reduced fill opacity and a visible outline. Both charts SHALL provide a mode-style legend and one pair-level tooltip from either sibling bar with separate `Text` and `JSON` sections.

#### Scenario: Model selection updates all comparison sections
- **WHEN** a user adds or removes models in the Compare page selector
- **THEN** all comparison sections (overall, by benchmark, head-to-head, per-fixture) update to reflect the new selection

#### Scenario: Overall chart pairs output modes by model effort
- **WHEN** `Both` is selected and a reasoning effort has text and JSON-schema pass-rate summaries
- **THEN** the overall chart renders one canonical model-effort label with adjacent text and JSON bars

#### Scenario: Overall pair shares one tooltip
- **WHEN** a user hovers or keyboard-focuses either sibling in the overall pass-rate chart
- **THEN** one tooltip shows separate `Text` and `JSON` pass-rate sections for that canonical model effort

#### Scenario: Overall chart sorts by mean pass rate in Both mode
- **WHEN** `Both` is selected and a model effort has both text and JSON pass rates
- **THEN** the overall chart sorts its canonical model-effort category by the mean of those two pass rates

#### Scenario: Per-benchmark chart pairs model series
- **WHEN** `Both` is selected
- **THEN** each benchmark category renders every canonical model effort's text and JSON bars consecutively with compact spacing inside the pair

#### Scenario: Per-benchmark pair shares one scoped tooltip
- **WHEN** a user hovers either output-mode bar for one model effort on a benchmark
- **THEN** one tooltip shows that benchmark and model effort with separate `Text` and `JSON` pass-rate sections
- **AND** the tooltip does not include unrelated selected models

#### Scenario: Compare legends hide storage suffixes
- **WHEN** `Both` is selected
- **THEN** model legends and labels use canonical model-effort identities without displaying the `__json_schema` suffix
- **AND** a separate mode legend explains the text and JSON bar treatments

#### Scenario: Missing mode remains explicit
- **WHEN** a model effort has only one output mode for an overall or per-benchmark value
- **THEN** the available bar remains grouped under the canonical identity and the shared tooltip labels the other mode `No data`

#### Scenario: Single mode renders one bar per model effort
- **WHEN** `Text` or `JSON` is selected
- **THEN** both Compare bar charts render only the selected mode without reserving an empty sibling slot

#### Scenario: Head-to-head scatter plot renders per-fixture dots
- **WHEN** two models are selected for head-to-head comparison
- **THEN** a scatter plot displays one dot per fixture, with X = model A similarity, Y = model B similarity

#### Scenario: Agreement matrix shows pass/fail overlap
- **WHEN** two models are selected for head-to-head comparison
- **THEN** a 2×2 matrix shows counts of: both pass, both fail, A-only pass, B-only pass

#### Scenario: Pre-selection from query parameter
- **WHEN** navigating to `/compare?with=gpt-4o%23high`
- **THEN** `gpt-4o#high` is pre-selected in the model picker

### Requirement: History page shows run history and time series
The History page (`history.astro`) SHALL render campaign records as the primary evaluation timeline when campaign data exists. Each campaign node or row SHALL show campaign identity, evaluation date, status, trial counts, mean success, valid attempts, and delta from the previous compatible campaign when available. The page MAY retain legacy run history and time-series behavior as a fallback for reports that contain only single-run aggregate data.

#### Scenario: Campaign timeline is rendered
- **WHEN** navigating to `/history` with campaign records available
- **THEN** the page displays campaign nodes or rows sorted by evaluation time
- **AND** each row includes status, trial counts, mean success, valid attempts, and compatibility-aware delta where available

#### Scenario: Time series chart uses campaign nodes
- **WHEN** the History page loads and campaign records exist
- **THEN** the time series chart SHALL use campaign-level points rather than independent trial rows

#### Scenario: Legacy run history fallback
- **WHEN** the report contains no campaign records but contains legacy run history
- **THEN** the History page MAY display the legacy run log and run-level time series

### Requirement: Ordinary report pages omit campaign controls

Overview, Models, Benchmarks, Explore, Compare, Methodology, and Fixture pages SHALL NOT render a campaign selector or a "No campaigns" campaign empty state. These pages SHALL use the default latest evaluation data supplied by the report APIs or store helpers.

#### Scenario: Overview has no campaign selector

- **WHEN** a user opens the Overview page
- **THEN** the page header SHALL NOT include a campaign selector
- **AND** the page SHALL NOT show "No campaigns" when aggregate report data exists

#### Scenario: Campaign-specific fixture evidence remains available

- **WHEN** a user navigates to a fixture evidence view from History or a raw-attempt link
- **THEN** campaign-specific raw attempt details MAY be shown for that evidence context

### Requirement: Models index page groups by provider and base model
The Models index page (`/models`) SHALL render models grouped by provider, then by base model within each provider. Each provider section SHALL display the provider brand icon and provider name as a header. Within each provider section, base models SHALL be displayed as cards containing sub-cards for each reasoning level. Reasoning level sub-cards SHALL be sorted by reasoning effort order: default/none, low, medium, high, xhigh, max. Each level sub-card SHALL show: the level name, pass rate percentage (color-coded), and total cost in USD. Clicking a level sub-card SHALL navigate to `/models/<provider>/<base-model>/<level>/`.

#### Scenario: Models grouped by provider
- **WHEN** the Models page renders with models from anthropic and openai
- **THEN** two provider sections appear: "Anthropic" (with its icon) and "OpenAI" (with its icon)

#### Scenario: Reasoning levels as sub-cards under base model
- **WHEN** anthropic/claude-opus-4.7 has runs at low, medium, high, xhigh, and max
- **THEN** five level sub-cards appear inside the claude-opus-4.7 card, each showing its pass rate and total cost

#### Scenario: Reasoning levels sorted by effort order
- **WHEN** a base model has levels "high", "low", "medium", "default"
- **THEN** the sub-cards appear in order: default, low, medium, high

#### Scenario: Clicking a level sub-card navigates to drill-down
- **WHEN** a user clicks the "low" sub-card under claude-opus-4.7
- **THEN** the browser navigates to `/models/anthropic/claude-opus-4.7/low/`

### Requirement: Base model overview page shows level comparison
The base model overview page (`/models/[provider]/[model]/`) SHALL display the provider icon, provider name, and base model name as a header. Below, it SHALL render reasoning level cards sorted by effort order (default/none, low, medium, high, xhigh, max) showing pass rate and total cost for each level. Each card SHALL link to the level's fixture gallery page.

#### Scenario: Level cards displayed for base model
- **WHEN** navigating to `/models/anthropic/claude-opus-4.7/`
- **THEN** cards for low, medium, high, xhigh, and max are displayed with pass rates and costs, in ascending effort order

#### Scenario: Header shows provider and base model
- **WHEN** navigating to `/models/anthropic/claude-opus-4.7/`
- **THEN** the page heading includes the Anthropic icon and "Anthropic / claude-opus-4.7"

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

### Requirement: Model summary card shows total cost not average cost
Any card displaying model cost data SHALL show `total_cost_usd` (total cost of the full evaluation run), not `avg_cost_usd` (average cost per fixture). Cost SHALL be formatted in USD with appropriate precision for the magnitude.

#### Scenario: Card shows total cost
- **WHEN** a model summary card renders and has `total_cost_usd=0.526615`
- **THEN** the card displays "Cost: $0.527" (or similar precision)

#### Scenario: Card handles missing cost data
- **WHEN** a model has no cost data (`total_cost_usd=null`)
- **THEN** no cost information is displayed on the card

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

### Requirement: Model detail page compares text and structured modes
The model level detail page SHALL show an output-mode comparison section when the current provider/base-model/reasoning level has both text and JSON-schema results.

#### Scenario: Comparison section shows aggregate delta
- **WHEN** the current model effort has both text and JSON-schema results
- **THEN** the page shows the pass-rate delta between JSON-schema and text modes
- **AND** it shows gained, lost, unchanged-pass, and unchanged-fail fixture counts

#### Scenario: Comparison section shows benchmark deltas
- **WHEN** both output modes have benchmark summary data
- **THEN** the page shows per-benchmark pass-rate deltas sorted by absolute delta

#### Scenario: Comparison section links fixture changes
- **WHEN** a fixture pass/fail status differs between text and JSON-schema modes
- **THEN** the comparison table includes a link to that fixture detail page

### Requirement: Fixture detail page displays structured fields
The fixture detail page SHALL display structured-output payload data with meaningful field labels when an output came from JSON-schema mode, while still showing canonical scorer text.

#### Scenario: Structured output card shows canonical and structured data
- **WHEN** a fixture output has a parsed structured payload
- **THEN** the output card shows the canonical scorer text and the structured field payload

#### Scenario: Structured error is visible
- **WHEN** a fixture output has a structured-output parse or validation error
- **THEN** the output card shows the structured-output error alongside the normal pass/fail state

### Requirement: History page distinguishes output modes
Run history SHALL identify the output mode for each run and SHALL compare deltas only against prior runs with the same model identity and output mode unless the user explicitly selects a cross-mode comparison.

#### Scenario: Run log shows mode
- **WHEN** the history table renders a JSON-schema run
- **THEN** the row identifies the run as JSON-schema mode

#### Scenario: Delta uses matching mode
- **WHEN** computing the previous-run delta for a text-mode run
- **THEN** only prior text-mode runs for the same model are considered

### Requirement: Model Detail page displays reasoning token count
The Model Detail page SHALL display total reasoning tokens alongside input and provider-reported total output tokens when the model has a reasoning level. The label SHALL make clear that reasoning tokens are included within total output rather than additional to it. When the model does not have a reasoning level, reasoning tokens SHALL be omitted from the display.

#### Scenario: Reasoning tokens shown as included output
- **WHEN** a model detail page has 127 input tokens, 166 total output tokens, and 150 reasoning tokens
- **THEN** the stats line SHALL identify 166 as total output and 150 as reasoning included within that output

#### Scenario: No reasoning tokens for non-reasoning model
- **WHEN** navigating to a model detail page for `granite-4.1-8b` with no reasoning level
- **THEN** the stats line SHALL show input and output tokens with no reasoning mention

#### Scenario: Reasoning model with zero reasoning tokens
- **WHEN** navigating to a model detail page for a model with `reasoning_level: "high"` but all reasoning tokens are 0
- **THEN** the stats line SHALL identify 0 reasoning tokens within total output

### Requirement: ModelOutputCard displays reasoning tokens in compact badge
The `ModelOutputCard` component SHALL display provider-reported output and reasoning tokens in its inline token badge when the fixture result includes a reasoning level. The badge SHALL state that reasoning belongs to output and SHALL not use additive `(+Nr)` notation.

#### Scenario: Reasoning tokens in output card badge
- **WHEN** a fixture result has `input_tokens: 127`, `output_tokens: 166`, `reasoning_tokens: 150`, and `reasoning_level: "high"`
- **THEN** the token badge SHALL read `127 in → 166 out (150 reasoning)` or an equivalently explicit compact label

#### Scenario: No reasoning portion without reasoning level
- **WHEN** a fixture result has `input_tokens: 127`, `output_tokens: 16`, and `reasoning_level: null`
- **THEN** the token badge SHALL show 127 input and 16 output tokens without a reasoning portion

#### Scenario: Reasoning level set but reasoning tokens are unavailable
- **WHEN** a fixture result has `reasoning_level: "high"` but `reasoning_tokens: null`
- **THEN** the token badge SHALL identify reasoning as unavailable without implying an additive token count

### Requirement: FixtureCard displays reasoning tokens when present
The `FixtureCard` component SHALL display a third token column when the fixture result includes a reasoning level. The output column SHALL be labeled as total output and the reasoning column SHALL be presented as a subset of that output. Without a reasoning level, the card SHALL retain its existing two-column input/output layout.

#### Scenario: FixtureCard with reasoning data
- **WHEN** a fixture card renders with input 127, total output 166, and reasoning 150
- **THEN** the card SHALL show Input (127), Total output (166), and Reasoning within output (150)

#### Scenario: FixtureCard without reasoning level
- **WHEN** a fixture card renders with `reasoning_level: null`
- **THEN** the card SHALL show two columns: Input and Output

#### Scenario: FixtureCard with unavailable reasoning count
- **WHEN** a fixture card renders with a reasoning level but `reasoning_tokens: null`
- **THEN** the reasoning column SHALL show `N/A`

### Requirement: Report pages preserve campaign selection

Overview, model, benchmark, fixture, compare, history, model-index, and directory report pages SHALL resolve campaign-sensitive data from the shared selected campaign.

#### Scenario: Navigate from overview to a fixture

- **WHEN** a user selects a campaign and follows a link from overview to a fixture page
- **THEN** the fixture page SHALL show data from the same campaign

### Requirement: Overview reports campaign reliability

The overview SHALL present mean one-attempt success, valid attempt counts, planned and completed trials, and campaign completeness for each ranked model configuration.

#### Scenario: View an overview model row

- **WHEN** a complete five-trial campaign is selected
- **THEN** the row SHALL display its mean success rate and five completed trials
- **AND** trial variability SHALL be available without changing the meaning of reasoning-effort range visuals

### Requirement: Model detail reports stability classifications

Model detail pages SHALL report stable-pass, flaky, and stable-fail fixture counts by benchmark and output mode and SHALL provide access to underlying attempts.

#### Scenario: Inspect model flakiness

- **WHEN** a model has fixtures with mixed outcomes across trials
- **THEN** the model page SHALL identify those fixtures as flaky
- **AND** it SHALL show pass counts and denominators

### Requirement: Benchmark and fixture pages aggregate repeated attempts

Benchmark pages SHALL display per-fixture reliability aggregates, and fixture pages SHALL display per-model and output-mode attempt aggregates with expandable raw evidence.

#### Scenario: View a benchmark cell

- **WHEN** a model passes a fixture four times in five valid attempts
- **THEN** the benchmark cell SHALL display `4/5` or equivalent explicit text
- **AND** it SHALL be identified as flaky

#### Scenario: Expand fixture attempts

- **WHEN** a user expands an aggregate on a fixture page
- **THEN** each trial SHALL show output, score, validation state, provider provenance, judge evidence, cost, tokens, and API time when available

### Requirement: Compare pages use reliability deltas

Compare pages SHALL compare fixture pass probabilities and attempt counts rather than treating a repeated campaign as one binary gained, lost, or agreed outcome.

#### Scenario: Compare output modes

- **WHEN** structured output passes four of five attempts and text passes two of five for the same fixture
- **THEN** the comparison SHALL classify structured output as more reliable
- **AND** it SHALL display both attempt ratios

### Requirement: History groups trials under campaigns

The history page SHALL use campaigns as primary rows or points and SHALL expose trials as nested detail.

#### Scenario: Calculate a historical delta

- **WHEN** two campaigns have compatible inputs and configuration
- **THEN** history MAY calculate the change in mean success rate
- **WHEN** they are incompatible
- **THEN** history SHALL withhold the delta and explain why

### Requirement: Model detail page lays out comparison sections without an empty central column

The Model Detail page SHALL render
(`/models/[provider]/[model]/[level]`) with the
"Reliability by Benchmark" section and the "Text vs JSON Schema
Comparison" section as full-width blocks at desktop and tablet widths.
Neither section SHALL use a multi-column grid that leaves more than
~10% of its width as empty whitespace between the metadata block and
the data block.

#### Scenario: Reliability section is a single full-width block
- **WHEN** a user navigates to `/models/<provider>/<base-model>/<level>/` at a desktop viewport
- **THEN** the "Reliability by Benchmark" section's content occupies the full available width inside its `.card` wrapper
- **AND** the left and right blocks of that section are stacked vertically (or the data table fills the full row) with no empty central column wider than ~10% of the section

#### Scenario: Text vs JSON comparison section is a single full-width block
- **WHEN** a user navigates to `/models/<provider>/<base-model>/<level>/` at a desktop viewport
- **THEN** the "Text vs JSON Schema Comparison" section's content occupies the full available width inside its `.card` wrapper
- **AND** the four summary tiles and the benchmark delta table are not split into two side-by-side groups separated by empty whitespace

#### Scenario: Tablet layout already single-column is preserved
- **WHEN** a user navigates to `/models/<provider>/<base-model>/<level>/` at a tablet viewport (601–960px)
- **THEN** both sections continue to render as a single column without regression
