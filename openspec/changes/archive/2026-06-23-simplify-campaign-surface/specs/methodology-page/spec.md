## MODIFIED Requirements

### Requirement: Methodology explains benchmark reliability metrics

The methodology page SHALL explain that model generation can be non-deterministic, describe evaluation runs and complete trial rounds, define mean one-attempt success and `pass_any_at_n`, explain stable-pass/flaky/stable-fail classifications, and state all denominator and exclusion rules. The page MAY define "campaign" as the internal stored identity for repeated evaluation runs, but it SHALL prefer reader-facing terms such as "evaluation run" and "trial round" for the primary explanation.

#### Scenario: Reader interprets mean success

- **WHEN** a reader views a model with 80% mean success over five trials
- **THEN** the methodology SHALL explain that this is the proportion of valid attempts that passed
- **AND** it SHALL not describe it as the probability of passing at least once in five attempts

#### Scenario: Reader interprets excluded failures

- **WHEN** an attempt is absent because of provider, fixture-identity, or judge failure
- **THEN** the methodology SHALL explain that the evaluation run is incomplete
- **AND** the failure is not silently counted as model-quality failure

#### Scenario: Reader views a legacy campaign

- **WHEN** a report contains a one-trial legacy campaign
- **THEN** the methodology SHALL explain that fixture stability cannot be inferred from it
- **AND** it SHALL make clear that "campaign" is the stored evaluation identity, not an end-user selection workflow

### Requirement: Methodology distinguishes resource normalizations

The methodology page SHALL distinguish mean per-trial cost, tokens, and API time from total evaluation-run consumption and from wall-clock duration. When campaign terminology appears in this section, it SHALL be used only to identify the stored internal evaluation unit behind those totals.

#### Scenario: Reader compares evaluation run costs

- **WHEN** two evaluation runs have different trial counts
- **THEN** the methodology SHALL explain why ranking charts use mean cost per complete trial
- **AND** why total run cost remains operationally relevant
