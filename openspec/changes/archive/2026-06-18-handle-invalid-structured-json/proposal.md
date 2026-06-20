## Why

Structured-output runs can currently accept non-standard or out-of-contract JSON values as parsed payloads. A recent `gpt-oss-120b` result produced a raw structured output that Python parsed as infinity, which was then serialized into `web/public/results.json` as bare `Infinity`; the web app failed on the home page before any fixture detail UI could render.

## What Changes

- Treat structured-output JSON parsing as a strict validation boundary: non-standard JSON constants and non-finite numeric results are structured-output failures, not valid parsed payloads.
- Validate parsed structured payloads against the fixture contract before canonicalization and scoring.
- Preserve invalid structured responses as raw output strings plus structured-output error details instead of storing invalid parsed payloads.
- Keep generated report JSON parseable by browser-compatible `JSON.parse` semantics.
- Show structured-output parse/schema failures on fixture output cards with a clear message that includes the raw model output.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fixture-structured-output`: tighten structured response validation so strict JSON parse and schema validation happen before canonicalization, with invalid responses recorded as fixture failures.
- `json-export`: require report JSON artifacts to remain standard JSON and to represent invalid structured responses through raw output and error fields rather than non-finite parsed payloads.
- `report-pages`: require fixture detail output cards to display invalid structured-output errors with the raw model output.

## Impact

- Python harness structured-output parsing and validation.
- Benchmark runner structured-output failure handling.
- Aggregated `results.json` generation and strict JSON serialization guardrails.
- SQLite report database generation for structured-output payload fields.
- Fixture detail output card rendering in the Astro web app.
- Tests for strict parsing, schema failure handling, report JSON validity, and fixture display.
