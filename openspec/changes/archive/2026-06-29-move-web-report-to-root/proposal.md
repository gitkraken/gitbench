## Why

GitBench is already a monorepo in practice, but the Astro report app lives under
the Python package tree and several specs make the web app path part of shallow
interfaces. This blurs the boundary between benchmark data production and report
visualization, and it leaves two implementations responsible for producing the
same SQLite report database.

## What Changes

- Move the Astro report project from `gitbench/web/` to a top-level `web/`
  module without changing route behavior or report UI behavior.
- Define a shared report artifact contract covering the compatibility JSON and
  the SQLite database derived from it.
- Make `gitbench report` responsible for aggregating benchmark and campaign
  results into the compatibility JSON at `web/public/results.json`.
- Make the web module responsible for deriving `web/data/gitbench.db` from
  `web/public/results.json` using `web/data/schema.sql`.
- Deprecate `gitbench report` web build, dev-server, preview, and open-browser
  behavior. Deprecated flags should remain available during the transition and
  print clear guidance to use the web module commands.
- Update web commands, Vercel config, docs, tests, and OpenSpec specs to use the
  top-level `web/` module path.
- Keep checked-in report artifacts: `web/public/results.json`,
  `web/data/gitbench.db`, and `web/data/schema.sql`.
- **BREAKING**: Consumers that directly rely on `gitbench/web/...` paths must
  migrate to `web/...`.
- **BREAKING**: `gitbench report` no longer runs Astro build/dev/preview
  workflows as part of report generation.

## Capabilities

### New Capabilities

- `report-artifact-contract`: Defines the shared compatibility JSON and derived
  SQLite report artifact contract, including ownership, validation, versioning,
  safety metadata, and freshness expectations.

### Modified Capabilities

- `astro-site`: Move the Astro project requirement from the nested package path
  to the top-level `web/` module and keep static/API-backed site behavior.
- `json-export`: Narrow `gitbench report` to compatibility JSON publication and
  deprecated web-command guidance.
- `report-query-api`: Change SQLite generation ownership from Python report
  generation to the web module's JSON-to-SQLite derivation path.
- `embedded-chart-data`: Keep the build-time embedded chart behavior while
  updating database freshness and command paths for the top-level web module.
- `web-ui-typecheck`: Run typecheck and build verification from top-level `web/`.
- `shadcn-ui`: Update shadcn/ui component path requirements to the top-level web
  module.
- `lucide-icons`: Update the package dependency requirement to top-level
  `web/package.json`.
- `provider-brand-icons`: Update provider icon source paths to the top-level web
  module.
- `provider-logo-pattern`: Update provider logo implementation paths to the
  top-level web module.

## Impact

- **Python CLI**: `gitbench report` defaults, help text, deprecated flags,
  tests, and report artifact path resolution.
- **Python report rendering**: JSON aggregation remains; SQLite writer should be
  removed from the default publication path or kept only as a transitional test
  helper if implementation needs it.
- **Web module**: Move Astro app files, package files, Vercel config, tests,
  checked-in artifacts, build scripts, and documentation to `web/`.
- **Report artifacts**: `web/public/results.json` remains canonical; SQLite is
  rebuilt by web tooling from that JSON and checked in for runtime/deployment.
- **Tests**: Python CLI/report tests, web API/database tests, Astro check/build,
  artifact contract validation, and stale-path searches.
- **Docs/specs**: Root README, web README, developer docs, and path-bearing
  OpenSpec specs.
