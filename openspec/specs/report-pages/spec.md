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

### Requirement: Model Detail page includes "Compare" button
The Model Detail page SHALL include a "Compare →" button that navigates to `/compare?with=<encoded-model-name>`, pre-selecting the current model.

#### Scenario: Compare button navigates to Compare page
- **WHEN** a user clicks "Compare →" on `/models/gpt-4o%23high`
- **THEN** the browser navigates to `/compare?with=gpt-4o%23high` with that model pre-selected

### Requirement: Model Detail page shows reasoning level comparison when applicable
When a base model has been run at multiple reasoning levels, the Model Detail page SHALL display a reasoning level comparison section showing the pass rate delta per benchmark between levels, sorted by delta magnitude.

#### Scenario: Reasoning comparison renders when multiple levels exist
- **WHEN** navigating to a model detail page for a base model with runs at `high`, `medium`, and `low`
- **THEN** a comparison table or chart shows per-benchmark pass rates for each reasoning level

#### Scenario: No reasoning comparison for single-level models
- **WHEN** navigating to a model detail page for a model with only one reasoning level
- **THEN** no reasoning comparison section is displayed

### Requirement: Benchmark Detail page shows leaderboard and per-fixture comparison
The Benchmark Detail page (`benchmarks/[name].astro`) SHALL render the benchmark description, a model leaderboard bar chart (React island) showing pass rates for this specific benchmark only, a per-fixture comparison table (`FixtureComparisonTable` React island) showing pass/fail and similarity for each selected model with its own synced `ModelSelector`, and a tag breakdown chart.

#### Scenario: Leaderboard shows per-benchmark pass rates for all selected models
- **WHEN** navigating to `/benchmarks/commit_messages`
- **THEN** the `PassRateBarChart` is rendered with `benchmarkName="commit_messages"` and displays pass rates computed only from the `commit_messages` fixture set, not the global 204-fixture average

#### Scenario: Per-fixture table uses synced model selection
- **WHEN** navigating to `/benchmarks/commit_messages` with model selection `["anthropic/claude-opus-4.7", "openai/gpt-4o"]`
- **THEN** the fixture comparison table shows only those model groups' efforts as columns

#### Scenario: Per-fixture table has its own ModelSelector
- **WHEN** viewing the per-fixture comparison section
- **THEN** a `ModelSelector` widget appears above the table; changing it updates the table columns and syncs across all other selectors on the site

#### Scenario: Clicking a fixture row navigates
- **WHEN** a user clicks a fixture row in the comparison table
- **THEN** the browser navigates to `/fixtures/<benchmark>/<fixture-id>`

#### Scenario: Fixture cells show similarity scores with pass/fail coloring
- **WHEN** a model passed a fixture with 100% similarity
- **THEN** the cell shows "100.0%" in a pass-colored badge

#### Scenario: Missing fixture results show dash
- **WHEN** a model has no result for a fixture
- **THEN** the cell displays "—" in dim text

### Requirement: Fixture Detail page shows full prompt, expected, and all model outputs
The Fixture Detail page (`fixtures/[fixture].astro`) SHALL render the fixture metadata (id, description, purpose, difficulty, tags), the full prompt text in a monospace block, the full expected text in a monospace block, and all model outputs as static `ModelOutputCard` components showing model name, pass/fail badge, similarity score, and full output text. Each block SHALL include a copy-to-clipboard button.

#### Scenario: Full prompt is displayed in monospace
- **WHEN** navigating to `/fixtures/f001`
- **THEN** the complete prompt text is displayed in a monospace block with a copy button

#### Scenario: All model outputs are displayed
- **WHEN** navigating to `/fixtures/f001`
- **THEN** a card is rendered for each model that ran this fixture, showing the model name, similarity, pass/fail, and full output

#### Scenario: Copy button copies text to clipboard
- **WHEN** a user clicks the copy button on the prompt block
- **THEN** the full prompt text is copied to the system clipboard

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
The History page (`history.astro`) SHALL render a static run log table showing timestamp, model, pass rate, suite version, and delta from previous run. It SHALL include a React island time series chart showing pass rate over time per selected model. Expanding a run row SHALL show the specific fixtures that regressed or improved compared to the previous run of the same model.

#### Scenario: Run log table is rendered statically
- **WHEN** navigating to `/history`
- **THEN** a table displays all runs sorted by timestamp descending, without requiring JavaScript

#### Scenario: Time series chart shows pass rate over calendar time
- **WHEN** the History page loads and React hydrates
- **THEN** a line chart displays pass rate over time for each selected model

