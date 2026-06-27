## ADDED Requirements

### Requirement: Single-file conflict calibration uses replay evidence
Single-file conflict calibration SHALL separate scorer brittleness from genuine task difficulty using local replay and manual review.

#### Scenario: Replay precedes calibration decision
- **WHEN** a single-file conflict fixture is considered for scorer migration
- **THEN** local replay of stored attempts is performed before changing the fixture

#### Scenario: Campaign rerun is not required
- **WHEN** migration decisions are made under this proposal
- **THEN** a full campaign rerun is not required as part of implementation
