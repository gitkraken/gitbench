# Report Artifact Contract

GitBench report artifacts have one canonical source and one derived runtime
artifact.

- Python report aggregation owns `web/public/results.json`.
- The web module owns `web/data/schema.sql`, `web/scripts/build-db.mjs`, and
  `web/data/gitbench.db`.
- `web/data/gitbench.db` is always derived from `web/public/results.json` plus
  `web/data/schema.sql`; it is never the source of benchmark truth.

## Compatibility JSON

`web/public/results.json` is the compatibility artifact produced by
`gitbench report`. It must be standard JSON, so `NaN`, `Infinity`, and Python or
JavaScript-only values are invalid. Writers must serialize with strict JSON
settings and fail before replacing the checked-in artifact when data cannot be
serialized for browsers.

Required top-level sections:

- `models`
- `benchmarks`
- `fixtures`
- `fixture_index`
- `model_summaries`
- `model_runtimes`
- `matrix`
- `runs_meta`
- `base_model_groups`
- `campaigns`

Optional top-level sections currently recognized by the contract:

- `model_token_summaries`
- `safety_review`

Fixture results preserve the fields needed by report pages and database
derivation: fixture identity, pass status, similarity, model output, errors,
reasoning level, output mode, token usage, reasoning tokens, cost, wall timing,
API timing, fixture metadata, and structured-output metadata
(`parsed_payload`, `raw_structured_output`, `structured_error`).

Campaign entries preserve campaign metadata, trials, raw attempts, fixture
aggregates, model summaries, benchmark summaries, resource summaries, output
modes, publication state, and safety summary metadata. Raw attempts preserve
attempt identity, reasoning effort, output mode, cost, timing, token usage,
provider telemetry, judge evidence, result-safety state, and provenance when
present.

## SQLite Derivation

`web/scripts/build-db.mjs` is the supported SQLite build path. It reads
`web/public/results.json`, applies `web/data/schema.sql`, writes a temporary
database, inserts normalized report rows, runs `ANALYZE`, and atomically
renames the temporary database to `web/data/gitbench.db`.

The database exists for report API and build-time read paths. Schema changes,
column meaning changes, or JSON field changes used by `build-db.mjs` must update
this contract and its validation tests in the same change.

## Compatibility Rules

- Additive JSON fields are allowed when older web code can ignore them.
- Required top-level section changes must update the Python contract tests and
  the web artifact validator.
- Incompatible JSON or SQLite changes must define a versioning or migration path
  before implementation is considered complete.
- Safety metadata must be preserved when present. When result-safety publication
  requirements are configured, `gitbench report` must reject missing, stale, or
  modified safety metadata before checked-in public artifacts are updated.

## Validation Commands

Run Python contract validation:

```bash
python -m pytest tests/test_report_artifact_contract.py
```

Run web artifact validation from the web module:

```bash
cd web
pnpm validate:artifacts
```

Regenerate the derived SQLite artifact from the canonical JSON:

```bash
cd web
pnpm build:db
```
