# provider-brand-icons Specification

## Purpose
TBD - created by archiving change improve-astro-output. Update Purpose after archive.
## Requirements
### Requirement: ProviderIcon maps provider slugs to Simple Icons
A `ProviderIcon` React component SHALL render the appropriate brand icon from `@icons-pack/react-simple-icons` for a given provider slug. The component SHALL accept a `provider` prop (lowercase string, e.g. `"anthropic"`, `"openai"`) and a `size` prop (number, default 16). It SHALL use `color="default"` on the icon component to render the brand's canonical color.

#### Scenario: Anthropic icon renders
- **WHEN** `<ProviderIcon provider="anthropic" size={16} />` renders
- **THEN** the Anthropic brand icon is displayed at 16×16 pixels in the Anthropic brand color

#### Scenario: OpenAI icon renders
- **WHEN** `<ProviderIcon provider="openai" size={20} />` renders
- **THEN** the OpenAI brand icon is displayed at 20×20 pixels in the OpenAI brand color

#### Scenario: Unknown provider falls back to initial circle
- **WHEN** `<ProviderIcon provider="unknown-provider" size={16} />` renders
- **THEN** a colored circle with the first letter "U" is displayed at 16×16 pixels

### Requirement: ProviderIcon supports known providers list
The component SHALL include a mapping from at least the following provider slugs to their Simple Icons components: `anthropic` (SiAnthropic), `openai` (SiOpenai), `google` (SiGoogle), `meta` (SiMeta), `mistral` (SiMistral), `deepseek` (SiDeepseek). The mapping SHALL be extensible by adding entries to the lookup table.

#### Scenario: All known providers render without error
- **WHEN** each provider in the known list is rendered
- **THEN** none throw an error; each displays its corresponding SVG icon

#### Scenario: New provider added to mapping
- **WHEN** a developer adds a new entry to the mapping table
- **THEN** the new provider renders its icon without other code changes

### Requirement: @icons-pack/react-simple-icons is a project dependency
The Astro web project (`gitbench/web/package.json`) SHALL list `@icons-pack/react-simple-icons` as a runtime dependency. Icons SHALL be imported with named imports (e.g., `import { SiAnthropic } from '@icons-pack/react-simple-icons'`) to enable tree-shaking.

#### Scenario: Dependency is in package.json
- **WHEN** checking `gitbench/web/package.json`
- **THEN** `@icons-pack/react-simple-icons` appears in `dependencies`

#### Scenario: Icons are tree-shakeable
- **WHEN** the site is built with `npm run build`
- **THEN** the output bundle only includes SVG code for icons actually imported in the source

