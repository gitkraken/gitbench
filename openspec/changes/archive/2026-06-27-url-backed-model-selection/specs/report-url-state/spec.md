## ADDED Requirements

### Requirement: Report view state is URL encoded
Report chart view state SHALL be representable in the page URL without requiring server-side lookup, localStorage, or user account state. The encoded state SHALL include model group selection semantics and output mode when they differ from page defaults.

#### Scenario: Bare URL uses page default
- **WHEN** a report page URL contains no model or output-mode state
- **THEN** the page resolves model selection and output mode from that page's current-data default

#### Scenario: URL reproduces narrowed view
- **WHEN** a user opens a copied URL containing valid report view state
- **THEN** the page initializes with the encoded model selection and output mode

### Requirement: URL state supports include, exclude, and all selections
The report URL state codec SHALL represent model group selection using one of three selection kinds: include only listed groups, exclude listed groups from all current groups, or select all current groups. Decoding SHALL sanitize all listed values against the current provider/base-model groups.

#### Scenario: Include selection resolves listed groups
- **WHEN** URL state encodes include selection for `["openai/gpt-5", "anthropic/claude-sonnet"]`
- **THEN** the resolved selected groups are exactly those known groups in encoded order

#### Scenario: Exclude selection includes future groups
- **WHEN** URL state encodes exclude selection for `["old-provider/old-model"]`
- **THEN** the resolved selected groups are all current known groups except `old-provider/old-model`

#### Scenario: All selection follows current data
- **WHEN** URL state encodes all selection
- **THEN** the resolved selected groups are every current known provider/base-model group

#### Scenario: Unknown group IDs are ignored
- **WHEN** URL state includes group IDs that are not known in the current report data
- **THEN** those group IDs are ignored during resolution

### Requirement: Output mode is part of URL state
The report URL state codec SHALL encode output mode as part of the same view state as model selection. Missing output mode SHALL resolve to `both` when both text and JSON-schema modes are available.

#### Scenario: Missing mode defaults to both
- **WHEN** URL state contains model selection but no output-mode value
- **AND** the current report data has both text and JSON-schema output modes
- **THEN** the resolved output mode is `both`

#### Scenario: Text mode is restored
- **WHEN** URL state encodes output mode `text`
- **THEN** the resolved output mode is `text`

#### Scenario: Unavailable mode falls back
- **WHEN** URL state encodes output mode `json_schema`
- **AND** the current report data only contains text-mode results
- **THEN** the resolved output mode is `text`

### Requirement: URL state supports compressed browser decoding
The report URL state codec SHALL support compressed state using `fflate` deflate/inflate in the browser. Compressed state SHALL use a versioned prefix and base64url transport for the compressed bytes.

#### Scenario: Compressed state round trips
- **WHEN** view state is encoded as `s=gb1.<payload>`
- **THEN** browser-side decoding inflates the payload and resolves the original view state

#### Scenario: Raw JSON is not base64 encoded as compression
- **WHEN** compressed state is written
- **THEN** the base64url payload represents compressed bytes, not raw JSON bytes

#### Scenario: Unsupported codec version falls back
- **WHEN** URL state uses an unsupported compressed-state prefix
- **THEN** the page ignores that state and resolves the page default

#### Scenario: Corrupt compressed payload falls back
- **WHEN** URL state contains an invalid compressed payload
- **THEN** the page ignores that state and resolves the page default without throwing

### Requirement: Encoder chooses compact URL representation
The report URL state encoder SHALL choose a compact representation by minimizing the semantic selection before serialization and by choosing compressed state when it is shorter or when the readable URL exceeds the configured length threshold.

#### Scenario: Include selected for small subset
- **WHEN** 2 of 100 model groups are selected
- **THEN** the encoder represents the selection as include semantics

#### Scenario: Exclude selected for mostly-all subset
- **WHEN** 98 of 100 model groups are selected
- **THEN** the encoder represents the selection as exclude semantics for the 2 unselected groups

#### Scenario: All selected omits group list
- **WHEN** every model group is selected
- **THEN** the encoder represents all selection without listing every group

#### Scenario: Compression used for long URLs
- **WHEN** the readable URL state would exceed the configured length threshold
- **THEN** the encoder writes compressed state with the `gb1` prefix
