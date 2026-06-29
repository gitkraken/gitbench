## MODIFIED Requirements

### Requirement: Web UI typecheck passes
The web UI SHALL pass Astro TypeScript checking without error-level diagnostics.

#### Scenario: Error-level typecheck succeeds
- **WHEN** `pnpm exec astro check --minimumSeverity error` is run from top-level `web/`
- **THEN** the command exits successfully with zero error-level TypeScript diagnostics

### Requirement: Web UI build remains valid
The web UI MUST continue to build successfully after TypeScript fixes are applied.

#### Scenario: Production build succeeds
- **WHEN** `npm run build` or `pnpm build` is run from top-level `web/`
- **THEN** the build command exits successfully
