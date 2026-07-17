## 1. Model Catalog Metadata

- [x] 1.1 Define the normalized catalog and override-file schemas, TypeScript types, and validation fixtures for context window, tri-state weight access, provenance, aliases, and refresh timestamps.
- [x] 1.2 Implement the explicit OpenRouter synchronization script with exact-ID matching, reviewed alias/override precedence, deterministic ordering, diagnostics, and atomic replacement of valid output.
- [x] 1.3 Add the web package command, a reviewed initial overrides file, and a generated catalog covering every current report base-model group with explicit unknowns where necessary.
- [x] 1.4 Add automated tests for exact matches, renamed models, ambiguous weight access, invalid overrides, unresolved-model diagnostics, deterministic output, and offline ordinary builds.

## 2. Central Preset Resolution

- [x] 2.1 Add serializable model-metadata and model-preset contracts to chart/summary response types and implement catalog loading keyed by canonical group ID.
- [x] 2.2 Implement and unit-test the Top Performers resolver using active-campaign overall results, per-output-mode distinct-effort medians, cross-mode averaging, deterministic tie-breaking, and an exact 20-model limit.
- [x] 2.3 Implement and unit-test Frontier Models, Open Weights, and the four mutually exclusive context-window resolvers, including unknown-value exclusion and boundary cases.
- [x] 2.4 Compose metadata and centrally resolved presets into summary and chart responses before scoping, then ensure scoped selectors intersect membership only with available groups.
- [x] 2.5 Extend API and chart-data tests to prove preset definitions remain identical across global, benchmark, and fixture scopes for the same active campaign.

## 3. Shared Selector Behavior

- [x] 3.1 Add generic multi-select extension points for custom header content and independent responsive trigger/panel sizing without introducing model-specific behavior into the generic component.
- [x] 3.2 Add preset controls, available-member counts, exact-active-preset detection, replacement selection behavior, and compact context/weight metadata to the shared model selector.
- [x] 3.3 Update selection initialization so Top Performers is the default on in-scope charts only when no explicit URL model state exists, preserving explicit concrete and empty selections.
- [x] 3.4 Audit and wire every overview, benchmark, model-detail, and fixture chart selector to the shared presets and dimensions while leaving Compare-specific defaults and behavior out of scope.
- [x] 3.5 Add component and URL-state tests for preset application, post-preset customization, concrete-ID encoding, URL precedence, explicit empty selection, search, and select-all/clear behavior.

## 4. Responsive Presentation and Verification

- [x] 4.1 Apply shared responsive trigger and wider dropdown dimensions, including viewport clamping, alignment, scrolling, and long-label handling across in-scope chart layouts.
- [x] 4.2 Verify preset and model-row controls remain keyboard accessible, expose meaningful active/selected state, and remain usable at narrow viewport widths.
- [x] 4.3 Run the web API/unit test suite, Astro type checking and production build, and the metadata synchronization validation against the committed catalog.
- [x] 4.4 Manually smoke-test all in-scope selector surfaces at desktop and mobile widths, including an explicit shared URL and a non-default campaign; record any incidental Compare presentation separately rather than expanding this change.
