## MODIFIED Requirements

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
