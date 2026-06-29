## Context

The repository currently has a Python benchmark/data module and an Astro report
app, but the Astro app is nested at `gitbench/web/` inside the Python package
tree. The Python package discovery configuration includes `gitbench*`, so the
current layout also makes the web project look like part of the Python
distribution boundary.

Report generation is split inconsistently:

- `gitbench report` aggregates benchmark and campaign artifacts, writes
  `gitbench/web/public/results.json`, writes `gitbench/web/data/gitbench.db`
  through Python, and can run Astro build/dev/preview workflows.
- The web module also has `scripts/build-db.mjs`, and `pnpm build` rebuilds
  `data/gitbench.db` from `public/results.json` before Astro reads the database
  for build-time embedded chart data.

Several current specs encode stale locations (`gitbench/ui/` or
`gitbench/web/`) or stale ownership (`gitbench report` writes SQLite). The
migration should preserve report behavior while making the repo shape and
artifact boundary explicit.

## Goals / Non-Goals

**Goals:**

- Present GitBench as a monorepo with two peer modules: Python benchmark/data
  production and top-level web report visualization.
- Move the Astro report app to top-level `web/`.
- Make `web/public/results.json` the canonical compatibility artifact produced
  by the Python CLI.
- Make `web/data/gitbench.db` a checked-in, web-owned artifact derived from the
  compatibility JSON.
- Define a contract that covers both artifacts and can be validated from Python
  and TypeScript workflows.
- Keep existing report routes, API behavior, checked-in data, and visual output
  stable during migration.
- Update docs, tests, and OpenSpec specs so new contributors see one coherent
  architecture.

**Non-Goals:**

- Reworking report UI routes, chart behavior, or API response shapes.
- Introducing an `apps/` workspace layout.
- Removing the Python terminal UI package at `gitbench/ui/`.
- Preserving every old filesystem path as a compatibility alias.
- Regenerating benchmark results during CI, Vercel build, or migration.
- Changing campaign semantics, scoring, result safety policy, or raw attempt
  formats beyond documenting them in the artifact contract.

## Decisions

### Decision 1: Use top-level `web/` as the report module root

Move the existing Astro project from `gitbench/web/` to `web/`. Do not introduce
`apps/web/` because there is only one web application and the extra nesting would
not clarify ownership.

**Rationale:** The root should show two peer modules at a glance: `gitbench/`
for Python benchmark/data code and `web/` for report visualization. This also
keeps the web app outside Python package discovery.

**Alternative considered:** Keep `gitbench/web/` and improve docs. That would
leave the open-source presentation and packaging ambiguity intact.

### Decision 2: Treat compatibility JSON as canonical report input

`gitbench report` should aggregate legacy result envelopes, aggregate report
JSON, and campaign artifacts into `web/public/results.json`. The CLI should not
write SQLite by default.

**Rationale:** Python owns benchmark execution and aggregation. JSON is the
lowest-friction cross-language artifact and the stable input the web module can
derive from.

**Alternative considered:** Keep Python and TypeScript SQLite writers as equal
authorities. That preserves today’s duplication and makes schema changes harder
to reason about.

### Decision 3: Let the web module derive SQLite from JSON

`web/scripts/build-db.mjs` should be the supported SQLite build path. It reads
`web/public/results.json`, applies `web/data/schema.sql`, writes
`web/data/gitbench.db` atomically, and remains part of `web` build verification.

**Rationale:** The SQLite database exists to serve web runtime/API access paths,
so the web module should own its schema, build script, runtime assumptions, and
freshness checks.

**Alternative considered:** Keep a Python SQLite writer as production behavior.
That keeps Python coupled to web runtime schema details and leaves two places to
update on every schema change.

### Decision 4: Use a hybrid artifact contract

Create a readable contract plus executable validation. The prose should define
ownership, versioning, required top-level JSON fields, safety metadata
expectations, campaign/attempt representation, and the JSON-to-SQLite mapping.
The executable layer should include schema or validator checks that run in both
Python and web test workflows.

