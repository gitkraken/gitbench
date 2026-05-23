## ADDED Requirements

### Requirement: Every page section has an explanatory blurb
Each chart section, table section, and major content area on every Astro page SHALL include a 1-3 sentence prose blurb between the section label and the content. The blurb SHALL explain what the section shows, how to read it, and any important caveats. Blurbs SHALL use `text-sm text-[var(--color-text-mid)] leading-relaxed` styling consistent with the existing About paragraph on the Overview page.

#### Scenario: Overview page has blurbs above each chart
- **WHEN** navigating to `/`
- **THEN** each of the five chart sections (Model Summary, Cost, Runtime, Token Usage, Benchmark Matrix) has a short explanatory paragraph between the section label and the chart

#### Scenario: Model detail page has blurb above fixture gallery
- **WHEN** navigating to a model level page (e.g., `/models/openai/gpt-4o/high`)
- **THEN** a blurb explains what the fixture gallery shows and how to use the filters

#### Scenario: History page has blurbs above chart and table
- **WHEN** navigating to `/history`
- **THEN** both the Time Series chart section and the Run Log table section have explanatory blurbs

### Requirement: Expanded overview introduction
The Overview page (`/`) About section SHALL be expanded from its current 1-paragraph form to 3-4 paragraphs explaining: why GitBench exists (the problem it solves), what it tests (204 fixtures across 17 Git skill categories), and who it serves (model evaluators, developers picking AI tools, researchers). The expanded text SHALL be written to be accessible to readers at all technical levels.

#### Scenario: Overview has multi-paragraph intro
- **WHEN** navigating to `/`
- **THEN** the About card contains 3 or more paragraphs of explanatory prose

#### Scenario: Intro explains the purpose
- **WHEN** a non-technical visitor reads the Overview intro
- **THEN** they understand what GitBench is, what it measures, and why it exists

### Requirement: Section blurbs include "Learn more" links to methodology
Section blurbs that explain metrics or concepts covered in the Methodology page SHALL include a "Learn more →" link at the end pointing to the relevant methodology section. Links SHALL use `text-[var(--color-accent)]` styling to visually distinguish them from the blurb text.

#### Scenario: Pass rate blurb links to methodology
- **WHEN** the Model Summary section blurb mentions pass rates
- **THEN** a "Learn more →" link points to `/methodology#pass-at-k` (or equivalent)

#### Scenario: Similarity score blurb links to methodology
- **WHEN** a fixture detail or benchmark detail blurb mentions similarity scoring
- **THEN** a "Learn more →" link points to the similarity scoring section of methodology

### Requirement: Empty state messages are reviewed for clarity
All existing empty state messages in chart components (CostValueChart "No pricing data available", TokenUsageChart "No token data available", RuntimeBarChart "No runtime data available") SHALL be reviewed and updated for clarity, completeness, and consistency with the new explanatory text tone.

#### Scenario: Empty states use consistent voice
- **WHEN** any chart displays an empty state message
- **THEN** the message uses language consistent with the new section blurbs and tooltips
