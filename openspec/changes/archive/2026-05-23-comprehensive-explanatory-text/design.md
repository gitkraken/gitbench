## Context

GitBench's web dashboard currently renders rich benchmarking data across 10 pages but provides almost no explanatory text, tooltips, or contextual help. The Methodology page is the only content-rich page. A first-time visitor cannot understand what any chart shows, what any metric means, or how to use the interface without reading the methodology page first.

The app is built with Astro (`.astro` pages for static content) and React islands (`.tsx` components for interactive charts using Recharts). The chart components already have Recharts `<Tooltip>` elements showing raw data (model names, effort levels, percentage values) but no explanatory content. The Astro pages have no tooltip infrastructure at all.

**Constraint**: Frontend-only changes. No backend, no CLI, no data pipeline modifications.

## Goals / Non-Goals

**Goals:**
- Add explanatory section blurbs to every page, every chart section, and every table
- Add tooltips on interactive elements (section labels, badges, filter controls, table headers, chart data points)
- Provide rich hover cards on React chart components with explanatory text below the data
- Ensure accessibility via `title` attribute fallbacks on all tooltip triggers
- Match the existing dark-themed visual design perfectly
- Zero new npm dependencies, zero new React islands for tooltips on Astro pages

**Non-Goals:**
- Tutorial or onboarding wizard / guided tour
- Interactive "how to read a chart" annotations
- Backend changes to fixture metadata, data models, or CLI
- Changes to chart rendering logic (only tooltip/enrichment additions)
- i18n or localization

## Decisions

### Decision 1: Pure CSS tooltips for Astro pages (not JS, not React islands)

**Rationale**: Astro pages are static and should stay static. Adding React islands just for tooltips would bloat the client bundle and cause layout shifts on hydration. CSS `::after` pseudo-elements with `data-tooltip` attributes provide rich hover cards with zero JavaScript, instant rendering, and no bundle impact. The `title` attribute serves as the universal fallback.

**Alternatives considered**:
- *shadcn/ui HoverCard*: Requires React islands on every Astro page. Overkill for text-only tooltips.
- *Vanilla JS tooltip script*: Requires a global event listener. Unnecessary complexity compared to CSS.
- *Web Component*: More flexible than CSS but adds a JS dependency and Shadow DOM complexity.

### Decision 2: Ⓘ icon as tooltip indicator (icon style TBD at implementation)

**Rationale**: A visible Ⓘ icon makes hover targets obvious for all users, including those on touch devices who can't hover to discover tooltips. More accessible than dotted underlines which may be confused with links or text-decoration.

**Implementation**: The tooltip trigger will use a thin, subtle icon rendered via CSS (pseudo-element or inline SVG) positioned after the trigger text. The exact visual style will be finalized during implementation to match the app aesthetic.

**Alternatives considered**:
- *Dotted underline*: Subtle but confusing (looks like a misspelling indicator or broken link).
- *Question mark `?`*: Less standard than `ⓘ` for informational tooltips.

### Decision 3: Section blurbs as inline prose (not card-wrapped)

**Rationale**: Section blurbs are page-level context that should feel like documentation, not UI widgets. Placing them as plain prose between the section label and the chart/table keeps the visual hierarchy clear and avoids "card overload." "Learn more →" links at the end of blurbs point to specific methodology sections.

### Decision 4: Enhanced Recharts Tooltip content (separator + explanation)

**Rationale**: The six React chart components already use Recharts `<Tooltip>` with a dark card style (`tooltipStyle`). Rather than replacing this system, we enrich the existing tooltip content by adding a thin visual separator followed by a brief explanatory sentence about what the metric means. This is minimal disruption with maximum informational value.

**Implementation pattern**:
```
[Existing: provider icon + model name]
[Existing: effort levels with values and labels]
[New: thin horizontal rule separator]
[New: 1-2 sentences explaining the metric shown]
```

### Decision 5: Enhanced `title` attributes on BenchmarkHeatmap cells (not custom tooltips)

**Rationale**: The BenchmarkHeatmap uses a plain HTML `<table>`, not a Recharts visualization. Adding a custom tooltip component would require refactoring the component. Enhanced `title` attributes provide immediate value with zero risk — the native browser tooltip appears on hover and contains the full structured description. This is the "best effort given what we have" approach.

**Format**: `"[model] on [benchmark]: [X]% ([passed]/[total] passed)[ — Strong/Moderate/Weak]"`

## Risks / Trade-offs

- **[CSS tooltips can't contain HTML]**: Tooltips are plain text only. Mitigation: "Learn more →" links go in section blurbs, not tooltips. Tooltips focus on immediate definitions; blurbs provide deeper context with links.
- **[CSS tooltips may overflow viewport edges]**: Long tooltips near the right/bottom edge could be clipped. Mitigation: Use `max-width: 280px` and position tooltips above the trigger element. For edge cases (mobile), the `title` attribute fallback ensures content is still accessible.
- **[`title` attribute duplication]**: Using both `data-tooltip` and `title` means content is duplicated in markup. Mitigation: Keep `title` text concise (one sentence) while `data-tooltip` can be richer. The duplication is manageable since content is static and hand-authored.
- **[Touch devices can't hover]**: CSS tooltips won't appear on touch. Mitigation: `title` attribute serves as the universal fallback — mobile users long-press to see the browser tooltip. Section blurbs also provide context without requiring hover.
- **[Chart tooltip changes are additive only]**: Adding text to existing tooltips increases their height. Mitigation: Keep explanatory text to 1-2 brief sentences. The existing tooltip cards are already well-sized.
