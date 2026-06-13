## MODIFIED Requirements

### Requirement: Judge gating is declared per fixture
The system SHALL invoke the LLM judge if and only if a fixture declares `scoring.type: llm_judge`. No benchmark-level allowlist or diff-presence heuristic SHALL participate in judge routing.

#### Scenario: llm_judge fixture routed to judge
- **WHEN** a fixture with `scoring.type: llm_judge` is scored and a judge is configured
- **THEN** the score comes from `JudgeClient` ensemble averaging, with `passed = similarity >= threshold`

#### Scenario: similarity fixture never routed to judge
- **WHEN** a fixture with `scoring.type: similarity` is scored, even with a judge configured and a diff available
- **THEN** the score comes from SequenceMatcher only

#### Scenario: llm_judge without judge client
- **WHEN** a fixture with `scoring.type: llm_judge` is scored and no judge client is configured
- **THEN** the result is a failed score with an error indicating a judge is required (normally prevented by CLI preflight)

### Requirement: Judge-required benchmarks are discovered from fixtures
The system SHALL determine which benchmarks require a judge by scanning their fixtures for `scoring.type: llm_judge`, replacing the hardcoded `JUDGE_REQUIRED_BENCHMARKS` constant.

#### Scenario: Preflight error without judge profile
- **WHEN** a requested benchmark contains llm_judge fixtures, no `judge` section exists in `gitbench.json`, and models are not all mock
- **THEN** the CLI exits with the existing "requires an LLM judge" error before any fixtures run

#### Scenario: Mock-models exemption preserved
- **WHEN** all requested models are mock variants
- **THEN** llm_judge benchmarks run without a judge profile, as today

#### Scenario: No stale allowlist
- **WHEN** a new benchmark's fixtures declare `scoring.type: llm_judge`
- **THEN** preflight validation and judge wiring apply to it without any code or config change

### Requirement: Runner wires judge into benchmark execution
The `BenchmarkRunner` SHALL construct a single judge-aware `Scorer` when a judge is configured and use it for all benchmarks; scoring-type dispatch alone decides whether the judge is called.

#### Scenario: Runner with judge configuration
- **WHEN** the runner is initialized with a valid `judge` section
- **THEN** one `Scorer` carrying the `JudgeClient` is used for every benchmark, with no per-benchmark scorer substitution

#### Scenario: Runner without judge configuration
- **WHEN** the runner is initialized without a `judge` section
- **THEN** the `Scorer` has no judge client, and only llm_judge fixtures would error (prevented by preflight)

### Requirement: Judge failure handling
The system SHALL call every model in the judge profile and average their scores; when all judge models fail, the system SHALL fall back to SequenceMatcher and set a `judge_failed` error on the score. This behavior is unchanged; it now lives in the `llm_judge` scoring branch instead of the `similarity` branch.

#### Scenario: All judge models fail
- **WHEN** every model in the judge profile exhausts its retries while scoring an llm_judge fixture
- **THEN** the score falls back to SequenceMatcher against `fixture.expected` and `Score.error` contains "judge_failed"

#### Scenario: Partial judge failure
- **WHEN** one judge model fails and others return scores
- **THEN** the average of successful scores is used and no error is set
