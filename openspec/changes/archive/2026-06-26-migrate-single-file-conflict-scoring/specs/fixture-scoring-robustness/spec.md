## ADDED Requirements

### Requirement: Single-file conflict scorer migrations are evidence-gated
Single-file conflict fixtures SHALL migrate to file-aware resolved-content scoring only after local replay evidence shows the migration preserves semantic correctness.

#### Scenario: Expected answer passes before migration
- **WHEN** a candidate single-file conflict fixture is evaluated with its expected answer
- **THEN** the expected answer passes both before and after the candidate scoring change

#### Scenario: Newly passing stored outputs are inspected
- **WHEN** stored-attempt replay shows outputs that newly pass after scorer migration
- **THEN** those outputs are manually inspected for semantic correctness before the migration is accepted

#### Scenario: Newly failing stored outputs are reviewed
- **WHEN** stored-attempt replay shows outputs that newly fail after scorer migration
- **THEN** those outputs are reviewed to determine whether the stricter failure is intentional or caused by parser/prompt mismatch

### Requirement: Single-file conflict migration decisions are documented
Each candidate single-file conflict fixture SHALL have a recorded migration decision.

#### Scenario: Fixture is migrated
- **WHEN** evidence supports migrating a fixture to file-aware scoring
- **THEN** the implementation records the fixture, reason, and replay outcome summary

#### Scenario: Fixture remains unchanged
- **WHEN** evidence does not support migration
- **THEN** the implementation records why the fixture remains on its existing scorer
