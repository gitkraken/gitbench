# llm-judge-scoring Specification

## Purpose
TBD - created by archiving change add-llm-judge. Update Purpose after archive.
## Requirements
### Requirement: Judge configuration in gitbench.json
The system SHALL require a top-level `judge` section in `gitbench.json` for benchmarks whose fixtures declare `scoring.type: llm_judge`. Running a judge-required benchmark without judge configuration SHALL exit with an error (unless all models are mock).

The `judge` section MUST have:
- `profile`: Name of a model profile defined in `models` to use as the judge model group. Every model in the profile is called for ensemble averaging.

#### Scenario: Judge section present
- **WHEN** `gitbench.json` contains `"judge": {"profile": "openrouter-llms-as-judges"}`
- **THEN** the system SHALL use the judge for all benchmarks containing `llm_judge` fixtures

#### Scenario: Judge section absent for judge-required benchmark
- **WHEN** `gitbench.json` has no `judge` key and a benchmark with `llm_judge` fixtures (e.g. `commit_messages`) is run
- **THEN** the system SHALL exit with an error indicating that a judge profile is required

#### Scenario: Judge section absent for non-judge benchmark
- **WHEN** `gitbench.json` has no `judge` key and a benchmark that has no `llm_judge` fixtures is run (e.g. `git_bisect`)
- **THEN** the system SHALL run normally without a judge

#### Scenario: Judge profile not found
- **WHEN** the `judge.profile` references a profile not defined in `models`
- **THEN** the system SHALL exit with an error indicating the profile is not found

### Requirement: JudgeClient evaluates commit messages via ensemble averaging
The system SHALL provide a `JudgeClient` class that wraps multiple model clients and returns the **average** of their scores.

`JudgeClient` MUST:
- Accept a list of ``ModelInterface`` instances at initialization
- Call **every** model for each evaluation
- Average the successful scores; exclude failed models from the average
- Provide an `evaluate_commit_message(diff, message)` method that returns a `float` between 0.0 and 1.0
- Construct a prompt that includes the diff and message, asking the model to rate quality
- Parse each model response to extract a numeric rating

#### Scenario: Perfect commit message
- **WHEN** the diff shows adding a file `hello.txt` and the message is "Add hello.txt with greeting message"
- **THEN** the judge SHALL return a score ≥ 0.7

#### Scenario: Wrong commit message
- **WHEN** the diff shows adding a file `hello.txt` and the message is "Fix login bug"
- **THEN** the judge SHALL return a score < 0.5

#### Scenario: Vague commit message
- **WHEN** the diff shows adding three new files `config.py`, `main.py`, `utils.py` and the message is "Update files"
- **THEN** the judge SHALL return a score between 0.3 and 0.6

#### Scenario: Non-numeric judge response
- **WHEN** the judge model returns a response that cannot be parsed as a number
- **THEN** `evaluate_commit_message` SHALL raise a `ValueError`

### Requirement: Judge gating is declared per fixture
The system SHALL invoke the LLM judge if and only if a fixture declares `scoring.type: llm_judge`. No benchmark-level allowlist or diff-presence heuristic SHALL participate in judge routing.

The `Scorer` class SHALL accept an optional `JudgeClient` and dispatch to it for `llm_judge` fixtures.

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

### Requirement: Judge failure handling
The system SHALL call **every** model in the judge profile and average their scores.

Each model adapter is configured with 5 retries:
- The adapter SHALL retry with exponential backoff on transient failures
- On rate limits (HTTP 429), the adapter SHALL respect the ``Retry-After`` header
- Failed models are excluded from the average; only successful scores count
- If all models in the profile fail, the system SHALL fall back to ``SequenceMatcher``
- The resulting ``Score`` SHALL have a non-null ``error`` field containing "judge_failed"
- This fallback behavior lives in the `llm_judge` scoring branch, not the `similarity` branch.

#### Scenario: Judge averages multiple model scores
- **WHEN** the judge profile has 3 models returning 0.8, 0.6, and 0.7
- **THEN** the judge SHALL return 0.7 (the average)

#### Scenario: Judge excludes failed model from average
- **WHEN** one model fails and two return 0.8 and 0.4
- **THEN** the judge SHALL return 0.6 (average of the two successful scores)

#### Scenario: All judge models fail
- **WHEN** every model in the judge profile exhausts its retries while scoring an llm_judge fixture
- **THEN** the score falls back to SequenceMatcher against `fixture.expected` and `Score.error` contains "judge_failed"

#### Scenario: Partial judge failure
- **WHEN** one judge model fails and others return scores
- **THEN** the average of successful scores is used and no error is set

### Requirement: Runner wires judge into benchmark execution
The `BenchmarkRunner` SHALL construct a single judge-aware `Scorer` when a judge is configured and use it for all benchmarks; scoring-type dispatch alone decides whether the judge is called.

#### Scenario: Runner with judge configuration
- **WHEN** the runner is initialized with a valid `judge` section
- **THEN** one `Scorer` carrying the `JudgeClient` is used for every benchmark, with no per-benchmark scorer substitution

#### Scenario: Runner without judge configuration
- **WHEN** the runner is initialized without a `judge` section
- **THEN** the `Scorer` has no judge client, and only llm_judge fixtures would error (prevented by preflight)
