## ADDED Requirements

### Requirement: Methodology page supports tooltip triggers
The Methodology page SHALL use the `.has-tooltip` class on key technical terms and section headers that benefit from contextual explanation. Tooltips SHALL provide quick definitions for terms like "SequenceMatcher", "pass@k", "OpenRouter", and "Ollama" without requiring the reader to search elsewhere. The tooltip content SHALL be concise (1-2 sentences per term).

#### Scenario: Technical terms have tooltips
- **WHEN** viewing the Methodology page
- **THEN** key technical terms (e.g., "SequenceMatcher", "OpenRouter", "benchmark suite") have `.has-tooltip` spans with explanatory text

#### Scenario: Tooltips supplement but do not replace existing prose
- **WHEN** reading the Methodology page
- **THEN** the existing detailed explanations remain intact, with tooltips providing quick-reference definitions on hover
