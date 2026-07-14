## Context

GitBench stores provider token usage as reported: `input_tokens`, `output_tokens`, `total_tokens`, and optional `reasoning_tokens`. The OpenAI-compatible adapter maps `completion_tokens` to `output_tokens` and `completion_tokens_details.reasoning_tokens` to `reasoning_tokens` without normalization.

The report UI currently treats reasoning tokens as a subset of provider output. That is usually the intended interpretation, but current stored data includes providers and model routes where `reasoning_tokens > output_tokens`. In those cases, the tooltip says an impossible thing and the stacked token chart can render `input + reasoning` higher than the provider-reported `total_tokens`.

The fix needs to preserve raw telemetry while making the derived chart presentation internally consistent.

## Goals / Non-Goals

**Goals:**

- Preserve raw provider token fields unchanged in persisted result files and SQLite tables.
- Keep provider `total_tokens` as the authoritative bar value and range-whisker value.
- Decompose output into visible output, bounded reasoning within output, and inconsistent overflow reasoning for presentation.
- Prevent token chart stacks from exceeding provider totals because of inconsistent reasoning telemetry.
- Make tooltips explicit when a provider reports reasoning tokens that cannot fit within output tokens.
- Cover global, benchmark-scoped, and fixture-scoped token chart data paths.

**Non-Goals:**

- Rewrite historical result data or database rows.
- Infer which provider field is "correct" when raw usage fields conflict.
- Change model adapter usage extraction or provider request behavior.
- Hide inconsistent provider telemetry from users.

## Decisions

### 1. Preserve raw usage and add derived decomposition fields

`output_tokens` and `reasoning_tokens` remain raw provider values. The shared TypeScript helper will continue returning raw totals, but will also derive:

- `visible_output_tokens = max(output_tokens - reasoning_tokens, 0)` when output is known;
- `reasoning_within_output_tokens = min(reasoning_tokens, output_tokens)` when both are known;
- `reasoning_overflow_tokens = max(reasoning_tokens - output_tokens, 0)` when both are known; and
- an inconsistency flag when overflow is positive.

Alternative considered: clamp raw `reasoning_tokens` globally. Rejected because it would hide provider telemetry that may be useful for data-quality analysis.

### 2. Stack only the portion that can fit inside provider output

Token chart stack segments will use input, visible output, and bounded reasoning-within-output. Overflow reasoning will not be rendered as an additional stacked segment because doing so would make the bar exceed `total_tokens` for rows where `total_tokens = input_tokens + output_tokens`.

Alternative considered: add a fourth overflow segment above the bar. Rejected because the chart axis and sorting represent provider total tokens; adding overflow visually changes the metric.

### 3. Keep the tooltip accountable to raw values

Tooltips will define a color-coded `Total · (in / out / reasoning)` grouping once, then show each effort's total and compact grouped values on one line. Effort rows will retain the same type size as other chart tooltips; compact number formatting and a 300-pixel content cap will control width instead of smaller text or multi-line prose. Missing reasoning will use an unavailable marker.

When overflow exists, the reasoning position will show `bounded+overflow*`, and one shared footnote will identify the marker as provider-reported reasoning overflow. Bounded reasoning plus overflow preserves the raw reported reasoning count without repeating a diagnostic sentence for every effort.

Alternative considered: omit reasoning details for inconsistent providers. Rejected because it makes the suspicious data harder to diagnose.

Alternative considered: spell out every token field and overflow diagnostic on separate lines. Rejected because dense two-mode tooltips become excessively wide or tall and require smaller text than other chart tooltips.

### 4. Leave ingest validation out of scope

The adapter and import paths should continue to record usage as received. A future data-quality change could add warnings or provenance, but this proposal is limited to presentation correctness.

## Risks / Trade-offs

- **[Risk] Users may see both bounded reasoning and raw overflow and need more context.** -> Keep labels compact but explicit: provider output, reasoning within output, and inconsistent overflow.
- **[Risk] Some providers may intend reasoning to be separate from output despite using OpenAI-compatible field names.** -> Preserve raw values and avoid rewriting totals; only chart decomposition is bounded.
- **[Risk] Existing tests assume raw reasoning is the stacked segment.** -> Update focused chart tests to assert stack height equals provider total even when reasoning exceeds output.
- **[Risk] Fixture-scoped charts aggregate repeated attempts differently from global fixture results.** -> Add coverage for scoped chart aggregation, not only the shared helper.

## Migration Plan

1. Extend the token decomposition helper and tests for bounded reasoning and overflow.
2. Update chart metric rows to carry bounded reasoning and overflow metadata.
3. Update token chart stacks to use bounded reasoning.
4. Update token chart tooltip copy for normal, zero, unavailable, and inconsistent reasoning telemetry.
5. Run focused web tests and `pnpm build`.

Rollback can restore the previous chart decomposition and tooltip wording without data migration.

## Open Questions

None.
