## RENAMED Requirements

FROM: Report generation writes SQLite database
TO: Web module derives SQLite database

## MODIFIED Requirements

### Requirement: Web module derives SQLite database
The web module SHALL write a read-only SQLite report database at `web/data/gitbench.db` by deriving it from `web/public/results.json` using `web/data/schema.sql`. `gitbench report` SHALL NOT be the supported production writer for the SQLite database.

#### Scenario: Web command writes database artifact
- **WHEN** the supported database build command runs from `web/`
- **THEN** `web/data/gitbench.db` contains generated SQLite data for report API queries

#### Scenario: Existing database is rebuilt
- **WHEN** the database build command runs and a previous generated report database exists
- **THEN** the previous report data is replaced with data generated from the current compatibility JSON and latest schema

### Requirement: Report API stays within Vercel function budget
The web project SHALL expose the report API with no more than 11 Vercel serverless function route files under `web/api`.

#### Scenario: Consolidated API file count
- **WHEN** the report API route files are enumerated under `web/api`
- **THEN** there are no more than 11 TypeScript API route files

#### Scenario: Chart endpoints share one dynamic function
- **WHEN** the chart API routes are enumerated
- **THEN** the six chart names `cost`, `heatmap`, `pass-rate`, `quadrant`, `runtime`, and `tokens` are served by one dynamic chart function
- **AND** there are not separate serverless function files for each chart name
