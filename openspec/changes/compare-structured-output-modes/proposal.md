## Why

GitBench currently evaluates each model from free-form text output only. Several fixture families would be easier for models to answer and easier for humans to inspect when the provider enforces a fixture-specific JSON schema with meaningful fields such as `commit`, `command`, `branches_to_delete`, or `resolved_content`.

We need to compare the same models across text and schema-enforced JSON modes without collapsing results into the same report bucket, and we need every fixture to define a valid structured-output contract before running the experiment.

## What Changes

- Add fixture-level structured-output contracts that define a strict JSON Schema, primary field/path, canonical text rendering, and display metadata for every fixture.
- Add a benchmark/fixture validation path that fails when any fixture lacks a valid structured-output contract or cannot render a representative structured answer back to scorer-compatible text.
- Add run-time output modes for normal text and schema-enforced JSON output.
- Preserve both the canonical text used by existing scorers and the raw/parsed structured payload returned by the provider.
- Record output mode in run envelopes, score payloads, aggregate JSON, SQLite report data, report APIs, and history metadata.
- Keep raw run artifacts and aggregated report artifacts distinguishable so `gitbench report` can regenerate the web data from newly produced text/JSON-schema runs without misreading aggregate JSON as raw run input.
- Update report grouping so text and structured runs for the same model/reasoning level are separate result variants but remain comparable under the same provider/base-model group.
- Add UI controls to filter or show both output modes next to the model selector.
- Add model detail comparisons for text vs structured JSON mode, including aggregate deltas, benchmark deltas, and per-fixture gain/loss rows.
- Change the default output mode from `text` to `both` so every benchmark run produces paired text and JSON-schema results by default. Text-mode runs remain possible by passing `--output-mode text` explicitly.
- Add output-mode toggle controls to every chart on every page (Quadrant Comparison, Benchmark Heatmap, Fixture Comparison Table, Time Series) for consistent visual coverage, synced globally via localStorage.

## Capabilities

### New Capabilities

- `fixture-structured-output`: Fixture-level JSON Schema contracts, validation, canonicalization, and provider-neutral structured-output request metadata.

### Modified Capabilities

- `json-export`: Aggregated report JSON includes output-mode-aware model variants and fixture-level structured-output metadata.
- `report-query-api`: SQLite report schema and APIs expose output mode and structured-output fields without merging text and structured runs.
- `report-pages`: Model, compare, benchmark, fixture, and history pages support output-mode selection and text-vs-structured comparison.
- `searchable-model-selector`: Model selector-adjacent state includes output mode filtering while preserving provider/base-model group selection semantics.
- `transcript-recording`: Recorded transcripts preserve structured-output request and response information sufficient for fixture debugging.

## Impact

- Python harness: fixture loading/types, model adapters, benchmark runner, score serialization, CLI run options, result doctoring/rerun handling, and fixture self-checking.
- Providers: OpenAI-compatible structured outputs via JSON Schema response format, OpenRouter-compatible forwarding, Ollama schema forwarding through native format support where available.
- Report generation: aggregate keying, JSON output, raw-vs-aggregate artifact ingestion, SQLite schema, Python and JavaScript DB builders, store abstraction, and API filter validation.
- Web UI: data types, model grouping helpers, model selector controls, comparison charts, model detail pages, fixture drilldowns, history views, and route/link behavior.
- Tests: fixture contract validation across all 204 fixtures, provider request serialization, canonicalization/scoring behavior, aggregation isolation by output mode, report ingestion from newly generated artifacts, report API coverage, UI route/component behavior, and static build coverage.
