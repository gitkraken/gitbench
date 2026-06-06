## Context

GitBench currently sends each fixture prompt as a single user message, receives text from the model adapter, and passes that text directly into the benchmark scorer. Result aggregation keys model data by the model name plus existing reasoning-level parsing. Report JSON, SQLite tables, API routes, and UI model grouping all assume one primary result variant for each model identity.

Structured JSON output changes that assumption. The same provider/base model/reasoning level can now be evaluated in `text` mode and in schema-enforced JSON mode. The structured response also needs fixture-specific semantics: a commit-message fixture is clearer as `{ "commit": "..." }`, a branch cleanup fixture as `{ "branches_to_delete": [...] }`, and a merge-conflict fixture as `{ "resolved_content": "..." }`.

## Goals / Non-Goals

**Goals:**

- Define a strict structured-output contract for every fixture.
- Run the same fixture/model combinations in text and schema-enforced JSON modes.
- Preserve scorer compatibility by canonicalizing structured payloads back to the existing expected text shapes.
- Keep text and structured results separate in storage and charts while grouping them under the same provider/base-model identity.
- Show direct text-vs-structured comparisons on model detail pages.
- Preserve raw structured payloads and parse/schema errors for debugging fixture-level results.

**Non-Goals:**

- Replace existing fixture scorers with JSON-native scoring in this change.
- Recalibrate fixture expected answers or scoring thresholds.
- Require all providers to support structured output. Unsupported providers may fail early or be skipped with a clear message.
- Add multi-attempt pass@k behavior beyond the existing one-output-per-fixture flow.

## Decisions

### Use `output_mode` as a first-class result dimension

Runs, scores, aggregate rows, API payloads, and UI data SHALL carry `output_mode`, with initial values `text` and `json_schema`.

Alternative considered: encode structured mode into the model name, such as `openai/gpt-4o:high+json`. This would avoid schema changes but would pollute model grouping, make text-vs-structured comparisons harder, and treat a run mode as a model identity.

### Keep raw run input distinct from aggregate report output

`gitbench report` SHALL only feed raw run envelopes or supported combined-run payloads into `aggregate_runs()`. If `gitbench run --output-mode both` writes an already-aggregated report JSON, report generation SHALL either load it through a dedicated aggregate-report path or ignore it during raw-run discovery. Aggregate JSON with top-level `models`, `model_summaries`, `matrix`, and `fixtures` MUST NOT be interpreted as the older combined-run format that nests model entries under `model` plus `results`.

Report-time deduplication SHALL include `output_mode` in addition to suite version, timestamp, and model name. This prevents same-timestamp text and JSON-schema runs for the same model from collapsing before aggregation.

### Store concrete fixture contracts, generated from templates where practical

Each fixture SHALL resolve to a concrete JSON Schema contract before a structured run starts. Most contracts can be generated from benchmark/scoring templates, but the generated contract is still fixture-specific and auditable.

The contract shape should include:

- `schema`: strict JSON Schema object sent to providers.
- `primary_field` or `primary_path`: field/path used for canonical text.
- `canonicalize`: rendering strategy such as string, lines, command lines, numeric string, or file block.
- `display_label`: human-readable field label for fixture drilldowns.

Alternative considered: one generic `{ "answer": "..." }` schema. This is simpler, but it loses semantic value and does not test whether structured output helps models express the right kind of answer.

### Score canonical text, preserve raw structured data

Existing scorers continue to score `model_output`, which is the canonical text rendered from the structured payload. Structured runs also store raw provider text, parsed payload, and structured errors.

Alternative considered: create JSON-native scorers immediately. That would increase scope and risk by changing scoring semantics at the same time as output mode collection.

### Require fixture contract self-checks

Fixture validation SHALL fail if any fixture lacks a contract, has invalid JSON Schema, has required fields missing from properties, allows additional properties unexpectedly, or cannot render a representative structured expected value back to the scorer-compatible expected text.

This keeps the experiment from silently comparing partial fixture coverage.

### Keep provider-specific request details inside adapters

The runner asks the model adapter for structured mode with a provider-neutral contract. Adapters translate it into OpenAI-compatible `response_format`, OpenRouter-compatible forwarding, or Ollama native `format` behavior.

Provider responses are normalized into a common model response dict containing canonical text, raw structured output, parsed payload, output mode, usage, transcript, and API timing.

### Extend grouping rather than replacing the model selector

Provider/base-model selection remains group-based. Output mode is a separate selector next to model selection, with choices such as `Text`, `JSON`, and `Both`.

When `Both` is selected, charts may expand each selected model effort into two variant series. The model detail page receives a dedicated text-vs-structured comparison section rather than relying only on generic compare-page charts.

## Risks / Trade-offs

- Provider schema dialect differences -> Keep the fixture contract provider-neutral, use strict common JSON Schema features, and cover adapter serialization with tests.
- Structured payloads can be valid JSON but semantically wrong -> Always canonicalize to existing scorer text and record structured payload separately.
- Per-fixture schemas can drift from fixture intent -> Add an all-fixture audit and make missing/invalid contracts block structured runs.
- UI charts can become visually crowded when `Both` doubles visible variants -> Default output mode to `Text`, provide explicit `Both`, and keep model detail comparison focused on one model/effort at a time.
- Result schema changes can break older reports -> Treat missing `output_mode` as `text` during loading and aggregation.
- Result artifact ambiguity can break new reports -> Keep raw run artifacts and aggregate report artifacts distinguishable, and add a regression that runs `gitbench report` against artifacts produced by `gitbench run --output-mode both`.
- Report DB builder drift can occur because Python and JavaScript both write SQLite -> Update and test both builders for output-mode columns and structured payload fields.

## Migration Plan

1. Add backward-compatible fields and loaders that default missing `output_mode` to `text`.
2. Add fixture structured-output contracts and validation without changing default run behavior.
3. Add text/JSON run modes and provider adapter support.
4. Extend result aggregation, JSON export, SQLite schema, and APIs.
5. Update UI controls and comparison pages.
6. Validate existing historical result files still render as text-mode data.
7. Validate newly generated text/JSON-schema artifacts can regenerate `public/results.json`, `data/gitbench.db`, and a static web build without empty model identities or route generation failures.

Rollback is straightforward before structured runs are generated: remove the new output-mode UI and ignore new fields. After structured runs exist, report loaders can still treat `json_schema` variants as separate rows or filter them out.
