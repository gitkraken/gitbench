## Purpose

Shadcn UI provides the component library and design system foundation for the GitBench web interface.

## Requirements

### Requirement: Tailwind CSS is configured
The Astro project SHALL use Tailwind CSS v4 with the `@tailwindcss/vite` plugin integrated via the Astro config. Existing CSS custom properties (`--bg`, `--surface`, `--card`, `--accent`, `--pass`, `--fail`, `--warn`, etc.) SHALL be mapped into Tailwind's `@theme` block so shadcn components render with the project's dark color palette.

#### Scenario: Tailwind utilities work in Astro templates
- **WHEN** an Astro component uses a Tailwind class (e.g., `class="bg-card rounded-xl"`)
- **THEN** the component renders with the project's `--card` background color and 12px border radius

#### Scenario: shadcn components match the existing dark theme
- **WHEN** a shadcn `Card` component renders
- **THEN** its background, border, and text colors match the existing `--card`, `--border`, and `--text` design tokens

### Requirement: shadcn/ui component primitives are available
The project SHALL have the following shadcn/ui components installed at `web/src/components/ui/`: Card, Badge, Button, Select, Command, Popover. Each component SHALL be generated via `npx shadcn@latest add` and placed in the standard `src/components/ui/` directory under the top-level web module. A `lib/utils.ts` SHALL provide the `cn()` utility for Tailwind class merging. The Button component's `outline` and `ghost` variants SHALL use a transparent accent tint on hover (`hover:bg-accent/20` for outline, `hover:bg-accent/10` for ghost) with text remaining the accent color (`hover:text-accent`), avoiding black text on hover.

#### Scenario: Developer adds a new shadcn component
- **WHEN** `npx shadcn@latest add dialog` is run from `web/`
- **THEN** `src/components/ui/dialog.tsx` is created and importable by other components

#### Scenario: cn() utility merges Tailwind classes
- **WHEN** a component uses `cn("px-4", condition && "bg-red-500")`
- **THEN** classes are correctly merged with Tailwind conflict resolution via `tailwind-merge`

#### Scenario: Outline button hover keeps text readable
- **WHEN** a user hovers over an outline variant button on the dark theme
- **THEN** the button background gains a subtle accent tint (~20% opacity) and the text remains the accent color (not black)

#### Scenario: Ghost button hover keeps text readable
- **WHEN** a user hovers over a ghost variant button on the dark theme
- **THEN** the button background gains a very subtle accent tint (~10% opacity) and the text remains the accent color (not black)

### Requirement: shadcn React components render server-side in Astro
shadcn React components (Card, CardHeader, CardContent, CardTitle, Badge, Button) SHALL be importable and usable directly in `.astro` files without any `client:*` directive. Astro SHALL render them to static HTML server-side with zero client-side JavaScript.

#### Scenario: Card renders in Astro page
- **WHEN** an Astro page renders `<Card><CardHeader><CardTitle>Hello</CardTitle></CardHeader></Card>`
- **THEN** the output HTML matches the structure and Tailwind classes of shadcn's Card component

#### Scenario: No JS payload for static shadcn components
- **WHEN** the page loads in a browser
- **THEN** no JavaScript is executed for Card, Badge, or Button components used without `client:*`

### Requirement: Inline styles are replaced with design system
All inline `style="..."` attributes in `.astro` and `.tsx` files SHALL be replaced with either Tailwind utility classes or shadcn component props. The shared CSS classes (`.result-pill`, `.tag-pill`, `.heat-pill`) SHALL be replaced with shadcn `Badge` components with appropriate variants.

#### Scenario: Pass/fail pill uses Badge component
- **WHEN** a fixture result displays a PASS badge
- **THEN** it renders as `<Badge variant="default" className="bg-pass-bg text-pass border-pass-border">PASS</Badge>`

#### Scenario: Filter selects use shadcn Select component
- **WHEN** the Explore page or Model Detail page renders a filter dropdown
- **THEN** it uses shadcn's `<Select>` component instead of a native `<select>` with inline styles
