## ADDED Requirements

### Requirement: Suite-level self-check requires benchmark context
Fixture self-check execution for suite-level validation SHALL provide benchmark context so effective scorer behavior can be resolved accurately.

#### Scenario: Suite validation passes benchmark name
- **WHEN** validation iterates fixtures for a benchmark
- **THEN** it calls self-check with the benchmark name for each fixture

#### Scenario: Missing benchmark context is rejected or deprecated
- **WHEN** a suite-level caller invokes self-check without benchmark context
- **THEN** the system rejects the call or emits a deprecation warning according to the migration phase

#### Scenario: Generic fixture-only check remains explicit
- **WHEN** a caller intentionally performs a generic fixture-only check
- **THEN** the call path clearly identifies that benchmark-local scorer behavior is not represented
