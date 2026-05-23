## ADDED Requirements

### Requirement: Models index page uses compact chip layout
The Models index page (`/models`) SHALL render reasoning level variants as compact chips without nested card wrappers. Each provider section SHALL display a provider header, then a list of base models with their level chips in a CSS grid.

#### Scenario: No outer card per base model
- **WHEN** the Models index page is rendered
- **THEN** base model groups are NOT wrapped in a `<div class="card">` element
- **AND** the model name appears as a heading within the provider section

#### Scenario: Level chips use compact styling
- **WHEN** a reasoning level variant is rendered as a clickable chip
- **THEN** the chip uses flat background styling (no gradient, no box shadow)
- **AND** the chip has a thin border and tight padding
- **AND** hovering changes the border color to the accent color

#### Scenario: Pass rate badge is displayed on each chip
- **WHEN** a level chip is rendered
- **THEN** the pass rate is displayed as a color-coded badge (pass/warn/fail)
- **AND** the badge uses the same color scheme as the current implementation

### Requirement: No info-circle tooltips on the Models index page
The Models index page SHALL NOT use the `has-tooltip` CSS class on any element. Accessibility information SHALL be provided via standard `title` attributes where appropriate.

#### Scenario: No "i" circles visible
- **WHEN** the Models index page is rendered
- **THEN** no elements have the `has-tooltip` class
- **AND** no info-circle pseudo-elements are visible on level names or pass-rate badges

#### Scenario: Title attributes remain for accessibility
- **WHEN** hovering over a level name or pass-rate badge
- **THEN** the browser displays a native tooltip via the `title` attribute (where applicable)

### Requirement: Cost data is not displayed on the Models index page
The Models index page SHALL NOT display cost information on level chips.

#### Scenario: No cost on level chips
- **WHEN** a level chip is rendered on the Models index page
- **THEN** the chip does NOT contain a dollar-amount cost line

### Requirement: Provider sections maintain visual grouping
Consecutive base models from the same provider SHALL appear within the same provider section without repeating the provider name.

#### Scenario: Provider name shown once per section
- **WHEN** a provider has multiple base models
- **THEN** the provider icon and name appear once at the top of the section
- **AND** all base models for that provider are listed within that section

#### Scenario: Provider sections are visually separated
- **WHEN** navigating between provider sections
- **THEN** clear visual separation exists between sections (via margin or spacing)
