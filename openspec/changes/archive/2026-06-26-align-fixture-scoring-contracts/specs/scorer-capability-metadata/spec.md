## ADDED Requirements

### Requirement: Effective scorer capabilities are available to tooling
GitBench SHALL expose scoring capability metadata that describes the effective behavior of a fixture scorer for validation and tooling.

#### Scenario: Generic scoring type resolves capabilities
- **WHEN** tooling asks for capabilities for `unordered_line_set` without a benchmark name
- **THEN** the metadata identifies the scorer as order-insensitive for non-empty answer lines

#### Scenario: Benchmark-specific scorer resolves capabilities
- **WHEN** tooling asks for capabilities for benchmark `branch_cleanup` with scoring type `exact_match`
- **THEN** the metadata identifies the effective scorer as set-based branch selection rather than generic literal exact match

#### Scenario: Unknown scorer fails conservatively
- **WHEN** tooling asks for capabilities for an unknown scoring type
- **THEN** the metadata returns conservative defaults or a clear unknown capability result that does not suppress validation warnings

### Requirement: Capability lookup uses benchmark context with fallback
GitBench SHALL resolve scorer capabilities by `(benchmark_name, scoring.type)` when benchmark context is available, and by `scoring.type` otherwise.

#### Scenario: Benchmark-specific capability wins
- **WHEN** benchmark `branch_cleanup` uses YAML scoring type `exact_match`
- **THEN** lookup returns the branch-selection capabilities for that benchmark instead of generic exact-match capabilities

#### Scenario: Generic fallback is used
- **WHEN** benchmark context is omitted for scoring type `exact_match`
- **THEN** lookup returns generic exact-match capabilities

### Requirement: Fixture self-check consumes scorer capabilities
Fixture self-checks SHALL use effective scorer capabilities to decide whether a warning applies.

#### Scenario: Dynamic reflog target does not trigger static hash warning
- **WHEN** a `reflog` fixture asks for a hash and stores a stable commit subject as the expected lookup key
- **THEN** self-check does not report the stable subject as a static non-hash expected defect

#### Scenario: Branch cleanup exact-match YAML does not trigger order warning
- **WHEN** a `branch_cleanup` fixture stores multiple expected branches and uses benchmark-local set scoring
- **THEN** self-check does not report a multiline exact-match ordering warning

#### Scenario: Generic exact-match multiline still warns
- **WHEN** a fixture uses generic `exact_match` with multiple non-empty expected lines and does not declare order sensitivity
- **THEN** self-check reports an ordering review issue
