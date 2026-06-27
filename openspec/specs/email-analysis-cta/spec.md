# email-analysis-cta Specification

## Purpose
Define the Overview page email CTA for requesting the GitBench analysis PDF while preserving the existing email capture flow and responsive dashboard layout.

## Requirements
### Requirement: Overview page shows analysis PDF CTA
The Overview page SHALL show an email CTA that invites users to request the GitBench analysis PDF. The CTA SHALL appear after the introductory About section and before the main chart sections.

#### Scenario: CTA appears in Overview flow
- **WHEN** a user opens the Overview page
- **THEN** the page shows a CTA for getting the GitBench analysis PDF by email after the About content
- **AND** the CTA appears before the Model Summary chart section

### Requirement: CTA uses prominent brand treatment
The CTA SHALL use a dedicated visual treatment that is more prominent than a standard report card. The treatment SHALL use the existing GitBench dark surface aesthetic with purple and teal brand colors for its background, border, glow, or icon accents.

#### Scenario: CTA differs from ordinary cards
- **WHEN** the CTA renders next to ordinary report cards
- **THEN** its background and border treatment are visually distinct from the default `.card` treatment
- **AND** the CTA still uses the existing GitBench color palette

#### Scenario: CTA keeps report layout density
- **WHEN** the CTA renders on the Overview page
- **THEN** it remains a compact dashboard callout
- **AND** it does not become a full landing-page hero section

### Requirement: CTA includes decorative background mail icon
The CTA SHALL include a large decorative mail icon in the card background. The icon SHALL use a brighter brand accent than the base card surface, MAY be partially clipped by the CTA edges, and MUST NOT reduce foreground text or button readability.

#### Scenario: Background mail icon renders decoratively
- **WHEN** the CTA renders on a desktop viewport
- **THEN** a large mail icon appears behind the CTA content
- **AND** the icon is decorative, non-interactive, and visually subordinate to the headline, body copy, and button

#### Scenario: Background icon does not affect accessibility
- **WHEN** assistive technology reads the CTA
- **THEN** the decorative background mail icon is hidden from the accessible name and reading order
- **AND** it does not intercept pointer events intended for the CTA button

### Requirement: CTA and dialog copy describe one offer
The CTA card, trigger button, dialog title, and dialog description SHALL consistently frame the interaction as requesting the GitBench analysis PDF or analysis by email. The dialog SHALL NOT switch to unrelated generic update or newsletter language.

#### Scenario: Copy stays aligned from card to dialog
- **WHEN** a user opens the CTA dialog
- **THEN** the dialog title and description match the offer introduced by the CTA card
- **AND** the primary action text does not imply a different signup purpose

### Requirement: Email capture behavior is preserved
The CTA SHALL keep the existing dialog-based email capture behavior, including browser email validation, submission to `/api/email-signups`, disabled submitting state, error display, success confirmation, privacy link, and state reset when the dialog closes.

#### Scenario: Valid email can be submitted
- **WHEN** a user enters a valid email address and submits the dialog form
- **THEN** the form posts the email to `/api/email-signups`
- **AND** the dialog displays a success confirmation when the API accepts the submission

#### Scenario: Invalid or failed submission is handled
- **WHEN** a user submits an invalid email or the API returns an error
- **THEN** the dialog shows the relevant validation or error message
- **AND** the user can correct the email and submit again

#### Scenario: Dialog reset remains intact
- **WHEN** a user closes and reopens the CTA dialog
- **THEN** previous email input, submission state, success message, and error message are cleared

### Requirement: CTA remains responsive and readable
The CTA SHALL remain readable and free of visual overlap on desktop, tablet, and mobile viewports. Decorative layers SHALL stay behind content, and the primary button SHALL remain easy to tap on narrow screens.

#### Scenario: Mobile CTA layout remains clear
- **WHEN** the CTA renders on a mobile viewport
- **THEN** the headline, body copy, background icon, and button do not overlap incoherently
- **AND** the primary button is usable as a touch target

#### Scenario: Desktop CTA layout remains clear
- **WHEN** the CTA renders on a desktop viewport
- **THEN** the decorative background icon is clipped or positioned so it adds visual interest without obscuring the CTA text
