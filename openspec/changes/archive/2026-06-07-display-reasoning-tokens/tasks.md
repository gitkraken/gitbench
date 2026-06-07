# Tasks: Display Reasoning Tokens

## Phase 1: Data Pipeline (bottom-up)

### 1.1 Add reasoning_tokens column to DB schema
- [x] Add `reasoning_tokens INTEGER` to `fixture_results` table in `gitbench/web/data/schema.sql`
- [x] Add after `total_tokens INTEGER` line

### 1.2 Extract reasoning_tokens in Python data pipeline
- [x] In `render.py` `_build_report_json()` (~line 394): add `"reasoning_tokens": score.get("reasoning_tokens")` to fixture dict
- [x] In `render.py` DB writer (~line 800): add `"reasoning_tokens": result.get("reasoning_tokens")` to `result_rows`
- [x] In `render.py` INSERT SQL: add `reasoning_tokens` column to the INSERT statement

### 1.3 Map reasoning_tokens in JS ingestion
- [x] In `build-db.mjs`, add `reasoning_tokens` to the `INSERT INTO fixture_results` column list
- [x] Add `reasoning_tokens: result.reasoning_tokens ?? null` to the VALUES mapping

### 1.4 Add reasoning_tokens to TypeScript types
- [x] Add `reasoning_tokens: number | null` to `FixtureResult` interface in `types.ts`
- [x] Add `reasoning_tokens: number` to `ModelTokenSummary` interface in `types.ts`

### 1.5 Add reasoning_tokens to report store query
- [x] Add `COALESCE(SUM(reasoning_tokens), 0) AS reasoning_tokens` to the token summaries SQL query in `node-sqlite-report-store.ts`
- [x] Map `reasoning_tokens: Number(r.reasoning_tokens)` in the result mapping

## Phase 2: Chart Components

### 2.1 Add reasoningTokens to MetricEffort
- [x] Add `reasoningTokens?: number` to `MetricEffort` interface in `model-groups.ts`
- [x] Populate `reasoningTokens` in `tokenMetric()` extractor from `data.model_token_summaries`

### 2.2 Update TokenUsageChart with stacked bar segments
- [x] Refactor `VerticalGroupedMetricChart` to support 3-segment stacked bars (input | output | reasoning)
- [x] Reasoning segment uses a lighter/translucent variant of the provider color
- [x] Reasoning segment only renders when `reasoningTokens > 0` AND `reasoningLevel` is set
- [x] Update tooltip to show `in / out / r` breakdown in `TokenUsageChart.tsx`
- [x] Ensure `renderEffort` in tooltip handles reasoning tokens display

### 2.3 Handle chart rendering for models without reasoning
- [x] When no effort in a group has reasoning tokens, bars render as 2-segment (input | output) with no reasoning segment
- [x] Group range whiskers continue to use `total_tokens` (which already includes reasoning)

## Phase 3: Page-Level Display

### 3.1 Model detail page reasoning tokens
- [x] In `[provider]/[model]/[level].astro`, compute total reasoning tokens alongside input/output
- [x] Display reasoning tokens in the stats line when `reasoning_level` is set
- [x] Omit reasoning token display when `reasoning_level` is null/empty

### 3.2 Fixture detail page
- [x] In `fixtures/[benchmark]/[fixture].astro`, pass `reasoning_tokens` from `fr` to `ModelOutputCard`
- [x] Add `reasoningTokens` to the prop types

### 3.3 ModelOutputCard reasoning display
- [x] Add `reasoningTokens?: number | null` prop
- [x] When `reasoningTokens != null`, update inline badge from `{input}→{output}` to `{input}→{output}(+{reasoning}r)`
- [x] When `reasoningTokens` is null/undefined, keep current `{input}→{output}` format

### 3.4 FixtureCard reasoning display
- [x] Add `reasoningTokens?: number | null` prop to `FixtureCard.astro`
- [x] Add third column to the token grid when reasoning data is present
- [x] Column shows count with "Reason" label
- [x] Without reasoning data, keep existing 2-column grid

## Phase 4: OpenRouter Transcript Fix

### 4.1 Check OpenRouter reasoning field in adapter
- [x] In `OpenAIAdapter.generate()` (~line 270), add fallback: `getattr(message, "reasoning", None)` after `getattr(message, "reasoning_content", None)`
- [x] The `reasoning_content` takes priority; `reasoning` is the fallback
- [x] No test changes needed (existing tests use mock responses without either field)

## Phase 5: Verification

### 5.1 Run with reasoning model to validate end-to-end
- [ ] Run benchmark with an OpenAI reasoning model (e.g., `openai/o3-mini#high`) through OpenRouter
- [ ] Verify `reasoning_tokens > 0` in the result JSON
- [ ] Verify DB ingestion captures reasoning tokens
- [ ] Verify token chart shows reasoning segment
- [ ] Verify model detail page and fixture cards show reasoning tokens
- [ ] Verify OpenRouter transcript includes `reasoning_content` in transcript

### 5.2 Run with non-reasoning model to verify N/A handling
- [ ] Verify non-reasoning models don't show reasoning segment in chart
- [ ] Verify fixture cards don't show reasoning column for non-reasoning models
- [ ] Verify model detail page doesn't show reasoning tokens when level is absent