#### Scenario: Expanding a run row shows fixture deltas
- **WHEN** a user clicks to expand a run row
- **THEN** the expanded area lists fixtures whose pass status or similarity changed significantly from the previous run

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
The model level page (`/models/[provider]/[model]/[level]/`) SHALL display: the full model identity (provider icon, base model, level), a reasoning level tab bar linking to sibling levels of the same base model and sorted by effort order, a summary stats area (pass rate, total cost, input/output token counts), a "Compare" button linking to `/compare?with=<encoded-full-model-name>`, and a fixture gallery with filter controls (benchmark, difficulty, tag). Fixture gallery filter controls SHALL be implemented using plain JavaScript (no TypeScript syntax) so they execute correctly in the browser. Difficulty values in the filter dropdown SHALL be sorted by difficulty order (trivial, easy, medium, hard, expert), not alphabetically. The token summary in the header SHALL display separate input and output token counts (e.g., "15.2K in / 48.7K out tokens") rather than a single total.

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
- **THEN** the browser navigates to `/compare?with=anthropic%2Fclaude-opus-4.7%3Alow`

### Requirement: Model summary card shows total cost not average cost
Any card displaying model cost data SHALL show `total_cost_usd` (total cost of the full evaluation run), not `avg_cost_usd` (average cost per fixture). Cost SHALL be formatted in USD with appropriate precision for the magnitude.

#### Scenario: Card shows total cost
- **WHEN** a model summary card renders and has `total_cost_usd=0.526615`
- **THEN** the card displays "Cost: $0.527" (or similar precision)

#### Scenario: Card handles missing cost data
- **WHEN** a model has no cost data (`total_cost_usd=null`)
- **THEN** no cost information is displayed on the card

### Requirement: Report pages support output-mode selection
Report pages with model selection SHALL provide an output-mode control that lets users view text results, JSON-schema results, or both when both modes exist in the report data.

#### Scenario: Output mode defaults to text
- **WHEN** a report page loads and no output mode is selected
- **THEN** text-mode results are shown by default

#### Scenario: Both modes expand selected models
- **WHEN** the user selects both output modes
- **THEN** charts and tables show separate text and JSON-schema variants for each selected model effort

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

The Model Detail page SHALL display total reasoning tokens alongside input and output tokens when the model has a reasoning level. When the model does not have a reasoning level, reasoning tokens SHALL be omitted from the display.

#### Scenario: Reasoning tokens shown for reasoning model
- **WHEN** navigating to a model detail page for `o3-mini#high` with 1,500 total reasoning tokens across all fixtures
- **THEN** the stats line reads "127 in / 16 out / 1,500 reasoning tokens" or similar

#### Scenario: No reasoning tokens for non-reasoning model
- **WHEN** navigating to a model detail page for `granite-4.1-8b` with no reasoning level
- **THEN** the stats line reads "127 in / 16 out tokens" with no reasoning mention

#### Scenario: Reasoning model with zero reasoning tokens
- **WHEN** navigating to a model detail page for a model with `reasoning_level: "high"` but all reasoning_tokens are 0
- **THEN** the stats line reads "127 in / 16 out / 0 reasoning tokens"

### Requirement: ModelOutputCard displays reasoning tokens in compact badge

The `ModelOutputCard` component SHALL display reasoning tokens in its inline token badge when the fixture result includes a reasoning level. The format SHALL be `{input}→{output}(+{reasoning}r)` where the `(+{reasoning}r)` portion is only present when reasoning level is set.

#### Scenario: Reasoning tokens in output card badge
- **WHEN** a fixture result has `input_tokens: 127`, `output_tokens: 16`, `reasoning_tokens: 150`, and `reasoning_level: "high"`
- **THEN** the token badge reads "127→16(+150r)"

#### Scenario: No reasoning portion without reasoning level
- **WHEN** a fixture result has `input_tokens: 127`, `output_tokens: 16`, and `reasoning_level: null`
- **THEN** the token badge reads "127→16"

#### Scenario: Reasoning level set but reasoning_tokens is null
- **WHEN** a fixture result has `reasoning_level: "high"` but `reasoning_tokens: null`
- **THEN** the token badge reads "127→16(+N/A)"

### Requirement: FixtureCard displays reasoning tokens when present

The `FixtureCard` component SHALL display a third column for reasoning tokens when the fixture result includes a reasoning level. Without a reasoning level, the card SHALL retain its existing two-column (Input | Output) layout.

#### Scenario: FixtureCard with reasoning data
- **WHEN** a fixture card renders for a result with `input_tokens: 127`, `output_tokens: 16`, `reasoning_tokens: 150`, and `reasoning_level: "high"`
- **THEN** the card shows three columns: Input (127), Output (16), Reason (150)

#### Scenario: FixtureCard without reasoning level
- **WHEN** a fixture card renders for a result with `reasoning_level: null`
- **THEN** the card shows two columns: Input and Output only

#### Scenario: FixtureCard with reasoning level but null reasoning_tokens
- **WHEN** a fixture card renders with `reasoning_level: "high"` and `reasoning_tokens: null`
- **THEN** the Reason column shows "N/A"

