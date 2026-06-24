## ADDED Requirements

### Requirement: App main content area is capped via --main-max-width CSS variable

The site SHALL define a CSS custom property `--main-max-width` on
`:root` in `src/styles/global.css` with a default value of `1440px`.
The `.app-main` element SHALL apply
`max-width: var(--main-max-width); margin-inline: auto;` so the
content area centers within the available width on desktop viewports
(≥960px). Changing the variable's value (or setting it to `none`)
SHALL be the only edit required to revert to full-bleed content on
wide monitors.

#### Scenario: Variable exists on :root with 1440px default
- **WHEN** a developer reads `src/styles/global.css`
- **THEN** `:root` declares `--main-max-width: 1440px;`

#### Scenario: .app-main applies the cap at desktop
- **WHEN** the viewport width is ≥1440px
- **THEN** the `.app-main` element's effective width does not exceed `1440px`
- **AND** the element is horizontally centered within the remaining space (sidebar is fixed 220px on the left)

#### Scenario: Cap does not regress tablet or mobile
- **WHEN** the viewport width is between 601px and 1439px
- **THEN** `.app-main` retains its existing full-bleed behavior inside the sidebar offset
- **WHEN** the viewport width is ≤600px
- **THEN** `.app-main` retains its existing full-bleed behavior (mobile has no sidebar)

#### Scenario: Cap is opt-out via the CSS variable
- **WHEN** a developer sets `--main-max-width: none` on `:root`
- **THEN** `.app-main` stretches to the full remaining width without further code changes
