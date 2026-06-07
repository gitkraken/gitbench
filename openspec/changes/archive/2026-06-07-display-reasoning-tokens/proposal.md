## Why

Reasoning tokens are collected from API responses and persisted in result JSON files, but they are invisible to users. Every place that shows token counts—the chart, model detail page, fixture cards, model output cards—shows input and output tokens but omits reasoning tokens entirely. The database schema, both data ingestion paths, and the TypeScript type system all lack reasoning token support. When users run reasoning models (o3-mini, GPT-5, etc.), the most expensive and interesting part of their token consumption is hidden.

Additionally, OpenRouter normalizes the reasoning text field to `message.reasoning`, but the adapter only checks the OpenAI-native `message.reasoning_content`, so reasoning transcripts from OpenRouter are silently dropped.

## What Changes

- Add `reasoning_tokens INTEGER` column to the SQLite `fixture_results` table.
- Extract and map `reasoning_tokens` in the Python report builder (`render.py`) and JS ingestion script (`build-db.mjs`).
- Add `reasoning_tokens` field to TypeScript types (`FixtureResult`, `ModelTokenSummary`).
- Include `SUM(reasoning_tokens)` in the report store token summaries query.
- Render reasoning tokens as a third stacked segment in the token usage chart, using a lighter tint of the provider color. Only show when any effort in the group has a reasoning level.
- Show `in / out / r` breakdown in the chart tooltip, with the `r` portion only when reasoning level is set.
- Display reasoning token count on the model detail page stats line, gated by `reasoning_level` presence.
- Show compact reasoning count in `ModelOutputCard` inline badge as `127→16(+150r)` and in `FixtureCard` as a third column.
- Fix OpenRouter transcript capture by falling back to `message.reasoning` when `message.reasoning_content` is absent.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `reasoning-token-measurement`: Extended to require database storage and token summary aggregation, not just Score-level collection.
- `token-usage-chart`: Chart gains stacked reasoning segment, tooltip gains `in / out / r` breakdown.
- `report-pages`: Model detail page, ModelOutputCard, and FixtureCard gain reasoning token display.
- `transcript-recording`: OpenRouter `reasoning` field handled as fallback for `reasoning_content`.

## Impact

- Database schema migration needed for existing SQLite databases (backward-compatible: new nullable column).
- `gitbench/render.py`: Two extraction points (report JSON builder + DB writer) + INSERT SQL.
- `gitbench/web/scripts/build-db.mjs`: INSERT column list + value mapping.
- `gitbench/web/src/lib/types.ts`: Two interface additions.
- `gitbench/web/src/lib/node-sqlite-report-store.ts`: Query + result mapping.
- `gitbench/web/src/components/charts/model-groups.ts`: `MetricEffort` + `tokenMetric` extractor.
- `gitbench/web/src/components/charts/TokenUsageChart.tsx`: Stacked segments + tooltip format.
- `gitbench/web/src/components/charts/grouped-chart-ui.tsx`: 3-segment bar support.
- `gitbench/web/src/pages/models/[provider]/[model]/[level].astro`: Stats line.
- `gitbench/web/src/components/fixtures/ModelOutputCard.astro`: Inline badge.
- `gitbench/web/src/components/fixtures/FixtureCard.astro`: 3-column token grid.
- `gitbench/web/src/pages/fixtures/[benchmark]/[fixture].astro`: Prop pass-through.
- `gitbench/harness/model.py`: One-line fallback for OpenRouter reasoning field.
