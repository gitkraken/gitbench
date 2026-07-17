## Why

GitBench charts expose a growing catalog of base models through a flat selector, making useful comparisons difficult to discover and producing an overwhelming default view. The frontend also lacks stable metadata about model weight access and context-window size, so it cannot offer meaningful, consistently defined model collections.

## What Changes

- Add reusable model-selection presets to the shared chart model selector: Top Performers, Frontier Models, Open Weights, and four context-window bands.
- Define Top Performers as the top 20 base models ranked by median overall pass rate for the active campaign, using a deterministic tie-break, and make it the default selection when the URL does not specify models.
- Define Frontier Models as closed-weight models from OpenAI, Anthropic, or Google; models with unknown weight access are not included.
- Add a normalized, generated model-metadata catalog containing context-window size, weight-access classification, source provenance, and refresh time, with explicit aliases and manual overrides for missing or ambiguous upstream data.
- Enhance the shared selector dropdown with preset controls, model metadata, consistent trigger widths, and a wider consistent dropdown width across chart instances.
- Preserve explicit URL model selections over the Top Performers default and encode applied presets as their concrete selected model IDs.
- Exclude Compare-page-specific behavior and ranking logic from this change; shared visual improvements may be inherited without additional Compare requirements.

## Capabilities

### New Capabilities

- `model-catalog-metadata`: Generate, validate, and expose normalized model metadata used to classify base models by weight access and context window.
- `chart-model-presets`: Define, display, apply, and default shared chart model-selection presets with consistent selector presentation.

### Modified Capabilities

None.

## Impact

- Affects the report/data contract and chart API data needed to resolve campaign-aware preset membership consistently across global and scoped charts.
- Affects the shared React model selector, generic multi-select presentation hooks, chart selection state, and URL-state initialization.
- Adds a metadata synchronization script and a committed generated catalog plus curated aliases/overrides.
- Requires unit and API coverage for metadata normalization, preset membership/ranking, default resolution, URL precedence, and shared selector behavior.
- Does not add a runtime dependency on OpenRouter and does not require Compare-page-specific changes.
