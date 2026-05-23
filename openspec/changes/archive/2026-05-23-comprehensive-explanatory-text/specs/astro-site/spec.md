## ADDED Requirements

### Requirement: Overview page has expanded introduction
The Overview page (`index.astro`) About section SHALL contain 3-4 paragraphs explaining the purpose of GitBench, what it tests, and who it serves. The text SHALL be accessible to readers at all technical levels. The section SHALL remain in the existing `.card` container above the first chart.

#### Scenario: Overview has expanded intro
- **WHEN** navigating to `/`
- **THEN** the About card contains at least 3 paragraphs of explanatory prose

### Requirement: Section labels on pages support tooltip triggers
Section labels throughout the site SHALL support the `.has-tooltip` class pattern. Labels that would benefit from contextual explanation (e.g., "Model Summary", "Cost per Full Run", "Benchmark Matrix") SHALL use `<span class="has-tooltip" data-tooltip="..." title="...">` markup.

#### Scenario: Overview section labels have tooltips
- **WHEN** viewing the Overview page
- **THEN** each chart section label has a `.has-tooltip` span with explanatory data-tooltip and title attributes

#### Scenario: History page column headers have tooltips
- **WHEN** viewing the History page's Run Log table
- **THEN** each `<th>` element uses `.has-tooltip` with explanatory text for what the column represents

### Requirement: Model pages include organizational explanation
The Models index page (`models/index.astro`) SHALL include a blurb before the model cards explaining how models are organized (provider → base model → reasoning level) and what reasoning levels mean. The Model Level page (`models/[provider]/[model]/[level].astro`) SHALL include a blurb before the fixture gallery explaining what each card represents and how to use the filters.

#### Scenario: Models page has organizational blurb
- **WHEN** navigating to `/models`
- **THEN** explanatory text appears before the model cards explaining the organization and reasoning levels

#### Scenario: Model level page has gallery blurb
- **WHEN** navigating to `/models/openai/gpt-4o/high`
- **THEN** explanatory text appears above the fixture gallery explaining the cards and filters

### Requirement: Benchmark pages include contextual blurbs
The Benchmarks index page (`benchmarks/index.astro`) SHALL include a blurb explaining the 17 benchmark categories and what the Best % badge represents. The Benchmark Detail page (`benchmarks/[name].astro`) SHALL include blurbs above the leaderboard and the per-fixture comparison table.

#### Scenario: Benchmarks page has intro blurb
- **WHEN** navigating to `/benchmarks`
- **THEN** explanatory text appears before the benchmark cards explaining what benchmarks are

#### Scenario: Benchmark detail has leaderboard and table blurbs
- **WHEN** navigating to `/benchmarks/rebase`
- **THEN** the leaderboard and comparison table sections each have explanatory blurbs

### Requirement: Explore and Compare pages include usage guidance
The Explore page (`explore.astro`) SHALL include a blurb explaining that the page indexes all 204 fixtures and how to filter by tag, difficulty, or benchmark. The Compare page header area SHALL include a blurb explaining how to use the comparison and what the charts show.

#### Scenario: Explore page has usage blurb
- **WHEN** navigating to `/explore`
- **THEN** explanatory text explains what the Explore page is and how to use it

#### Scenario: Compare page has usage blurb
- **WHEN** navigating to `/compare`
- **THEN** explanatory text appears before the model selector explaining how comparison works

### Requirement: Fixture detail page includes model outputs explanation
The Fixture Detail page (`fixtures/[benchmark]/[fixture].astro`) SHALL include a blurb above the Model Outputs section explaining that all model responses are shown sorted by similarity and what PASS/FAIL means.

#### Scenario: Fixture page has model outputs blurb
- **WHEN** navigating to any fixture detail page
- **THEN** the Model Outputs section includes a brief explanatory blurb

### Requirement: History page includes column explanations
The History page (`history.astro`) SHALL include blurbs above the Time Series chart and the Run Log table. Every `<th>` element in the Run Log table SHALL have a `.has-tooltip` span with explanatory text for column headers that are not self-explanatory (Profile, Reasoning, Suite, Δ prev, Git SHA).

#### Scenario: History page has section blurbs
- **WHEN** navigating to `/history`
- **THEN** both the Time Series and Run Log sections have explanatory blurbs

#### Scenario: History table headers have tooltips
- **WHEN** viewing the Run Log table
- **THEN** the Profile, Reasoning, Suite, Δ prev, Git SHA, and Compare column headers have tooltip triggers
