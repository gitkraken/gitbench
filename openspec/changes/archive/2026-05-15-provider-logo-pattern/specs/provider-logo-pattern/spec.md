## ADDED Requirements

### Requirement: Provider logo resolution follows a documented two-step process

When adding a new model provider to GitBench, the developer SHALL follow a documented process to provide a brand logo. The process document SHALL be located at `docs/agents/provider-logos.md`. The process SHALL cover two tiers in priority order:

1. **Custom inline SVG**: Create an inline React SVG component in `gitbench/web/src/lib/custom-provider-icons.ts` and register it in the `PROVIDER_ICONS` lookup table in `ProviderIcon.tsx`.
2. **Automatic fallback**: If no SVG is provided, the system automatically renders a colored circle with the provider's first letter — no code changes needed.

#### Scenario: Developer follows documented process for new provider

- **WHEN** a developer reads `docs/agents/provider-logos.md` after being asked to add a new provider
- **THEN** the document contains step-by-step instructions for creating a custom SVG component and registering it, including code snippets and file paths

#### Scenario: New provider added via custom SVG

- **WHEN** a developer needs to add a logo for a new provider
- **THEN** the documented process tells them to add an inline React SVG component in `custom-provider-icons.ts` using `currentColor` for monochrome logos, and one entry to the `PROVIDER_ICONS` table

#### Scenario: Provider without a logo renders automatic fallback

- **WHEN** a new provider is added to GitBench but no logo SVG is created
- **THEN** the documented process explains that a colored initial circle renders automatically with no code changes

### Requirement: Custom provider icons module is documented for discoverability

The `gitbench/web/src/lib/custom-provider-icons.ts` file SHALL include a JSDoc comment at the top explaining its purpose as the canonical source of brand logos for GitBench providers. Each custom SVG component in the file SHALL include a JSDoc comment identifying the provider name and, where applicable, the source of the logo (e.g., official brand assets page).

#### Scenario: Module has explanatory header

- **WHEN** a developer opens `custom-provider-icons.ts`
- **THEN** the first comment explains that this file contains custom brand SVGs for all GitBench model providers

#### Scenario: Each custom icon is documented

- **WHEN** a developer inspects a custom SVG component in the file
- **THEN** a JSDoc comment identifies the provider and the logo source
