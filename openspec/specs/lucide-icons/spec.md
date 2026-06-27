## Purpose

Lucide icons provide a consistent, lightweight icon set used throughout the GitBench web interface.

## Requirements

### Requirement: Sidebar uses Lucide icons
The Sidebar component SHALL render Lucide SVG icons instead of unicode emoji characters for all navigation links. Icons SHALL be imported from `lucide-react` and rendered server-side by Astro (no `client:*` directive) to avoid client-side JavaScript for static icons. The History link has an icon mapping (`History`) but is hidden from the sidebar per the astro-site spec.

#### Scenario: Dashboard icon renders as SVG
- **WHEN** the page loads
- **THEN** the Dashboard nav link displays a `LayoutDashboard` Lucide SVG icon, not the unicode character `◉`

#### Scenario: All visible icons are Lucide SVGs
- **WHEN** the sidebar renders
- **THEN** each visible nav link displays its mapped Lucide icon: LayoutDashboard, Cpu, BarChart3, Search, GitCompare, BookOpen

### Requirement: Icon sizes are consistent
All sidebar icons SHALL render at 18×18 pixels (1.125rem) with `stroke-width="2"`. Icons SHALL inherit the current text color via `currentColor` so they respond to the sidebar's active/hover states.

#### Scenario: Icon inherits active link color
- **WHEN** a sidebar link is active (`.sidebar-link.active`)
- **THEN** its icon renders in `var(--accent)` (cyan) matching the link text color

#### Scenario: Icon inherits default link color
- **WHEN** a sidebar link is not active
- **THEN** its icon renders in `var(--text-dim)` matching the link text color

### Requirement: Icons are vertically aligned with labels
Each icon SHALL be vertically centered with its adjacent label text. The existing flexbox layout (`display: flex; align-items: center`) SHALL be preserved.

#### Scenario: Icon and label share baseline
- **WHEN** the sidebar renders a link
- **THEN** the SVG icon and the label text are vertically centered within the link row

### Requirement: lucide-react is a project dependency
The `lucide-react` package SHALL be added to `gitbench/web/package.json` as a production dependency.

#### Scenario: Build succeeds with lucide-react
- **WHEN** `npm run build` is executed
- **THEN** the Astro build completes without errors related to Lucide imports

#### Scenario: No client JS for sidebar icons
- **WHEN** the page loads in a browser
- **THEN** no React or Lucide JavaScript is loaded for sidebar icons (they render server-side as static SVGs)
