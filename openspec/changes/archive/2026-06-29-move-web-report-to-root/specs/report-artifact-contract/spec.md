## ADDED Requirements

### Requirement: Compatibility JSON is the canonical report artifact
The report artifact contract SHALL define `web/public/results.json` as the canonical compatibility artifact produced by GitBench report aggregation. The artifact SHALL be checked in and SHALL include the report data needed to derive web runtime artifacts, including models, benchmarks, fixtures, fixture index, model summaries, runtime summaries, benchmark matrix values, run metadata, base-model groups, campaign metadata, trials, fixture aggregates, raw attempts, cost data, timing data, token usage, output mode, and reasoning level.

#### Scenario: Report command publishes compatibility JSON
- **WHEN** `gitbench report` completes successfully
- **THEN** `web/public/results.json` contains valid standard JSON
- **AND** it includes the contract-required top-level report sections
- **AND** it does not require the web module to run benchmark aggregation

#### Scenario: JSON remains the source for derived artifacts
- **WHEN** the checked-in SQLite database is rebuilt
- **THEN** it is derived from `web/public/results.json`
- **AND** the rebuild does not require raw benchmark result directories

### Requirement: SQLite database is a derived web artifact
The report artifact contract SHALL define `web/data/gitbench.db` as a checked-in SQLite artifact derived from `web/public/results.json` using `web/data/schema.sql`. The web module SHALL own the derivation command, schema file, runtime database path, and freshness validation.

#### Scenario: Web command rebuilds SQLite
- **WHEN** the supported web database build command runs from `web/`
- **THEN** it reads `public/results.json`
- **AND** applies `data/schema.sql`
- **AND** atomically writes `data/gitbench.db`

#### Scenario: SQLite freshness is verifiable
- **WHEN** artifact validation runs
- **THEN** it can detect whether `web/data/gitbench.db` is current with `web/public/results.json` and `web/data/schema.sql`

### Requirement: Artifact contract is documented and executable
The repository SHALL include prose documentation for the report artifact contract and executable validation that can be run from both Python and web workflows. The contract SHALL describe ownership, required fields, JSON-to-SQLite mapping expectations, compatibility rules, and validation commands.

#### Scenario: Prose explains artifact ownership
- **WHEN** a maintainer reads the report artifact contract documentation
- **THEN** it states that Python publishes compatibility JSON
- **AND** the web module derives SQLite from that JSON

#### Scenario: Contract validation is runnable
- **WHEN** Python and web verification commands are run
- **THEN** they validate the compatibility JSON shape and SQLite derivation expectations

### Requirement: Artifact compatibility changes are explicit
Changes to required compatibility JSON fields, SQLite schema tables, column meanings, safety metadata, campaign representation, output-mode representation, timing representation, token usage, or cost fields SHALL update the report artifact contract and its validation tests in the same change.

#### Scenario: Schema-affecting change updates contract
- **WHEN** a change modifies `web/data/schema.sql` or the JSON fields used to build it
- **THEN** the report artifact contract documentation and validation tests are updated with the new expectations

#### Scenario: Incompatible changes are versioned or migrated
- **WHEN** a future report artifact change is not backward compatible with checked-in artifacts
- **THEN** the change defines a versioning or migration path before implementation is considered complete

### Requirement: Safety metadata is preserved across report artifacts
The report artifact contract SHALL require publication safety metadata to be preserved when present in compatibility JSON and represented in SQLite where report APIs need it. Artifact validation SHALL reject generated public artifacts that violate configured result-safety publication requirements.

#### Scenario: Safety-reviewed report remains publishable
- **WHEN** `gitbench report` aggregates inputs with valid result-safety metadata
- **THEN** the compatibility JSON preserves the metadata needed for publication validation
- **AND** the SQLite derivation keeps safety fields required by report API queries

#### Scenario: Unsafe artifact is rejected
- **WHEN** configured result-safety validation detects missing, stale, or modified safety metadata in report inputs
- **THEN** report artifact generation fails before checked-in public artifacts are updated
