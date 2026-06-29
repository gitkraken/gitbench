# web-ui-typecheck Specification

## Purpose
Define the web UI build-health contract for Astro TypeScript diagnostics, production builds, dashboard behavior preservation, and explicit shared TypeScript contracts.

## Requirements
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

### Requirement: Type fixes preserve dashboard behavior
The type fixes MUST preserve the existing web UI routes, report API response shapes, chart controls, fixture pages, and navigation behavior.

#### Scenario: Existing behavior is retained
- **WHEN** the TypeScript fixes are applied
- **THEN** no intentional route, dashboard interaction, report API contract, chart rendering, or visual design behavior is changed

### Requirement: Shared TypeScript contracts are explicit
The web UI SHALL use explicit shared TypeScript contracts for benchmark data, campaign-aware report data, model results responses, chart control props, and DOM interactions instead of relying on unresolved imports, implicit `any`, or `unknown` values at call sites.

#### Scenario: Shared contracts remove known diagnostic classes
- **WHEN** the implementation is checked by Astro's TypeScript checker
- **THEN** diagnostics caused by stale type imports, untyped JSON responses, inconsistent output-mode prop shapes, React prop mismatches in Astro templates, and un-narrowed DOM script values are absent
