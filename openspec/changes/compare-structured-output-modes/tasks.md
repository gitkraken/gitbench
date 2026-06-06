## 1. Fixture Contracts

- [x] 1.1 Add structured-output contract fields to fixture loading/types with backward-compatible defaults.
- [x] 1.2 Define contract templates for each benchmark/scoring family, including commit messages, git commands, branch lists, commit selections, numeric counts, hashes, stash refs, and resolved file content.
- [x] 1.3 Populate or derive concrete structured-output contracts for all 204 fixtures.
- [x] 1.4 Add fixture validation that fails when any fixture lacks a contract, has invalid JSON Schema, permits undeclared object properties, or has inconsistent required fields.
- [x] 1.5 Add canonicalization utilities that render structured payload fields back into scorer-compatible text.
- [x] 1.6 Add tests proving each fixture's expected answer can be represented by its structured schema and canonicalized back to the expected scorer text.

## 2. Harness and Provider Support

- [x] 2.1 Add `output_mode` configuration to the runner and CLI with `text` as the default and `json_schema` as the structured mode.
- [x] 2.2 Pass fixture structured-output contracts from the runner to model adapters only for JSON-schema mode.
- [x] 2.3 Implement OpenAI-compatible structured-output request serialization.
- [x] 2.4 Implement OpenRouter-compatible structured-output forwarding without breaking existing reasoning forwarding.
- [x] 2.5 Implement Ollama structured-output request serialization through native schema format support.
- [x] 2.6 Normalize structured provider responses into canonical text, raw structured output, parsed payload, output mode, usage, transcript, and API timing.
- [x] 2.7 Record structured parse and validation failures as failed fixture scores with useful errors.
- [x] 2.8 Add unit tests for adapter request shapes, response normalization, parse failures, and unsupported-provider behavior.

## 3. Result Schema and Aggregation

- [x] 3.1 Extend `Score` serialization with `output_mode`, raw structured output, parsed structured payload, and structured-output error fields.
- [x] 3.2 Extend run envelopes with top-level `output_mode` and default missing historical values to `text`.
- [x] 3.3 Update result deduplication to include `output_mode`.
- [x] 3.4 Update result doctoring and rerun replacement logic to preserve and match output mode.
- [x] 3.5 Update `aggregate_runs()` so text and JSON-schema runs for the same model remain separate variants while preserving provider/base-model/reasoning grouping.
- [x] 3.6 Add aggregation tests for same model plus same benchmark in both output modes.

## 4. Report Data and APIs

- [x] 4.1 Extend aggregate JSON types and generated `results.json` with output-mode-aware variants and structured-output fixture metadata.
- [x] 4.2 Update SQLite schema primary keys/indexes to distinguish model/output-mode variants.
- [x] 4.3 Update Python SQLite writer for output mode and structured-output payload columns.
- [x] 4.4 Update JavaScript SQLite builder for output mode and structured-output payload columns.
- [x] 4.5 Update report-store interfaces and Node SQLite queries to expose output mode and filter by mode where applicable.
- [x] 4.6 Update API route query validation to accept valid `output_mode` filters and reject invalid values.
- [x] 4.7 Add report DB and API tests covering text defaults, JSON-schema rows, compact omissions, and fixture-detail structured payloads.

## 5. Web UI

- [x] 5.1 Extend frontend data types and model grouping helpers with output-mode variants.
- [x] 5.2 Add an output-mode control next to model selectors with Text, JSON, and Both options.
- [x] 5.3 Synchronize output-mode state across charts without encoding mode into model group IDs.
- [x] 5.4 Update overview, benchmark, compare, and chart components to filter or expand by selected output modes.
- [x] 5.5 Add model detail text-vs-structured comparison with aggregate delta, benchmark deltas, agreement counts, and changed fixture links.
- [x] 5.6 Update fixture output cards to show structured payload fields and structured-output errors for JSON-schema results.
- [x] 5.7 Update history to display output mode and compute deltas against prior runs with matching output mode.
- [x] 5.8 Add focused component/page tests or API-backed smoke tests for output-mode selection and model detail comparison.

## 6. Verification

- [x] 6.1 Run Python unit tests for fixture validation, runner, model adapters, scoring, result doctoring, rendering, and CLI behavior.
- [x] 6.2 Run web API/report-store tests with `pnpm`.
- [x] 6.3 Build or smoke-test the web report with text-only historical data to verify backward compatibility.
- [x] 6.4 Generate a small text-vs-JSON-schema mock result set and verify report pages expose both modes separately.
- [x] 6.5 Run OpenSpec validation for `compare-structured-output-modes`.

## 7. Follow-up: Report Rendering Regressions

- [x] 7.1 Define the artifact contract for `gitbench run --output-mode both`: either write raw run envelopes where `gitbench report` expects raw run data, or teach report ingestion to recognize and load already-aggregated report JSON without treating it as the older combined-run shape.
- [x] 7.2 Update `load_runs_from_combined()` and `gitbench report` discovery so aggregate `results-v*.json` files with top-level `models`, `model_summaries`, `matrix`, and `fixtures` do not produce empty model identities.
- [x] 7.3 Include `output_mode` in report-time deduplication keys so same-model text and JSON-schema runs from the same timestamp are not collapsed.
- [x] 7.4 Restore backward-compatible CLI defaults and JSON output shape: `gitbench run` SHALL default to `text`, and `both` mode SHALL be opt-in. (Reversed in 8.1 — default is now `both`.)
- [x] 7.5 Add CLI/report regression tests for text default output, explicit `--output-mode both`, output directory + JSONL writes, model-worker concurrency counts, and report generation from newly produced both-mode artifacts.
- [x] 7.6 Fix report API `output_mode` filtering so query parameters are applied consistently rather than inferred only from composite model keys.
- [x] 7.7 Fix stale model links that still target `/models/<encoded full model>` after the provider/base-model/level route migration, including fixture output cards, history rows, heatmap labels, and compare links.
- [x] 7.8 Use `pnpm` for web build/dev commands invoked by `gitbench report`, replacing `npm run build` and `npx astro dev`.
- [x] 7.9 Re-run verification after fixes: `openspec validate compare-structured-output-modes --strict`, focused Python CLI/render tests, `pnpm test:api`, and `pnpm build`.

## 8. Default to Both + Full Visual Coverage

- [x] 8.1 Change `--output-mode` CLI default from `text` to `both` in `gitbench/cli.py` (click option + help text).
- [x] 8.2 Change `DEFAULT_OUTPUT_MODE` from `"text"` to `"both"` in `gitbench/harness/runner.py`.
- [x] 8.3 Change `build_run_envelope()` default parameter from `"text"` to `"both"` in `gitbench/cli.py`.
- [x] 8.4 Add `OutputModeSelector` to `QuadrantComparisonChart` and filter plotted points by the selected output mode.
- [x] 8.5 Add `OutputModeSelector` to `BenchmarkHeatmap` and filter model columns by the selected output mode.
- [x] 8.6 Add `OutputModeSelector` to `FixtureComparisonTable` and filter effort columns by the selected output mode.
- [x] 8.7 Switch `TimeSeriesChart` from local state to `useSyncedModelSelection`, add `OutputModeSelector`, and filter series by the selected output mode.
- [x] 8.8 Verify: run `gitbench run --benchmark blame_forensics --profile openrouter-demo` (defaults to both) produces both text and JSON-schema envelopes.
- [x] 8.9 Verify: `gitbench report` correctly aggregates both modes from raw envelopes into `results.json` and `gitbench.db`.
- [x] 8.10 Verify: `pnpm build` succeeds and all charts render with output-mode toggles synced globally.
