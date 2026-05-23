## ADDED Requirements

### Requirement: CSS tooltip class is defined in global styles
The global stylesheet (`global.css`) SHALL define a `.has-tooltip` utility class that renders a styled hover card via the `::after` pseudo-element using the `data-tooltip` attribute as content. The tooltip card SHALL use `var(--color-card)` background, `var(--color-border-accent)` border, `var(--color-text-mid)` text color, `var(--font-mono)` font family, and the existing dark theme border-radius and padding conventions. The tooltip SHALL have a maximum width of 280px, support multi-line text via `white-space: pre-wrap`, and transition opacity smoothly over 150ms. The tooltip SHALL be positioned above the trigger element with a 10px gap offset.

#### Scenario: Tooltip appears on hover
- **WHEN** a user hovers over an element with class `has-tooltip` and a `data-tooltip` attribute
- **THEN** a styled card appears above the element showing the `data-tooltip` text content

#### Scenario: Tooltip supports multi-line text
- **WHEN** `data-tooltip` contains text with newline characters or exceeds 280px worth of text
- **THEN** the tooltip wraps to multiple lines and respects the max-width constraint

#### Scenario: Tooltip fades in smoothly
- **WHEN** a user hovers over a `.has-tooltip` element
- **THEN** the tooltip appears with a 150ms opacity transition from 0 to 1

#### Scenario: Tooltip is styled consistently with the app theme
- **WHEN** a tooltip is displayed
- **THEN** its visual appearance (colors, fonts, borders, radius) matches the existing `.card` component style

### Requirement: Tooltip trigger includes icon indicator
Every element that triggers a tooltip SHALL display a small information icon after its text. The icon SHALL be rendered via CSS (pseudo-element or inline SVG) and SHALL use a muted color that changes to accent color on hover of the parent element. The icon SHALL be subtle (small size, low opacity when not hovered) to avoid visual clutter.

#### Scenario: Icon is visible on tooltip triggers
- **WHEN** a `<span class="has-tooltip" data-tooltip="...">` element renders
- **THEN** a small ⓘ icon appears after the span text

#### Scenario: Icon highlights on hover
- **WHEN** a user hovers over a `.has-tooltip` element
- **THEN** the icon color intensifies (from muted to accent) along with the tooltip appearing

### Requirement: Every tooltip trigger has a title attribute fallback
Every element using `.has-tooltip` with a `data-tooltip` attribute SHALL also include a `title` attribute with equivalent descriptive text. The `title` text MAY be shorter than `data-tooltip` but SHALL convey the same essential information.

#### Scenario: title attribute is present
- **WHEN** a `.has-tooltip` element is inspected in the DOM
- **THEN** it has a non-empty `title` attribute with descriptive text

#### Scenario: title acts as fallback on touch devices
- **WHEN** a user long-presses a `.has-tooltip` element on a touch device
- **THEN** the browser displays the native tooltip from the `title` attribute

### Requirement: Tooltip CSS is loaded on every page
The `Layout.astro` component SHALL ensure the tooltip CSS is available on every page. The `.has-tooltip` class SHALL be defined in `global.css` which is already imported by `Layout.astro`.

#### Scenario: Tooltip class is available site-wide
- **WHEN** navigating to any page in the site
- **THEN** the `.has-tooltip` CSS class is defined and functional
