## MODIFIED Requirements

### Requirement: CLI provides gitbench report command
The CLI SHALL provide a `gitbench report` command that aggregates legacy run results from `gitbench-results/`, ingests campaign artifacts from campaign directories containing `campaign.json`, validates configured result-safety publication requirements, and writes compatibility JSON to `web/public/results.json`. The command SHALL NOT run Astro build, dev-server, preview, or browser-opening workflows.

#### Scenario: report command publishes compatibility JSON
- **WHEN** `gitbench report` completes successfully
- **THEN** `web/public/results.json` contains the aggregated report JSON
- **AND** the command prints guidance for running web module commands when a user wants to build or view the report

#### Scenario: deprecated web flags do not run web workflows
- **WHEN** `gitbench report --open`, `gitbench report --dev`, or `gitbench report --no-build` is executed
- **THEN** the command prints a deprecation warning for the flag
- **AND** it does not run Astro build, dev-server, preview, or browser-opening behavior
- **AND** it still publishes compatibility JSON when valid report inputs are present

#### Scenario: report command ingests campaign artifacts
- **WHEN** `gitbench report` scans a result directory containing `campaign.json` and raw campaign attempt envelopes
- **THEN** the generated report JSON SHALL include campaign metadata, trials, exact raw-attempt references, fixture aggregates, and campaign summaries
- **AND** it SHALL NOT require a separate manual campaign export step

## REMOVED Requirements

### Requirement: CLI supports render --format json
**Reason**: The public JSON publication surface is `gitbench report`; there is no `gitbench render` command in the CLI.

**Migration**: Use `gitbench report --output <path>` when a custom compatibility JSON path is required.
