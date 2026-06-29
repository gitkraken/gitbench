## MODIFIED Requirements

### Requirement: Build script chains database rebuild before Astro build
The top-level `web/package.json` `build` script SHALL chain `build:db` before `astro build` so that `web/data/gitbench.db` is guaranteed fresh with `web/public/results.json` when Astro reads it at build time for embedded data computation.

#### Scenario: Build rebuilds database first
- **WHEN** `npm run build` or `pnpm build` is executed from `web/`
- **THEN** `build-db.mjs` runs first to rebuild `data/gitbench.db` from `public/results.json`
- **AND** `astro build` runs after the database is fresh

#### Scenario: Build fails if database rebuild fails
- **WHEN** `build-db.mjs` fails during `npm run build` or `pnpm build` from `web/`
- **THEN** `astro build` does not execute
- **AND** the build process exits with a non-zero status
