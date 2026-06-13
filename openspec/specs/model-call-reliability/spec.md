# model-call-reliability Specification

## Purpose
TBD - created by archiving change add-capacity-group-cooldowns. Update Purpose after archive.
## Requirements
### Requirement: Model attempts use a 240-second default timeout
GitBench SHALL use a 240-second timeout for every model-generation API attempt when neither the CLI nor the selected profile configures a timeout. This policy SHALL apply to benchmark generation, reasoning preflight calls, and LLM judge calls.

#### Scenario: Unconfigured OpenAI-compatible model uses default
- **WHEN** an OpenAI-compatible profile and CLI invocation specify no timeout
- **THEN** every model attempt uses a 240-second timeout

#### Scenario: Unconfigured Ollama model uses default
- **WHEN** an Ollama profile and CLI invocation specify no timeout
- **THEN** every model attempt uses a 240-second timeout

#### Scenario: Profile timeout overrides default
- **WHEN** a profile specifies `timeout: 180` and the CLI specifies no timeout
- **THEN** every applicable model attempt uses a 180-second timeout

#### Scenario: CLI timeout overrides profile
- **WHEN** a profile specifies `timeout: 180` and the CLI specifies `--timeout 300`
- **THEN** every applicable model attempt uses a 300-second timeout

#### Scenario: Judge clients use default timeout policy
- **WHEN** a judge profile has no timeout configured
- **THEN** each judge model attempt uses a 240-second timeout

### Requirement: Retryable attempts coordinate by failure scope
GitBench SHALL apply local exponential backoff to retryable errors that affect only one request and shared capacity-group cooldowns to HTTP 429 rate-limit responses.

#### Scenario: Timeout uses local retry backoff
- **WHEN** one model attempt times out and another target shares its capacity group
- **THEN** the timed-out call follows its configured local retry policy without establishing a group cooldown

#### Scenario: Rate limit uses shared cooldown
- **WHEN** one model attempt receives HTTP 429
- **THEN** its retry and other attempts in the same capacity group wait for the shared group cooldown

#### Scenario: Cooldown includes jitter
- **WHEN** GitBench calculates a fallback or `Retry-After` cooldown
- **THEN** it adds bounded positive jitter while still waiting at least the provider-requested or configured base duration

### Requirement: Model retry behavior is observable
GitBench SHALL emit structured logs for each retryable failure and SHALL persist request telemetry with fixture scores for the model-under-test generation call. Telemetry SHALL distinguish provider attempt count, local retry wait, shared cooldown wait, and retry reason categories.

#### Scenario: Successful first attempt records telemetry
- **WHEN** a fixture generation succeeds on its first provider attempt
- **THEN** its persisted score records one provider attempt and zero retry and cooldown wait

#### Scenario: Successful retry records prior failures
- **WHEN** a fixture succeeds after one or more retryable failures
- **THEN** its persisted score records the total provider attempts, cumulative local retry wait, cumulative shared cooldown wait, and encountered retry reason categories

#### Scenario: Exhausted retries preserve telemetry
- **WHEN** all configured attempts fail
- **THEN** the failed fixture score preserves the accumulated request telemetry alongside the final error

#### Scenario: Judge retries are logged
- **WHEN** an LLM judge call retries or waits on a group cooldown
- **THEN** structured logs identify the judge model, capacity group, attempt number, retry category, and wait duration

### Requirement: Doctor behavior remains unchanged
This change SHALL NOT modify doctor target selection, doctor pacing, doctor timeout defaults, or doctor result-repair semantics.

#### Scenario: Doctor invocation retains existing policy
- **WHEN** a user invokes `gitbench doctor`
- **THEN** the command follows its existing timeout, retry, and execution behavior

