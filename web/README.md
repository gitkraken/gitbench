# GitBench Web Report

The web report is a static Astro site with Vercel API functions for interactive
report data. `gitbench report` generates the compatibility JSON, and this web
module derives the SQLite database used by the API routes:

```text
public/results.json
data/gitbench.db
data/schema.sql
```

`public/results.json` remains a compatibility artifact for static build-time
data. Hydrated React islands should use `/api/*` report endpoints through the
browser report client instead of fetching the full JSON payload.

## Experimental WebMCP tools

In secure contexts, browsers that implement the experimental
`document.modelContext` imperative API discover six read-only report tools on
every page:

| Tool                         | Purpose                                   |
| :--------------------------- | :---------------------------------------- |
| `gitbench_get_overview`      | Compact report and leaderboard summary    |
| `gitbench_list_models`       | Exact model evaluation catalog            |
| `gitbench_get_model_results` | Filtered fixture results for one model    |
| `gitbench_get_benchmark`     | Benchmark leaderboard and fixture catalog |
| `gitbench_get_fixture`       | Fixture metadata and per-model evidence   |
| `gitbench_rank_models`       | Benchmark-scoped quality/resource ranking |

WebMCP is progressive enhancement: unsupported, insecure, disabled, duplicate,
or rejected registration leaves the ordinary report unchanged. The tools call
the existing `/api/*` routes and never fetch `public/results.json`.

List results default to 20 entries and are hard-capped at 50. Results include
`truncated` and `next_offset` pagination metadata. Raw prompt, expected-result,
model-output, and structured-output evidence is excluded by default. When
explicitly requested, each evidence field defaults to 2,000 characters and is
hard-capped at 8,000 characters. Fixture and model-result tools declare this
content untrusted because it may contain fixture-authored or model-generated
instructions.

To test in isolation, provide a `document.modelContext.registerTool` shim before
the shared layout script executes, collect the six definitions, and invoke each
definition's `execute` callback with mocked `fetch` responses. Pass an aborted
execution signal to verify pending report fetches are cancelled; aborting the
registration signal removes the catalog. The automated API suite includes this
shim-based coverage and does not require an experimental browser build.

## SQLite Runtime

API functions use Node's built-in `node:sqlite` module through the project
runtime requirement of Node 22.12 or newer. This avoids adding a native npm
SQLite dependency for Vercel/local development, keeps install friction low, and
isolates runtime-specific access behind `ReportStore` so a future Cloudflare D1
adapter can implement the same contract.

## Commands

Run these from top-level `web/` unless noted otherwise.

| Command                   | Action                                             |
| :------------------------ | :------------------------------------------------- |
| `pnpm install`            | Installs dependencies                              |
| `pnpm dev`                | Starts Astro only at `localhost:4321`              |
| `pnpm dev:api`            | Starts Astro and Vercel API routes together        |
| `pnpm build:og`           | Regenerates OpenGraph card PNGs with agent-browser |
| `pnpm validate:artifacts` | Validates JSON shape and SQLite freshness          |
| `pnpm build`              | Build your production site to `./dist/`            |
| `pnpm preview`            | Preview your build locally, before deploying       |
| `pnpm astro ...`          | Run CLI commands like `astro add`, `astro check`   |

Before running `pnpm dev:api`, generate report artifacts from the repository
root:

```sh
gitbench report
```

To rebuild only the SQLite database from the already-generated aggregate JSON,
run this from top-level `web/`:

```sh
pnpm build:db
```

The command reads `public/results.json`, applies `data/schema.sql`, loads the
tables inside one transaction, runs `ANALYZE`, and atomically replaces
`data/gitbench.db`.

To verify that the checked-in JSON, schema, and SQLite database are in sync:

```sh
pnpm validate:artifacts
```

To regenerate the checked-in OpenGraph card PNGs, run:

```sh
pnpm build:og
```

The command reads `scripts/og-cards.json`, renders
`scripts/og-card-template.html` in `agent-browser`, screenshots the fixed
`.card` element, verifies every PNG is `1200x630`, and writes the files to
`public/og/`. By default it uses `npx --yes agent-browser@0.27.0`; set
`AGENT_BROWSER_BIN=agent-browser` to use an installed binary instead.
