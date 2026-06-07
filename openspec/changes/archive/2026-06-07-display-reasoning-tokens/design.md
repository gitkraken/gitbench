# Design: Display Reasoning Tokens

## Data Flow (current gaps → fixed)

```
  API Response
  ┌─────────────────────────────────────────┐
  │ response.usage.completion_tokens_       │
  │   details.reasoning_tokens              │  ✅ already read by adapter
  │ response.choices[0].message.reasoning   │  ❌ not read (OpenRouter field)
  └──────────────────┬──────────────────────┘
                     │
  Score (types.py)   │ ✅ already has reasoning_tokens field
  Result JSON        │ ✅ already includes reasoning_tokens
                     │
  ═══════════════ GAP BOUNDARY ═══════════════
                     │
  render.py ─────────┤ ❌ not extracted from scores
  schema.sql ────────┤ ❌ no column
  build-db.mjs ──────┤ ❌ not mapped
  types.ts ──────────┤ ❌ no field
  report-store.ts ───┤ ❌ no SUM in query
                     │
  Display surfaces ──┤ ❌ nowhere shown
```

## Database Change

Add nullable `reasoning_tokens` column to `fixture_results`:

```sql
ALTER TABLE fixture_results ADD COLUMN reasoning_tokens INTEGER;
```

No new summary table needed — the existing `model_token_summaries` query gains an additional `COALESCE(SUM(reasoning_tokens), 0)` aggregation.

## Display Strategy: NULL vs 0 Semantics

The display layer uses `reasoning_level` (not the token count) to gate whether reasoning data is relevant:

| `reasoning_level` | `reasoning_tokens` | Display            |
|-------------------|--------------------|--------------------|
| `null` / `""`     | any                | **Hidden** (N/A)   |
| `"high"` etc.     | `null`             | "N/A" (no data)    |
| `"high"` etc.     | `0`                | "0"                |
| `"high"` etc.     | `> 0`              | show count         |

This prevents showing `reasoning_tokens: 0` for models like `granite-4.1-8b` that don't support reasoning at all, while still showing zero for reasoning models that happened to produce none.

## Display Layout per Surface

### TokenUsageChart bar

```
  ┌────────────────────────────────────────────────┐
  │  ████████████████████░░░░░░░░░░░░              │
  │  <- input ---> <- output -> <-reasoning->      │
  │     127K           16K          150            │
  └────────────────────────────────────────────────┘
```
Three stacked segments per bar: input (solid), output (medium), reasoning (light/translucent). Reasoning segment only appears when `reasoning_level` is set and data is present.

Chart height stays 350px. No Y-axis label change — axis still shows total tokens.

### TokenUsageChart tooltip

```
  ┌──────────────────────────────────────────────┐
  │  🔷 openai/gpt-5                              │
  │                                               │
  │  Text                                         │
  │    low:    143  (in 127 / out 16 / r 0)      │
  │    medium: 512  (in 127 / out 200 / r 185)   │
  │    high:   1.2K (in 127 / out 300 / r 773)   │
  │  ───────────────────────────────────          │
  │  Tokens in + out + reasoning.                 │
  └──────────────────────────────────────────────┘
```

Tooltip shows `in / out / r` breakdown. The `r` segment only appears when the model has a reasoning level.

### Model detail page

Current stats line:
```
127 in / 16 out tokens
```
Updated:
```
127 in / 16 out / 0 reasoning tokens
```
Or when no reasoning level:
```
127 in / 16 out tokens
```

### FixtureCard

Current compact display:
```
127       16
Input    Output
```
Updated (with reasoning level):
```
127     16     +0r
Input  Output  Reason
```
Without reasoning level: unchanged.

### ModelOutputCard

Inline badge changes from `127→16` to `127→16(+0r)` when reasoning level is set.

## TypeScript Type Changes

```typescript
// FixtureResult gains:
reasoning_tokens: number | null;

// ModelTokenSummary gains:
reasoning_tokens: number;
```

## OpenRouter Transcript Fix

In `OpenAIAdapter.generate()`, the transcript builder checks `message.reasoning_content`. OpenRouter puts reasoning in `message.reasoning` (and sometimes `message.reasoning_details`). Fix:

```python
reasoning_content = (
    getattr(message, "reasoning_content", None)
    or getattr(message, "reasoning", None)
)
```

This is a low-risk one-line change that fixes transcript capture for OpenRouter models without breaking OpenAI-native models (which use `reasoning_content`).

## File Touch List

| File | Change |
|------|--------|
| `gitbench/web/data/schema.sql` | Add `reasoning_tokens INTEGER` |
| `gitbench/render.py` | Extract + map `reasoning_tokens` in both paths |
| `gitbench/web/scripts/build-db.mjs` | Map `reasoning_tokens` in fixture_results INSERT |
| `gitbench/web/src/lib/types.ts` | Add field to `FixtureResult` + `ModelTokenSummary` |
| `gitbench/web/src/lib/node-sqlite-report-store.ts` | Add `SUM(reasoning_tokens)` to query; map result |
| `gitbench/web/src/lib/chart-data.ts` | Pass `model_token_summaries` (already done, verify) |
| `gitbench/web/src/components/charts/model-groups.ts` | Add `reasoningTokens` to `MetricEffort`; populate in `tokenMetric` |
| `gitbench/web/src/components/charts/TokenUsageChart.tsx` | Stacked bar segments + tooltip breakdown |
| `gitbench/web/src/components/charts/grouped-chart-ui.tsx` | Support 3-segment bars |
| `gitbench/web/src/pages/models/[provider]/[model]/[level].astro` | Add reasoning token display |
| `gitbench/web/src/components/fixtures/ModelOutputCard.astro` | Add reasoning to inline badge |
| `gitbench/web/src/components/fixtures/FixtureCard.astro` | Add reasoning to token grid |
| `gitbench/web/src/pages/fixtures/[benchmark]/[fixture].astro` | Pass `reasoning_tokens` prop |
| `gitbench/harness/model.py` | OpenRouter `reasoning` field fallback |
