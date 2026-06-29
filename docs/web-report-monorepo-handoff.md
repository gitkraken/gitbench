# Web Report Monorepo Architecture Handoff

## Reader And Action

This document is for an OpenSpec explorer or future maintainer landing cold.
After reading it, they should be able to write an OpenSpec proposal that moves
the Astro report app to the repository root, updates the report artifact
contract, and preserves existing report behavior during migration.

This is not an implementation plan ready for coding. It records the architecture
direction and the decisions that should shape the proposal.

## Current Friction

GitBench is a monorepo, but the repository shape does not say that clearly. The
Python benchmark runner is the core data producer. The Astro report is the
visualizer for that generated data. Today the report app is physically nested
inside the Python package tree, which makes the repo look like a Python package
with a web app hidden inside it.

That creates two kinds of friction:

- Open-source presentation: contributors must infer that the report app is a
  peer module, not Python package internals.
- Locality: report-generation knowledge is spread across the Python CLI,
  Python report rendering, the Astro app, web build scripts, checked-in
  artifacts, README guidance, and OpenSpec specs.

The current shape also makes the report-site path part of several shallow
interfaces. Callers need to know where the app lives and where each artifact is
written instead of depending on a small report artifact module with a stable
interface.

## Decisions So Far

The proposed architecture should follow these decisions:

- GitBench is a monorepo with a Python benchmark/data module and a top-level web
  report module.
- The Astro app should move to a top-level `web/` directory. There is no expected
  need for an `apps/` layout.
- The Astro app is the visualizer of data produced by GitBench, not part of the
  Python package implementation.
- `gitbench report` should stop being responsible for running the Astro dev
  server, preview server, or production build.
- `gitbench report` should aggregate individual benchmark results into the
  compatibility JSON artifact.
- The web module should own the report artifacts it consumes, including the
  compatibility JSON and SQLite database.
- The compatibility JSON and SQLite database should stay checked in. They are
  stable report artifacts from GitBench runs, and regenerating them during CI or
  Vercel builds would be too expensive.
- The stable report contract should cover both artifacts: the compatibility JSON
  and the SQLite database derived from it.
- The report contract should be shared and hybrid: prose contract documentation
  plus schema/tests that both Python and TypeScript workflows satisfy.
- Existing behavior should continue to work during migration. Path changes are
  acceptable, but the proposal should include enough tests to prove the migration
  is clean.
- Compatibility aliases for old paths are not required unless OpenSpec finds a
  concrete user workflow that would otherwise break. The goal is working
  behavior, not preserving every old path.

Target artifact locations after the move:

- Compatibility JSON: `web/public/results.json`.
- SQLite database: `web/data/gitbench.db`.
- SQLite schema: `web/data/schema.sql`.

Historical docs and specs may mention either `gitbench/ui/` or `gitbench/web/`.
The proposal should treat both as stale project locations and converge on the
top-level `web/` module.

## Proposed Module Shape

The repository should present two peer modules:

- **Benchmark data module**: the Python CLI and harness. It runs benchmarks,
  aggregates run envelopes, applies safety checks, and publishes report input.
- **Web report module**: the Astro app. It consumes checked-in report artifacts,
  serves query-shaped report data, renders the visual report, and owns
  deployment/runtime details.

The important seam is the report artifact contract. The Python module should not
need to understand the web app's runtime or development commands. The web module
should not need to understand benchmark execution internals.

The deletion test points to the same shape:

- If the top-level web module were deleted, benchmark execution should still
  work and still be able to produce report input.
- If the Python benchmark module were deleted, the web module should still be a
  coherent report viewer over its checked-in artifacts.
- If the report artifact contract were deleted, JSON shape and database shape
  assumptions would reappear across Python, TypeScript, tests, docs, and build
  scripts. That means the contract is earning its keep as a deep module.

## Report Artifact Contract

The report artifact contract should describe the two artifacts as a pair:

- Compatibility JSON: the cross-language aggregate produced by `gitbench report`.
- SQLite database: the web runtime artifact derived from the compatibility JSON.

