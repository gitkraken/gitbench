## Context

GitBench validates model effort suffixes before benchmark execution by combining a shipped effort matrix with OpenRouter capability metadata. The matrix currently lists effort values that some models do not document, and a listed `none` value is treated as sufficient evidence that reasoning will be disabled.

OpenRouter normalizes a `reasoning` request object, but provider endpoints may support different controls or ignore unsupported values. The observed DeepSeek V4 Flash run sent `reasoning.effort=none`, yet some responses contained non-zero reasoning tokens and reasoning text. Provider `completion_tokens` also includes reasoning tokens, while the report UI currently presents and stacks reasoning as if it were additional output.

The change crosses CLI validation, adapter request/response handling, concurrent run failure propagation, report calculations, and fixture versioning. Existing persisted token fields must remain compatible.

## Goals / Non-Goals

**Goals:**

- Preserve the existing static supported-level validation for all configured efforts.
- Make `none` a strict, testable no-reasoning invariant rather than a best-effort hint.
- Abort before benchmark fixtures when a configured `none` target is disproven or cannot be verified.
- Abort a running target if a later response violates `none`.
- Preserve raw provider usage while presenting output and reasoning without double-counting.
- Make `blame_forensics/f010` identify one objectively correct commit.

**Non-Goals:**

- Dynamically discover every provider's supported effort enum from undocumented APIs.
- Guarantee that a single canary proves future provider behavior; runtime enforcement remains necessary.
- Rewrite historical result files or change the persisted meaning of `output_tokens`.
- Make benchmark output persistence transactional across unrelated models that completed before a runtime violation.

## Decisions

### 1. Keep static level validation and correct the shipped matrix

The existing capability resolver remains the first validation layer. The shipped matrix SHALL list only effort levels supported by current provider documentation. DeepSeek V4 Flash and V4 Pro will be restricted to `high` and `xhigh` unless verified provider behavior supports additional values.

This avoids spending an API call on combinations already known to be unsupported. A purely live-discovery approach was rejected because the OpenRouter models and endpoints APIs expose support for the `reasoning` parameter, not necessarily every accepted effort value.

### 2. Forward OpenRouter `none` as an explicit disable operation

For OpenRouter targets, `none` will use `reasoning: {"enabled": false}` rather than `reasoning: {"effort": "none"}`. Non-`none` levels continue to use `reasoning.effort`. The adapter will merge this with existing `extra_body` values without mutating caller-owned data.

The disable shape matches the control documented for hybrid DeepSeek models and expresses intent without relying on an effort enum that the endpoint may not support. First-party OpenAI behavior remains `reasoning_effort="none"`.

### 3. Add a behavioral preflight for unique `none` targets

After credentials and static capability validation succeed, but before benchmark fixtures execute, the CLI will preflight each unique `none` target once. Uniqueness is based on the effective provider, base URL, model, and routing configuration so duplicated profile entries do not create redundant calls.

The preflight uses the normal adapter request path with a fixed, small reasoning canary and a bounded output budget. It is not scored, timed as benchmark data, or persisted in result files.

A preflight passes only when:

- usage explicitly reports `reasoning_tokens == 0`; and
- the assistant response contains no non-empty reasoning field.

Non-zero reasoning, reasoning content, missing reasoning-token telemetry, request rejection, or an exhausted retry budget makes the target unsupported or unverifiable and aborts the complete invocation before fixture execution. A single probe can disprove `none` but cannot prove permanent behavior, so it is paired with runtime enforcement.

### 4. Enforce the same invariant on every real response

The adapter will centralize `none` response validation in one helper used by both preflight and benchmark generation. Violations raise a dedicated fatal exception carrying the model and observed evidence.

The runner and concurrent CLI orchestration will allow this exception to escape ordinary fixture error conversion, cancel pending work on a best-effort basis, stop scheduling new work, and exit non-zero. The violating response is not recorded as a normal failed score or successful model result. Results from unrelated targets already completed before the violation are not rolled back.

### 5. Preserve raw usage and derive visible output

`output_tokens` remains the provider-reported completion total, including reasoning when the provider reports that relationship. A shared presentation helper derives:

`visible_output_tokens = max(output_tokens - reasoning_tokens, 0)`

When `reasoning_tokens` is absent, visible output equals provider output. When output is absent, visible output remains unavailable. If provider values are inconsistent and reasoning exceeds output, raw values remain unchanged and visible output is clamped to zero rather than becoming negative.

No database migration is required.

### 6. Make report labels and chart stacks express inclusion

Fixture and model report labels will describe output as total output and identify reasoning as included within it. Compact badges will use wording such as `182 in → 1,349 out (1,343 reasoning)` instead of the additive `(+1343r)` notation.

Token chart stacks will use:

`input + visible output + reasoning = total tokens`

For each mode, stack segments will come from the same representative effort used for the median bar rather than summing every effort in the group. Range whiskers continue to describe the minimum and maximum raw total-token values across efforts.

### 7. Correct the ambiguous fixture and bump suite version

`blame_forensics/f010` will retain only one commit that changes a valid import to the nonexistent `helpers` module. Later commits may add or modify a separate valid formatter import but must preserve blame for the broken line on `Update import path`.

Because this changes which outputs pass, `BENCHMARK_SUITE_VERSION` will move from `0.2.0` to `0.3.0`.

## Risks / Trade-offs

- **[Risk] Preflight adds latency and cost for every unique `none` target.** → Use one bounded canary per effective routing identity and do not repeat it per output mode or fixture.
- **[Risk] A canary returns zero reasoning but a later request reasons.** → Enforce the invariant on every benchmark response and abort on the first violation.
- **[Risk] Providers omit zero-valued reasoning telemetry even when reasoning is disabled.** → Treat the target as unverifiable and fail closed; a strict no-reasoning benchmark cannot rely on absent evidence.
- **[Risk] Concurrent requests are already in flight when a violation occurs.** → Stop new scheduling and cancel pending futures best-effort; document that already completed unrelated results are not rolled back.
- **[Risk] Provider usage fields can be inconsistent.** → Preserve raw values, clamp only the derived visible-output value, and test reasoning-greater-than-output cases.
- **[Risk] Provider support changes after the matrix ships.** → Keep the matrix correction scoped and actionable; unsupported entries fail before costly benchmark execution.

## Migration Plan

1. Update the effort matrix and static validation tests.
2. Add provider-specific disable forwarding, response invariant checks, and preflight orchestration.
3. Update token presentation helpers and report/chart consumers without changing stored fields.
4. Correct `blame_forensics/f010` and bump the suite version to `0.3.0`.
5. Run focused Python and web tests, then validate the complete benchmark fixture set.

Rollback can restore the previous forwarding and presentation behavior without data migration. Results produced under suite version `0.3.0` remain distinguishable from earlier fixture semantics.

## Open Questions

None.
