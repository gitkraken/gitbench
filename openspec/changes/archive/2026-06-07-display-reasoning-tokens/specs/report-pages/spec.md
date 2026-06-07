## ADDED Requirements

### Requirement: Model Detail page displays reasoning token count

The Model Detail page SHALL display total reasoning tokens alongside input and output tokens when the model has a reasoning level. When the model does not have a reasoning level, reasoning tokens SHALL be omitted from the display.

#### Scenario: Reasoning tokens shown for reasoning model
- **WHEN** navigating to a model detail page for `o3-mini#high` with 1,500 total reasoning tokens across all fixtures
- **THEN** the stats line reads "127 in / 16 out / 1,500 reasoning tokens" or similar

#### Scenario: No reasoning tokens for non-reasoning model
- **WHEN** navigating to a model detail page for `granite-4.1-8b` with no reasoning level
- **THEN** the stats line reads "127 in / 16 out tokens" with no reasoning mention

#### Scenario: Reasoning model with zero reasoning tokens
- **WHEN** navigating to a model detail page for a model with `reasoning_level: "high"` but all reasoning_tokens are 0
- **THEN** the stats line reads "127 in / 16 out / 0 reasoning tokens"

### Requirement: ModelOutputCard displays reasoning tokens in compact badge

The `ModelOutputCard` component SHALL display reasoning tokens in its inline token badge when the fixture result includes a reasoning level. The format SHALL be `{input}→{output}(+{reasoning}r)` where the `(+{reasoning}r)` portion is only present when reasoning level is set.

#### Scenario: Reasoning tokens in output card badge
- **WHEN** a fixture result has `input_tokens: 127`, `output_tokens: 16`, `reasoning_tokens: 150`, and `reasoning_level: "high"`
- **THEN** the token badge reads "127→16(+150r)"

#### Scenario: No reasoning portion without reasoning level
- **WHEN** a fixture result has `input_tokens: 127`, `output_tokens: 16`, and `reasoning_level: null`
- **THEN** the token badge reads "127→16"

#### Scenario: Reasoning level set but reasoning_tokens is null
- **WHEN** a fixture result has `reasoning_level: "high"` but `reasoning_tokens: null`
- **THEN** the token badge reads "127→16(+N/A)"

### Requirement: FixtureCard displays reasoning tokens when present

The `FixtureCard` component SHALL display a third column for reasoning tokens when the fixture result includes a reasoning level. Without a reasoning level, the card SHALL retain its existing two-column (Input | Output) layout.

#### Scenario: FixtureCard with reasoning data
- **WHEN** a fixture card renders for a result with `input_tokens: 127`, `output_tokens: 16`, `reasoning_tokens: 150`, and `reasoning_level: "high"`
- **THEN** the card shows three columns: Input (127), Output (16), Reason (150)

#### Scenario: FixtureCard without reasoning level
- **WHEN** a fixture card renders for a result with `reasoning_level: null`
- **THEN** the card shows two columns: Input and Output only

#### Scenario: FixtureCard with reasoning level but null reasoning_tokens
- **WHEN** a fixture card renders with `reasoning_level: "high"` and `reasoning_tokens: null`
- **THEN** the Reason column shows "N/A"