The contract should define:

- Required top-level JSON fields.
- Checked schema files or equivalent machine-readable constraints.
- Versioning and compatibility expectations.
- Safety metadata expectations for public artifacts.
- How model identity, output mode, reasoning level, fixtures, campaigns, costs,
  timing, and token usage are represented.
- Which SQLite schema is current and how it maps from the JSON artifact.
- Whether the SQLite database is authoritative or derived. The current direction
  is that it is derived from the compatibility JSON and owned by the web module.
- Required validation tests before checking in updated artifacts.

This gives callers leverage: Python publishes one report input; web code can
serve many query-shaped views from a local runtime database. It also improves
locality: schema changes happen at the artifact seam instead of being scattered
through ad hoc path and shape assumptions.

## CLI Direction

The proposal should narrow `gitbench report` to artifact publication.

Recommended behavior:

- Default behavior writes the compatibility JSON artifact under the web module.
- Build, dev-server, preview, and open-browser behavior is deprecated.
- Deprecated flags should continue to exist for a transition period with clear
  warnings, unless OpenSpec decides to remove them immediately.
- The web module retains its own commands for local Astro development, API-backed
  development, production build, and SQLite database rebuild.

This keeps the Python CLI focused on data production and leaves web runtime
behavior behind the web module's interface.

## Migration Plan For OpenSpec

The OpenSpec proposal should be split into small, independently verifiable
changes:

1. Move the Astro app to top-level `web/` without changing its internal route or
   UI behavior.
2. Update the Python report command defaults so generated compatibility JSON is
   written to the new web artifact location.
3. Decide and implement the SQLite ownership change. The recommended direction
   is: Python writes JSON; web derives the SQLite database from JSON.
4. Add or update the shared report artifact contract documentation and validation
   tests. This should be a hybrid contract: readable prose plus checked schema
   files or equivalent executable validation.
5. Deprecate report build/server flags while keeping compatibility during the
   transition.
6. Update README and web README instructions.
7. Update OpenSpec specs that still describe old paths or old responsibilities.
8. Verify Python tests, web tests, Astro typecheck/build, and artifact freshness.

## OpenSpec Areas To Synchronize

At minimum, the proposal should review and update these existing specs:

- `astro-site`: currently describes the Astro project location and static report
  artifact behavior.
- `report-query-api`: currently says report generation writes the SQLite
  database under the web project and references the old API path shape.
- `embedded-chart-data`: currently assumes the web build rebuilds the database
  before Astro build.
- `web-ui-typecheck`: currently names the old web project path.
- Any report pages, report URL state, chart, campaign, or API specs that include
  hardcoded web project paths.

The proposal should also update public docs:

- Root README report generation section.
- Root README project structure section.
- Web README command and artifact sections.
- Any developer docs that point contributors to the current nested web path.

## Test And Verification Expectations

The OpenSpec proposal should require verification across both modules:

- Python CLI tests for report artifact generation.
- Python render/aggregation tests for JSON compatibility.
- Contract validation tests that exercise the shared report artifact contract.
- Web artifact/database tests for JSON-to-SQLite derivation.
- Web route/API tests against the checked-in SQLite artifact.
- Astro typecheck and production build from the new top-level web module.
- A docs check by search for stale nested web paths after migration.
- Migration tests or smoke checks proving the supported commands still work from
  their new locations.

The test surface should cross the same seam contributors use: the report
artifact contract. Tests that reach around the contract will recreate the
current locality problem.

## Open Questions

These should be resolved during OpenSpec exploration:

- Should deprecated `gitbench report` build/server flags warn and no-op, warn and
  still run the old behavior, or be removed in the same change?
- Should the web module's checked-in SQLite artifact always be regenerated by a
  web command, or should Python keep a low-level SQLite writer only for tests and
  migration compatibility?
- Should the checked-in compatibility JSON be treated as the canonical source for
  the checked-in SQLite artifact, or can either artifact be updated independently?
  The recommended answer is that JSON is canonical and SQLite is derived.