**Rationale:** A prose-only contract drifts. A schema-only contract is hard for
future maintainers to understand. The boundary is important enough to deserve
both.

**Alternative considered:** Let existing tests imply the contract. That is the
current locality problem in another form.

### Decision 5: Deprecate web-command flags as no-ops with guidance

`gitbench report` should keep `--no-build`, `--open`, and `--dev` during the
transition, but these flags should print deprecation guidance and not run Astro
build, dev, preview, or browser-opening behavior. The default command should
write the compatibility JSON and print the next web commands to run.

**Rationale:** Keeping the flags avoids immediate parser breakage while removing
the runtime coupling. A no-op is clearer than secretly delegating to the moved
web module.

**Alternative considered:** Warn and continue running old behavior. That would
preserve behavior but also preserve the architecture being removed.

### Decision 6: Do not add old-path compatibility aliases unless a concrete
workflow requires them

Implementation should update supported docs, specs, tests, and commands to
`web/...`. Old `gitbench/web/...` paths can fail unless a known user workflow is
identified during implementation.

**Rationale:** Path aliases add maintenance cost and reduce the clarity gained
by the move. This is a source-level repo restructuring, not a public HTTP route
change.

**Alternative considered:** Add symlinks or shim scripts at `gitbench/web/`.
That would reduce migration friction but could keep contributors using the old
mental model.

## Risks / Trade-offs

- **[Stale path references remain]** Specs, docs, tests, or scripts could still
  point to `gitbench/web/` or stale Astro `gitbench/ui/` paths. -> Mitigation:
  include stale-path search checks in the tasks and intentionally ignore only
  references to the Python terminal UI package.
- **[SQLite derivation parity regression]** Removing Python SQLite publication
  could lose rows currently inserted by Python. -> Mitigation: add contract and
  web `build-db` tests that cover aggregate data, campaigns, raw attempts,
  structured output, timing, cost, and safety metadata before removing Python
  from the default DB path.
- **[Build path assumptions break]** Vercel config, package scripts, `process.cwd`
  database paths, and tests may assume the old working directory. -> Mitigation:
  verify from `web/` with `pnpm test:api`, Astro check, `pnpm build`, and
  representative API route smoke tests.
- **[CLI users expect `gitbench report --open`]** Users may be used to one
  command building and opening the report. -> Mitigation: print explicit next
  commands such as `cd web && pnpm build` or `cd web && pnpm dev:api`.
- **[Checked-in artifacts become stale]** JSON and SQLite can diverge after the
  ownership split. -> Mitigation: add artifact freshness validation that rebuilds
  SQLite from JSON and fails if the checked-in DB is not current.

## Migration Plan

1. Add the report artifact contract docs and validation tests while the current
   layout still exists.
2. Move `gitbench/web/` to top-level `web/` and update package, Vercel, Astro,
   import, test, and docs paths without changing report UI behavior.
3. Update `gitbench report` defaults to write `web/public/results.json`; make
   web-command flags deprecated no-ops with guidance.
4. Make `web/scripts/build-db.mjs` the supported DB derivation path and remove
   Python SQLite writing from the default report command.
5. Refresh checked-in `web/public/results.json` and `web/data/gitbench.db` only
   through the supported artifact flow.
6. Update current OpenSpec specs and public docs to converge on `web/` and the
   JSON-to-SQLite artifact boundary.
7. Run Python tests, web tests, Astro check/build, artifact validation, and a
   stale-path search.

Rollback is file-structure based: restore the moved `gitbench/web/` tree and
the old CLI behavior if the migration cannot preserve current report behavior.
Because the change is not expected to alter public routes or data semantics,
runtime rollback should not require artifact regeneration.

## Open Questions

None blocking. During implementation, if a concrete external workflow depends
on `gitbench/web/...`, add a targeted compatibility note or shim instead of a
general old-path alias.
