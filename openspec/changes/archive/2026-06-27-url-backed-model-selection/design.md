## Context

Report chart state currently has two persistence paths:

- model group selection uses `gitbench-model-selection` in `localStorage` plus a `model-selection-changed` custom event;
- output mode uses `gitbench-output-mode` in `localStorage` plus an `output-mode-changed` custom event.

That makes same-page chart islands sync, but it also means a bare report URL can render a private, stale selection from a prior visit. Compare has a separate one-off `?with=` deep link, but selection changes after load do not remain shareable. As the benchmark grows, explicit repeated model query params can also become too long, so the URL state needs a compact browser-decodable representation.

## Goals / Non-Goals

**Goals:**

- Make model group selection and output mode shareable through URL state.
- Default bare report URLs to current data instead of old browser storage: all groups for overview/benchmark views, top two groups for Compare, and `both` output mode where both modes are available.
- Keep URL state compact enough for large future model sets by supporting include/exclude/all semantics and compressed state.
- Decode and encode compressed state entirely in the browser with `fflate`.
- Preserve same-page synchronization across independently hydrated React islands.
- Keep old `/compare?with=` links working.

**Non-Goals:**

- No server-side short-link service or persistent hash lookup table.
- No user account, saved view, or cross-device preference storage.
- No campaign selector redesign.
- No changes to benchmark result data shapes beyond the view-state URL behavior.

## Decisions

### Decision 1: Introduce a focused URL-state codec module

Add a web utility module, tentatively `src/lib/report-url-state.ts`, that owns all parsing and serialization of report view state. Components should not know about compression details.

The codec exposes functions along these lines:

- `decodeReportViewState(searchParams, groups, options)`
- `encodeReportViewState(state, groups, options)`
- `resolveReportViewState(decoded, groups, pageDefault)`
- `writeReportViewStateToHistory(state)`

The resolved state is expressed in component-friendly values:

- `selectedGroups: string[]`
- `outputMode: "text" | "json_schema" | "both"`
- `source: "url" | "default" | "legacy"`

Rationale: the current behavior is split across `ModelSelector`, `useSyncedModelSelection`, `model-groups`, and Compare. Centralizing URL state avoids drifting encoders and makes invalid-state fallback testable.

Alternatives considered:

- Put encoding in `useSyncedModelSelection`. Rejected because Compare and model drill-down output-mode controls also need the same semantics.
- Keep model state and output mode in separate query systems. Rejected because shared links should preserve one coherent view.

### Decision 2: Use `fflate` for browser-side compression

Add `fflate` to the web package and use its synchronous deflate/inflate APIs for compressed URL state. The transport format is:

```text
?s=gb1.<base64url(deflate(utf8(compact-json)))>
```

The `gb1` prefix identifies the codec version family and allows future codecs without guessing. Base64url is only the transport for compressed bytes; raw JSON MUST NOT be base64-encoded as a compression step.

Rationale: `fflate` works in the browser without a server dependency and avoids the async stream initialization required by native `CompressionStream`/`DecompressionStream`. Sync decode lets React initialize selection state from the URL before rendering charts.

Alternatives considered:

- Native `CompressionStream`. Rejected for v1 because it is asynchronous and would make initial state resolution more awkward.
- Hash IDs. Rejected because a hash needs a lookup table and would not make links self-contained.
- Raw repeated query params only. Rejected because model counts may grow enough to create long URLs.

### Decision 3: Encode include, exclude, or all before compression

The logical payload is versioned and compact:

```json
{"v":1,"k":"i","g":["openai/gpt-5","anthropic/claude"]}
{"v":1,"k":"x","g":["old-model-a"]}
{"v":1,"k":"a"}
```

The keys mean:

- `v`: payload version
- `k`: selection kind, `i` include, `x` exclude, `a` all
- `g`: provider/base-model group IDs
- `o`: optional output mode, `t` text, `j` json_schema, `b` both

The encoder chooses the smallest semantic selection before compression:

