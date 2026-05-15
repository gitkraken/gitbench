## Context

The GitBench Astro site (`gitbench/web/`) renders aggregated benchmark data from `results.json`. The data is produced by `gitbench/render.py`'s `aggregate_runs()` function. Currently:

- Model names come from OpenRouter as `provider/base-model:level` (e.g., `anthropic/claude-opus-4.7:low`), but `parse_model_name()` in the harness splits on `#`, so reasoning levels are never extracted
- The `/models` page is a flat grid of cards — all models at equal visual weight regardless of being different reasoning levels of the same base model
- URLs use `~`-encoding to represent special characters in flat slugs (`/models/anthropic~claude-opus-4.7~low`)
- The model summary chart uses horizontal bars — fine for 5-10 models, doesn't scale to 50+
- Cost comparison uses average per-fixture cost, but total cost of a full run is more interpretable: "this evaluation cost $0.53" vs "$0.0026 per fixture"

Constraint: only `render.py` (aggregation) and the Astro web code change. Fixtures, benchmarks, and harness code are out of scope.

## Goals / Non-Goals

**Goals:**
- Parse model names into provider, base model, and reasoning level at the aggregation layer
- Group models on the index page for visual hierarchy as the model count grows
- Clean URL structure with nested paths (no encoding hacks)
- Vertical bar chart with diagonal labels for the model summary — space-efficient for many models
- Total cost (not avg per fixture) as the primary cost metric
- Provider brand icons for visual scanning in selectors and chart labels

**Non-Goals:**
- Redirects for old URLs
- Changing any fixture YAML files or benchmark Python code
- Changing the harness model interface or `parse_model_name` in `harness/model.py`
- Adding new chart types or visualization features beyond the three stated changes
- Server-side rendering of charts (they remain React `client:load` islands)

## Decisions

### Decision 1: Parse model names in `aggregate_runs()`, not in the harness

The harness's `parse_model_name()` splits on `#`. Real data from OpenRouter uses `:`. We add parsing logic inside `render.py`'s `aggregate_runs()` to handle both separators:

```
"anthropic/claude-opus-4.7:low"
       → provider="anthropic", base_model="claude-opus-4.7", level="low"

"openai/gpt-oss-120b:high"
       → provider="openai", base_model="gpt-oss-120b", level="high"
```

**Rationale**: The harness convention (`#`) is the canonical format. We don't change it because we don't touch harness code. The renderer handles whatever the actual runs produce. If the harness later emits `#`, the renderer handles both.

**Alternative considered**: Fix at collection time (re-run benchmarks with `#`). Rejected — no re-running benchmarks.

### Decision 2: Nested Astro routes: `[provider]/[model]/[level].astro`

Three-level path segments. Astro's file-based routing supports this natively:

```
pages/models/
├── index.astro                              ← grouped index
├── [provider]/[model]/index.astro           ← base model overview
└── [provider]/[model]/[level].astro         ← fixture gallery
```

`getStaticPaths()` in each page enumerates all combinations from `results.json`. No `~` encoding needed since `provider`, `model`, and `level` are all valid URL segment characters.

**Rationale**: URLs are human-readable and semantically structured. `:` in model names is the only potentially problematic character, but it's removed by splitting provider/model from level.

**Alternative considered**: Keep flat paths with better encoding. Rejected — nested structure expresses the data hierarchy naturally.

### Decision 3: `@icons-pack/react-simple-icons` for provider logos

Map provider slug → Simple Icons component via a lookup table:

```tsx
const PROVIDER_ICON_MAP: Record<string, React.ComponentType<IconProps>> = {
  anthropic: SiAnthropic,
  openai: SiOpenai,
  google: SiGoogle,
  meta: SiMeta,
  // ... extensible
};
```

Unknown providers fall back to a colored circle with the first letter.

**Rationale**: 3400+ brand icons, MIT licensed, 370K weekly downloads, peer-dep compatible with React 19. Tree-shakeable — only imported icons are bundled. Each icon has a built-in brand color via `color="default"`.

**Alternative considered**: Inline SVGs in the project. Rejected — maintenance burden as providers are added. CDN hotlinked images. Rejected — adds external network dependency, no dark mode support.

### Decision 4: Custom Recharts tick renderer for diagonal labels

Recharts' `XAxis` accepts a custom `tick` prop. We render a custom SVG group with:
1. Provider icon (16×16)
2. Truncated model name (max ~10 chars + ellipsis)
3. Level suffix on a third line
4. Group rotated -40° via SVG `transform`, anchored at end

Height is computed dynamically: `max(300, modelCount * 80)`.

**Rationale**: Recharts' built-in `angle` prop rotates text but doesn't support multi-line or icon-including tick labels. A custom renderer gives full control.

**Alternative considered**: Abbreviated labels without icons. Rejected — icons are more scannable than text abbreviations. Switching charting library. Rejected — unnecessary migration.

### Decision 5: Cost chart uses `total_cost_usd`, not `avg_cost_usd`

`aggregate_runs()` already computes both. The chart simply reads `total_cost_usd` from `model_summaries` instead of `avg_cost_usd`. Label changes from "Avg cost per fixture (USD)" to "Total cost per full run (USD)".

**Rationale**: "This model's full evaluation cost $0.53" is more honest and interpretable than "$0.0026 per fixture." Both are computed from the same data; the chart just picks a different pre-computed field.

## Risks / Trade-offs

- **[Risk] Old URLs break with no redirects** → Mitigation: Accepted. Project is early-stage, no published links dependent on old URL format.
- **[Risk] `@icons-pack/react-simple-icons` is ~25MB unpacked** → Mitigation: Tree-shaking means only the 5-10 icons we import end up in the bundle. The package is a dev/build dependency, not a runtime download.
- **[Risk] Custom tick renderer may clip with very long model names** → Mitigation: Truncate to ~10 chars + ellipsis. Adjust bottom margin based on longest label. If names are still too long, users can hover tooltips for the full name.
- **[Risk] `:` separator assumption may not hold for all providers** → Mitigation: The parsing logic tries `:` first, falls back to `#`, then treats the whole name as base with no level. Unknown providers still render (with fallback icon).
