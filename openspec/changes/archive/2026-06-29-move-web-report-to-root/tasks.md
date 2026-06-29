## 1. Baseline Inventory

- [x] 1.1 Record the current dirty worktree state and avoid modifying unrelated user changes.
- [x] 1.2 Inventory all repo references to `gitbench/web`, stale Astro `gitbench/ui`, `ui/public`, `ui/dist`, `web/public/results.json`, and `web/data/gitbench.db`.
- [x] 1.3 Classify `gitbench/ui` references as Python terminal UI or stale Astro-web references before changing them.
- [x] 1.4 Identify all commands and tests that currently run from `gitbench/web`.

## 2. Report Artifact Contract

- [x] 2.1 Add prose documentation for the report artifact contract, including ownership, required JSON sections, SQLite derivation, safety metadata, compatibility rules, and validation commands.
- [x] 2.2 Add executable validation for the compatibility JSON top-level shape and standard-JSON serialization expectations.
- [x] 2.3 Add validation for JSON-to-SQLite derivation freshness using `results.json`, `schema.sql`, and `gitbench.db`.
- [x] 2.4 Ensure contract coverage includes campaigns, trials, raw attempts, fixture aggregates, structured-output metadata, output modes, reasoning levels, cost, timing, token usage, and result-safety metadata.
- [x] 2.5 Add or update Python and web tests so both sides exercise the artifact contract.

## 3. Move The Web Module

- [x] 3.1 Move the existing Astro project from `gitbench/web/` to top-level `web/` without changing routes, components, API handlers, or UI behavior.
- [x] 3.2 Move checked-in report artifacts to `web/public/results.json`, `web/data/gitbench.db`, and `web/data/schema.sql`.
- [x] 3.3 Update web package metadata, package scripts, lock/workspace files, Astro config, Vercel config, shadcn config, TypeScript config, and path aliases for the new root.
- [x] 3.4 Update web tests and API route-count tests to enumerate paths under `web/`.
- [x] 3.5 Confirm the Python package discovery boundary no longer includes the Astro app as `gitbench.web`.

## 4. Narrow `gitbench report`

- [x] 4.1 Update default report output path resolution to publish compatibility JSON at `web/public/results.json`.
- [x] 4.2 Remove SQLite writing from the default `gitbench report` publication path.
- [x] 4.3 Keep `--no-build`, `--open`, and `--dev` as deprecated transition flags that warn, do not run web workflows, and print the replacement web commands.
- [x] 4.4 Update CLI help text, README examples, and tests to describe JSON publication rather than build/dev/preview behavior.
- [x] 4.5 Preserve campaign artifact ingestion, aggregate report ingestion, result-safety validation, strict JSON serialization, and historical output-mode compatibility.

## 5. Web-Owned SQLite Derivation

- [x] 5.1 Make `web/scripts/build-db.mjs` the supported command for deriving `web/data/gitbench.db` from `web/public/results.json`.
- [x] 5.2 Verify the web database build path inserts all report data required by API routes, including campaign rows and raw attempts.
- [x] 5.3 Keep `web/package.json` build chaining `build:db` before `astro build`.
- [x] 5.4 Update runtime database path assumptions so API functions read `web/data/gitbench.db` in local, build, and Vercel contexts.
- [x] 5.5 Remove or demote Python SQLite writer tests if the writer is no longer supported behavior, while preserving contract tests that prove JSON can derive the runtime database.

## 6. Docs And Specs

- [x] 6.1 Update root README report generation and project structure sections.
- [x] 6.2 Update the web README command and artifact sections after the module move.
- [x] 6.3 Update developer docs such as provider logo guidance, fixture calibration notes, and audit docs to use top-level `web/` paths where they refer to the Astro app.
- [x] 6.4 Confirm current OpenSpec deltas cover all modified capabilities named in the proposal.
- [x] 6.5 Leave valid `gitbench/ui` Python terminal UI references intact.

## 7. Verification

- [x] 7.1 Run Python report/CLI tests covering `gitbench report`, aggregation, campaign ingestion, result safety, and artifact validation.
- [x] 7.2 Run web API and database tests from top-level `web/`.
- [x] 7.3 Run Astro typecheck from top-level `web/`.
- [x] 7.4 Run production build from top-level `web/` and confirm `build:db` runs before `astro build`.
- [x] 7.5 Smoke test representative API routes against the checked-in SQLite artifact.
- [x] 7.6 Search for stale `gitbench/web`, stale Astro `gitbench/ui`, `ui/public`, and `ui/dist` references and resolve or explicitly justify any remaining matches.
- [x] 7.7 Run OpenSpec status/validation for `move-web-report-to-root` before implementation is considered ready to archive.
