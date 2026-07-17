## Context

GitBench currently uses “model group” to mean one provider/base-model identity and all of its effort and output-mode variants. The shared `ModelSelector` presents those groups as a flat multi-select, while `useSyncedModelSelection` synchronizes concrete group IDs through the URL and browser events. Most chart endpoints can return scoped data, so deriving a performance preset independently from each response would cause membership to vary between otherwise synchronized selectors.

The report model records do not contain context-window or weight-access metadata. GitBench already queries OpenRouter for reasoning support, and OpenRouter's model catalog also exposes context length and a Hugging Face identifier, but the current capability cache discards those fields. Upstream identifiers may be renamed or retired, and a Hugging Face identifier is evidence of published weights rather than a complete license classification.

## Goals / Non-Goals

**Goals:**

- Give every in-scope chart selector the same useful, named model presets.
- Make a campaign-aware Top Performers preset the consistent default without overriding shared URLs.
- Produce deterministic, reviewable metadata for context-window and weight-access classification.
- Keep preset membership consistent across global, benchmark-scoped, and fixture-scoped chart responses.
- Improve selector information density while giving every trigger and every dropdown consistent responsive dimensions.

**Non-Goals:**

- Redesigning or changing the selection semantics of the Compare page.
- Treating “open weights” as equivalent to “open source” or asserting a model's license from a Hugging Face identifier alone.
- Fetching OpenRouter metadata in the browser, at request time, or as an implicit production-build dependency.
- Adding user-created or persisted custom presets.

## Decisions

### Generate a committed normalized catalog

Add a web-owned synchronization command that reads OpenRouter's public model catalog and writes a committed normalized metadata snapshot keyed by canonical `provider/baseModel` group ID. Each record carries `contextWindowTokens`, `weightAccess` (`open`, `closed`, or `unknown`), optional upstream/Hugging Face identifiers, provenance, and `fetchedAt`.

A separate hand-authored overrides file provides aliases for renamed identifiers and authoritative corrections for weight access or context length. Overrides win over fetched values. The generator reports current report models that remain unmatched or unknown, validates unique canonical IDs and valid field values, and produces stable key ordering. A metadata refresh is an explicit maintenance action; ordinary builds consume the committed snapshot without network access.

This is preferred over extending the runner's reasoning-capability cache because that cache is user-local and serves pre-run validation, whereas this catalog is a deployable, reviewable web artifact. It is also preferred over runtime fetching because reproducible builds and graceful handling of retired models are more valuable than immediate upstream freshness.

### Resolve presets centrally from the overall campaign summary

Introduce a serializable preset contract containing an ID, label, description, and ordered concrete base-model group IDs. Server-side chart/summary composition resolves this contract using the full overall summary for the active campaign before chart-specific scoping. Scoped responses retain the same preset definitions; the selector intersects membership with groups actually available in its response.

This prevents “Top Performers” from changing meaning between a global chart and a benchmark chart. It also allows all selectors on a page to agree even though their metric payloads differ.

### Use existing grouped-chart median semantics for ranking

Top Performers ranks base-model groups using overall pass rate for the active campaign. For each output mode, calculate the median of the distinct measurable pass rates across effort variants, matching grouped pass-rate chart behavior. When both text and JSON-schema modes are measurable, average their two median representatives. Sort descending, break equal scores by canonical `provider/baseModel`, and take exactly 20 (or all measurable groups when fewer than 20 exist).

This is preferred over the existing Compare-specific mean because it aligns the preset with the representative values users see in primary charts and avoids coupling the change to Compare.

### Define metadata presets with explicit inclusion rules

- **Frontier Models:** `weightAccess == closed` and provider is exactly `openai`, `anthropic`, or `google`.
- **Open Weights:** `weightAccess == open`.
- **Context: Up to 200K:** known context window less than or equal to 200,000 tokens.
- **Context: 200K–499K:** known context window greater than 200,000 and less than 500,000 tokens.
- **Context: 500K–999K:** known context window at least 500,000 and less than 1,000,000 tokens.
- **Context: 1M+:** known context window at least 1,000,000 tokens.

Unknown weight access is excluded from both Frontier and Open Weights. Unknown context length is excluded from all context presets. Metadata presets use a deterministic canonical-ID order.

### Apply presets as concrete selection replacements

Activating a preset replaces the current model selection with the preset's available concrete group IDs. The selector marks a preset active only when its available membership exactly matches the current selection. Subsequent individual edits produce a custom selection and clear that active indication.

URL state continues to encode concrete group IDs rather than preset IDs. Any explicit URL model-selection state, including an explicit empty selection, wins over the Top Performers default. In the absence of explicit URL model state, in-scope charts initialize to Top Performers.

Concrete IDs make shared links stable when metadata or performance later changes; a preset query parameter would make an old link silently change meaning.

### Keep model-specific behavior above the generic multi-select

The shared model selector owns preset definitions, model metadata display, and model-specific labels. The generic multi-select gains only reusable presentation extension points needed for header content and separate trigger/panel sizing; it does not learn model semantics.

Use shared responsive size tokens/classes for all in-scope instances: a uniform trigger width on non-mobile layouts and a uniform dropdown width that is wider than the trigger. Clamp both to the available viewport on narrow screens. The dropdown presents search, preset actions with membership counts, select-all/clear actions, and model rows with provider identity plus compact context/weight metadata.

## Risks / Trade-offs

- **[Upstream metadata is incomplete or renamed]** → Preserve a tri-state `unknown`, support reviewed aliases/overrides, and report unresolved current models during synchronization.
- **[Weight access can be confused with licensing]** → Name the classification “Open Weights,” avoid license claims, and require explicit `open` classification rather than inferring solely from a Hugging Face ID.
- **[Top 20 can change between campaigns or refreshes]** → Compute from the selected campaign intentionally, encode concrete IDs in URLs, and use deterministic tie-breaking.
- **[Scoped charts lack some preset members]** → Intersect with available groups at selection time while keeping centrally resolved membership and ordering intact.
- **[Twenty models may still produce dense charts]** → Treat Top 20 as a discoverable default that users can narrow via presets or individual selection; do not silently lower the agreed count per chart.
- **[A wider panel can overflow small screens]** → Clamp panel dimensions to viewport-safe values and verify keyboard and mobile interaction.
- **[Shared component styling may appear on Compare]** → Permit incidental presentation inheritance, but add no Compare-specific acceptance criteria or ranking/default changes.

## Migration Plan

1. Add the override input, synchronization command, generated catalog, and validation tests; generate an initial reviewed snapshot.
2. Add catalog loading and centralized preset resolution to full-summary and chart response composition without changing selection defaults.
3. Add the serializable preset fields to frontend types and make selectors consume them across in-scope chart surfaces.
4. Add preset controls and responsive shared dimensions to the selector, then switch no-URL initialization to Top Performers.
5. Verify legacy and current explicit URL selections continue to resolve identically.

Rollback can remove preset fields and restore the existing all-model default while leaving the generated metadata files unused. No persistent user data or destructive database migration is required.

## Open Questions

None. The preset definitions, ranking count and metric, URL precedence, context bands, and Compare exclusion were resolved during exploration.