- all selected: `k=a`
- selected count <= total / 2: `k=i`
- selected count > total / 2: `k=x`

The output mode key is omitted when the mode is the default `both`.

Rationale: include/exclude/all reduces both readable URL size and compressed payload size. It also keeps links stable as new models are added: an exclude link naturally includes future models, while an include link intentionally pins a specific subset.

### Decision 4: Support readable params but canonicalize to the shortest safe URL

The decoder accepts:

- compressed state: `s=gb1.<payload>`
- readable include: `m=<group>,<group>` or repeated `model=<group>`
- readable exclude: `x=<group>,<group>` or repeated `exclude=<group>`
- all: `models=all`
- mode: `mode=text|json_schema|both`
- legacy Compare seed: `with=<model-or-group>`

The encoder compares readable and compressed candidates and writes the shortest safe representation. If a readable URL exceeds a conservative threshold, such as 1800 characters for path plus search, it MUST write compressed state even if the compressed version is only slightly shorter.

Rationale: short URLs remain inspectable during development and debugging, while large states stay safe for sharing.

### Decision 5: URL state replaces storage as source of truth

Report/chart pages stop reading `gitbench-model-selection` and `gitbench-output-mode` as initial state. A missing URL state means page defaults:

- overview and benchmark detail: all available model groups;
- Compare: top two model groups by mean pass rate;
- model level drill-down output-mode toggle: `both` when both text and JSON variants exist, otherwise the available mode.

Same-page custom events remain, but they carry resolved view state after the URL is updated. React islands listen to the event and to `popstate`.

Rationale: URL state should be shareable and visible. Storage is the cause of stale bare URLs.

### Decision 6: Preserve state only across analytical drilldowns

Top-level navigation links remain bare and therefore reset to page defaults. Analytical links preserve state when the destination has the same comparative context:

- overview heatmap row/cell links to benchmark detail preserve model/mode state;
- benchmark fixture-comparison links may preserve mode if the destination has mode-aware evidence;
- model detail Compare button uses the new state format while still accepting old `?with=`;
- generic sidebar links, model directory links, methodology links, and Explore links do not carry model selection.

Rationale: preserving state everywhere makes navigation feel haunted. Preserving it only where the user is drilling into the same comparison keeps links useful without surprising resets.

## Risks / Trade-offs

- **[Risk] Compressed URLs are opaque.** -> Keep readable decoding support, choose readable encoding for short states, and add codec unit tests with fixture payloads.
- **[Risk] New model groups change decoded selections.** -> Use group IDs, sanitize all decoded IDs against current data, and treat include/exclude semantics explicitly.
- **[Risk] Invalid compressed payloads could break first render.** -> Decode in a try/catch boundary and fall back to page defaults, optionally replacing the bad state in the URL.
- **[Risk] Compare defaults change for returning users.** -> This is intentional; bare `/compare` should show current top-two groups and `both` mode rather than private stale state.
- **[Risk] Removing localStorage may surprise users who expected sticky selections.** -> The shareable URL becomes the persistence mechanism; users can bookmark narrowed views.
- **[Risk] URL updates from multiple islands could loop.** -> Compare canonical encoded state before writing history and before dispatching events.

## Migration Plan

1. Add `fflate` and the URL-state codec with unit tests before changing components.
2. Update `useSyncedModelSelection` to initialize from resolved URL state, write URL state on changes, and dispatch same-page events.
3. Update `ModelSelector` to stop reading/writing model selection localStorage on report pages.
4. Update output-mode controls to use URL state and default to `both`.
5. Update Compare initialization to accept `?with=` and normalize to the new state format after a valid decode.
6. Update analytical links to preserve state selectively.
7. Leave old localStorage keys untouched but unused; rollback can temporarily restore old readers if needed.

## Open Questions

- What exact URL length threshold should trigger compressed state? The design assumes a conservative threshold around 1800 characters.
- Should invalid URL state be silently replaced with a clean default URL, or should it fall back without mutating the address bar? The implementation can start with fallback without mutation to avoid surprising history changes.
