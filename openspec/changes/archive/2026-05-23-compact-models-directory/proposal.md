## Why

The Models index page (`/models`) serves as a directory for finding models, not a comparison tool. The current card-in-card layout (each base model in a `.card`, each reasoning level in a nested `.card`) consumes excessive vertical space and creates unnecessary visual weight. Info-circle tooltips ("i" badges) add noise to every level name and pass-rate badge. Cost data at 4 decimal places is meaningless at this zoom level. The page should be a quick-scan directory, not a dense data view.

## What Changes

- Remove the outer `.card` wrapper per base model; use the provider section as the visual grouping
- Replace inner `.card` level chips with compact styled chips (`bg-neutral-700`, thin border, tight padding, no shadow or gradient)
- Remove `has-tooltip` class from level labels and pass-rate badges on this page (keep `title` attributes for basic accessibility)
- Drop the cost display line from level chips on this page
- Tighten provider section spacing to reduce overall page height

## Capabilities

### New Capabilities
- `compact-models-directory`: A compact, scannable directory layout for the Models index page that uses lightweight chip components instead of nested cards

### Modified Capabilities
<!-- No existing spec requirements change — this is a pure layout/style change that doesn't alter data, routing, or behavior contracts -->

## Impact

- **Affected code**: `gitbench/web/src/pages/models/index.astro` (primary), `gitbench/web/src/styles/global.css` (possible new `.model-chip` utility class)
- **No API changes**: Static site build, `results.json` data shape unchanged
- **No new dependencies**: Uses existing Tailwind classes and CSS variables
