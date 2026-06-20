## MODIFIED Requirements

### Requirement: Fixture Detail page shows full prompt, expected, and all model outputs
The Fixture Detail page (`fixtures/[fixture].astro`) SHALL render the fixture metadata (id, description, purpose, difficulty, tags), the full prompt text in a monospace block, the full expected text in a monospace block, and all model outputs as static `ModelOutputCard` components showing model name, pass/fail badge, similarity score, and full output text. Each block SHALL include a copy-to-clipboard button. For JSON-schema mode outputs with structured-output parse or schema errors, the output card SHALL display a clear structured-output failure message that includes the raw model output.

#### Scenario: Full prompt is displayed in monospace
- **WHEN** navigating to `/fixtures/f001`
- **THEN** the complete prompt text is displayed in a monospace block with a copy button

#### Scenario: All model outputs are displayed
- **WHEN** navigating to `/fixtures/f001`
- **THEN** a card is rendered for each model that ran this fixture, showing the model name, similarity, pass/fail, and full output

#### Scenario: Copy button copies text to clipboard
- **WHEN** a user clicks the copy button on the prompt block
- **THEN** the full prompt text is copied to the system clipboard

#### Scenario: Invalid structured JSON message is displayed
- **WHEN** a JSON-schema mode fixture result has a structured-output parse error and raw structured output
- **THEN** the model output card displays `Invalid JSON. Output: <raw structured output>`
- **AND** the page remains renderable because the report artifact is valid JSON

#### Scenario: Invalid structured schema message is displayed
- **WHEN** a JSON-schema mode fixture result has a structured-output schema error and raw structured output
- **THEN** the model output card displays `Invalid structured output. Output: <raw structured output>`
- **AND** the raw structured output is available through the output card copy behavior
