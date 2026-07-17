## Context

Token usage appears at several levels of the report, but the overview and benchmark token-chart blurbs currently describe only the categories shown. GitBench stores provider-returned usage fields and builds chart aggregates from them; selected presentation paths can derive a missing total from available input and output counts. The existing Methodology page explains per-trial versus total-run normalization but not the provenance or comparability limits of the underlying counts.

The disclosure needs to be visible at the point where readers compare models, while the complete explanation should have one durable home. Existing `info-tip` blurbs and Methodology links provide the established presentation pattern.

## Goals / Non-Goals

**Goals:**

- Make provider telemetry provenance visible beside overview and benchmark token charts.
- Explain the distinction between provider-reported source counts and GitBench-derived aggregates precisely.
- Warn readers that token accounting is not normalized across providers.
- Provide a stable Methodology anchor for direct links and future references.

**Non-Goals:**

- Changing model adapters, token storage, aggregation, decomposition, or chart rendering.
- Independently retokenizing model requests or responses.
- Adding repeated disclaimers to fixture cards, model headers, or chart tooltips.
- Defining universal semantics for provider-specific token categories.

## Decisions

### Use a two-layer disclosure

The overview and benchmark pages will carry concise caveat text and a `Learn more →` link. The Methodology page will contain the full explanation under an element with `id="token-accounting"`.

This keeps the essential warning visible where comparisons happen without crowding dense fixture cards and tooltips. A Methodology-only disclaimer was considered but rejected because readers should not have to discover a separate page before learning that the values are provider-dependent. Repeating the full disclaimer at every token display was rejected because it would create visual noise and multiple copies that could drift.

### Describe source counts separately from displayed values

Copy will say that source token counts come from provider-reported usage telemetry and that GitBench calculates aggregates from those values. It will not say that all displayed values are returned verbatim by providers, because totals can be aggregated and a missing total can be derived from available input and output counts.

### Treat differences as an interpretation caveat, not invalid data

The copy will state that provider tokenizers and accounting conventions may differ and that comparisons are not independently normalized. It will not characterize provider data as inaccurate or merely estimated; the limitation is provenance and comparability.

### Use a stable semantic anchor

The detailed section will use `id="token-accounting"`, and both token-chart blurbs will link to `/methodology#token-accounting`. This follows the existing Methodology deep-link pattern and provides a reusable target for future token-related explanations.

## Risks / Trade-offs

- [The concise blurb becomes too long] → Keep it to two short sentences plus the established Learn more link.
- [Copy implies GitBench never derives values] → Explicitly distinguish source counts from aggregates and fallback totals in the Methodology section.
- [Provider terminology changes over time] → Use provider-neutral language and examples of category differences rather than claims about a specific API.
- [The disclaimer is overlooked on lower-level token displays] → Place it on both primary comparison surfaces and use the stable Methodology anchor; avoid duplicating it in every compact component unless future usability evidence supports that expansion.

## Migration Plan

This is a static-content change with no data migration. Deploy the page-copy and anchor updates together. Rollback consists of reverting those content changes and does not affect stored reports or APIs.

## Open Questions

None. The wording may be polished during implementation as long as it preserves the normative distinctions in the specifications.
