## MODIFIED Requirements

### Requirement: Models are selectable by checkbox
Each model entry in the list SHALL display a checkbox indicating selection state. Clicking an entry SHALL toggle its selection. A provider brand icon (via `ProviderIcon` component, size 14) SHALL appear between the checkbox and the model name. The model pass rate (from `model_summaries`) SHALL be displayed next to each entry as contextual information.

#### Scenario: Toggle a model on
- **WHEN** user clicks an unselected model entry
- **THEN** its checkbox fills and the model is added to the selected set

#### Scenario: Toggle a model off
- **WHEN** user clicks a currently-selected model entry
- **THEN** its checkbox clears and the model is removed from the selected set

#### Scenario: Provider icon shown per entry
- **WHEN** the model list is displayed
- **THEN** each entry shows a provider brand icon (e.g., Anthropic logo for anthropic models, OpenAI logo for openai models) next to the model name

#### Scenario: Pass rate shown per entry
- **WHEN** the model list is displayed
- **THEN** each entry shows the model's overall pass rate (e.g., "92.5%") next to the name
