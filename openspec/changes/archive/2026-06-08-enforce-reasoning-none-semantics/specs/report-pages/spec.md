## MODIFIED Requirements

### Requirement: Model Detail page displays reasoning token count
The Model Detail page SHALL display total reasoning tokens alongside input and provider-reported total output tokens when the model has a reasoning level. The label SHALL make clear that reasoning tokens are included within total output rather than additional to it. When the model does not have a reasoning level, reasoning tokens SHALL be omitted from the display.

#### Scenario: Reasoning tokens shown as included output
- **WHEN** a model detail page has 127 input tokens, 166 total output tokens, and 150 reasoning tokens
- **THEN** the stats line SHALL identify 166 as total output and 150 as reasoning included within that output

#### Scenario: No reasoning tokens for non-reasoning model
- **WHEN** navigating to a model detail page for `granite-4.1-8b` with no reasoning level
- **THEN** the stats line SHALL show input and output tokens with no reasoning mention

#### Scenario: Reasoning model with zero reasoning tokens
- **WHEN** navigating to a model detail page for a model with `reasoning_level: "high"` but all reasoning tokens are 0
- **THEN** the stats line SHALL identify 0 reasoning tokens within total output

### Requirement: ModelOutputCard displays reasoning tokens in compact badge
The `ModelOutputCard` component SHALL display provider-reported output and reasoning tokens in its inline token badge when the fixture result includes a reasoning level. The badge SHALL state that reasoning belongs to output and SHALL not use additive `(+Nr)` notation.

#### Scenario: Reasoning tokens in output card badge
- **WHEN** a fixture result has `input_tokens: 127`, `output_tokens: 166`, `reasoning_tokens: 150`, and `reasoning_level: "high"`
- **THEN** the token badge SHALL read `127 in → 166 out (150 reasoning)` or an equivalently explicit compact label

#### Scenario: No reasoning portion without reasoning level
- **WHEN** a fixture result has `input_tokens: 127`, `output_tokens: 16`, and `reasoning_level: null`
- **THEN** the token badge SHALL show 127 input and 16 output tokens without a reasoning portion

#### Scenario: Reasoning level set but reasoning tokens are unavailable
- **WHEN** a fixture result has `reasoning_level: "high"` but `reasoning_tokens: null`
- **THEN** the token badge SHALL identify reasoning as unavailable without implying an additive token count

### Requirement: FixtureCard displays reasoning tokens when present
The `FixtureCard` component SHALL display a third token column when the fixture result includes a reasoning level. The output column SHALL be labeled as total output and the reasoning column SHALL be presented as a subset of that output. Without a reasoning level, the card SHALL retain its existing two-column input/output layout.

#### Scenario: FixtureCard with reasoning data
- **WHEN** a fixture card renders with input 127, total output 166, and reasoning 150
- **THEN** the card SHALL show Input (127), Total output (166), and Reasoning within output (150)

#### Scenario: FixtureCard without reasoning level
- **WHEN** a fixture card renders with `reasoning_level: null`
- **THEN** the card SHALL show two columns: Input and Output

#### Scenario: FixtureCard with unavailable reasoning count
- **WHEN** a fixture card renders with a reasoning level but `reasoning_tokens: null`
- **THEN** the reasoning column SHALL show `N/A`
