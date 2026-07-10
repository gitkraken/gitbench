## ADDED Requirements

### Requirement: Chart endpoints support benchmark and fixture scopes
The dynamic chart API SHALL support scoped payloads for `cost`, `runtime`, `tokens`, and `quadrant` chart names. A `benchmark` query parameter SHALL scope supported chart payloads to one benchmark. A `fixture` query parameter SHALL scope supported chart payloads to one fixture and MUST be accompanied by `benchmark`. Scoped chart responses SHALL remain compact and SHALL NOT include raw prompt text, expected text, raw model output text, or bulky structured-output payloads.

#### Scenario: Benchmark scoped cost chart response
- **WHEN** a client requests `/api/charts/cost?benchmark=commit_messages`
- **THEN** the response contains cost summaries computed only from `commit_messages` results or attempts
- **AND** it does not include raw fixture output text

#### Scenario: Fixture scoped token chart response
- **WHEN** a client requests `/api/charts/tokens?benchmark=commit_messages&fixture=f001`
- **THEN** the response contains token summaries computed only from `commit_messages/f001` results or attempts
- **AND** it does not include raw prompt, expected, or model output text

#### Scenario: Fixture scope requires benchmark
- **WHEN** a client requests `/api/charts/runtime?fixture=f001` without a `benchmark` query parameter
- **THEN** the API returns a clear 400 response

#### Scenario: Unsupported fixture scope is rejected
- **WHEN** a client requests a fixture scope for a chart that cannot render fixture-level data
- **THEN** the API returns a clear client error instead of returning global chart data

### Requirement: Scoped chart APIs remain campaign-sensitive
Scoped chart endpoints SHALL resolve campaign-sensitive data the same way existing chart endpoints do. When a compatible explicit campaign is supplied, scoped chart data SHALL come from that campaign. When no explicit campaign is supplied and a default publishable campaign exists, scoped chart data SHALL come from the default campaign. When no campaign data exists, scoped chart data SHALL fall back to legacy aggregate fixture result rows where possible.

#### Scenario: Benchmark scoped chart uses selected campaign
- **WHEN** a client requests `/api/charts/runtime?benchmark=git_grep&campaign=<id>` with a compatible campaign ID
- **THEN** runtime values are computed from that campaign's `git_grep` attempts
- **AND** the response includes the selected campaign metadata

#### Scenario: Fixture scoped chart defaults to latest campaign
- **WHEN** a client requests `/api/charts/quadrant?benchmark=git_grep&fixture=f002` without a `campaign` query parameter and a default publishable campaign exists
- **THEN** the quadrant data is computed from the default campaign's `git_grep/f002` attempts
- **AND** the response includes the resolved campaign metadata

#### Scenario: Legacy aggregate fallback remains available
- **WHEN** no campaign records exist but legacy fixture result rows exist for `tag_management/f004`
- **THEN** `/api/charts/tokens?benchmark=tag_management&fixture=f004` returns token chart data derived from those legacy fixture result rows

### Requirement: Fixture scoped quadrant exposes adaptive quality data
The fixture-scoped quadrant chart payload SHALL expose enough compact metric data for clients to plot quality against cost, API time, or token usage. The payload SHALL identify whether fixture quality is campaign success rate, graded similarity, or binary success so clients can label axes and tooltips correctly.

#### Scenario: Payload identifies success quality
- **WHEN** a fixture-scoped quadrant response is based on repeated-attempt pass rates
- **THEN** the response identifies the quality metric as success rate
- **AND** includes valid and passing attempt counts where available

#### Scenario: Payload identifies similarity quality
- **WHEN** a fixture-scoped quadrant response is based on intermediate similarity values
- **THEN** the response identifies the quality metric as similarity

#### Scenario: Payload identifies binary quality
- **WHEN** a fixture-scoped quadrant response is based only on pass/fail results
- **THEN** the response identifies the quality metric as binary success
