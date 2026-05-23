# responsive-sidebar Specification

## Purpose
TBD - created by archiving change responsive-main-menu. Update Purpose after archive.
## Requirements
### Requirement: Collapsible sidebar on tablet viewports
At viewport widths 601–960px, the sidebar SHALL be collapsible. It SHALL default to the expanded state (icons and labels visible, 220px wide). A toggle button at the bottom of the sidebar SHALL switch between expanded (220px) and collapsed (~64px, icons only) states. The toggle SHALL use a CSS checkbox hack so the core show/hide behavior works without JavaScript.

#### Scenario: Sidebar is expanded by default on tablet
- **WHEN** the page loads at a viewport width between 601px and 960px
- **THEN** the sidebar renders at 220px width with both icons and text labels visible for all nav items

#### Scenario: Collapse button shrinks sidebar to icons only
- **WHEN** the user clicks the collapse toggle button on a tablet viewport
- **THEN** the sidebar shrinks to approximately 64px width, nav labels are hidden, and only icons remain visible

#### Scenario: Expand button restores full sidebar
- **WHEN** the sidebar is collapsed and the user clicks the expand toggle button
- **THEN** the sidebar returns to 220px width with both icons and labels visible

#### Scenario: Content area expands when sidebar collapses
- **WHEN** the sidebar is collapsed on a tablet viewport
- **THEN** the `.app-main` content area margin-left adjusts to approximately 64px, reclaiming horizontal space for page content

#### Scenario: Collapse toggle is not visible on desktop
- **WHEN** the viewport width is greater than 960px
- **THEN** the collapse toggle button is hidden and the sidebar remains at its full 220px width

#### Scenario: Collapse toggle is not visible on mobile
- **WHEN** the viewport width is 600px or less
- **THEN** the collapse toggle button is hidden and the mobile hamburger pattern takes over

### Requirement: Hamburger menu on mobile viewports
At viewport widths ≤600px, the sidebar SHALL become a sticky top bar with a hamburger toggle. The nav SHALL be hidden by default and SHALL drop down vertically when the hamburger is tapped. The hamburger SHALL use a CSS checkbox hack to function without JavaScript. The hamburger icon SHALL animate into an X when the menu is open.

#### Scenario: Sidebar is sticky top bar on mobile
- **WHEN** the viewport width is 600px or less
- **THEN** the sidebar renders as a sticky horizontal bar at the top of the viewport containing the logo, branding text, and a hamburger button

#### Scenario: Nav is hidden by default on mobile
- **WHEN** the page loads on a mobile viewport
- **THEN** the nav links are not visible and the hamburger shows three horizontal bars

#### Scenario: Hamburger opens vertical nav
- **WHEN** the user taps the hamburger button on a mobile viewport
- **THEN** the seven nav links appear in a vertical list below the header bar, pushing page content down

#### Scenario: Hamburger animates to X when open
- **WHEN** the mobile menu is open
- **THEN** the hamburger icon shows an X shape (top and bottom bars rotated 45° in opposite directions, middle bar hidden)

#### Scenario: Hamburger returns to three bars when closed
- **WHEN** the mobile menu is closed
- **THEN** the hamburger icon returns to three horizontal bars

#### Scenario: Mobile nav is a vertical list
- **WHEN** the nav is expanded on a mobile viewport
- **THEN** all seven nav links are displayed in a vertical column, not a horizontal row

#### Scenario: No horizontal scrolling on mobile nav
- **WHEN** the nav is visible on a mobile viewport
- **THEN** no horizontal scrollbar appears and all link text fits within the viewport width

### Requirement: Branding text visibility across breakpoints
The "GitBench" title and "by GitKraken" subtitle in the sidebar header SHALL remain visible at all viewport widths. The GitKraken logo icon SHALL also be visible at all widths.

#### Scenario: Full branding visible at all widths
- **WHEN** viewing the site on any viewport width
- **THEN** both "GitBench" and "by GitKraken" text are visible in the sidebar header

#### Scenario: Logo always visible
- **WHEN** viewing the site on any viewport width
- **THEN** the GitKraken icon logo is rendered in the sidebar header

### Requirement: CSS-only core functionality with JS ARIA enhancement
Both the tablet collapse toggle and the mobile hamburger toggle SHALL function without JavaScript for their core show/hide behavior. A small JavaScript snippet SHALL add `aria-expanded` attributes to the checkbox inputs and nav elements when JS is available.

#### Scenario: Menu toggles work with JavaScript disabled
- **WHEN** JavaScript is disabled in the browser
- **THEN** both the tablet collapse toggle and mobile hamburger toggle open and close the nav correctly

#### Scenario: aria-expanded is set when JS is available
- **WHEN** JavaScript is enabled and the user opens the mobile menu
- **THEN** the checkbox input element has `aria-expanded="true"` and the nav element has `aria-expanded="true"`

#### Scenario: aria-expanded updates on close
- **WHEN** JavaScript is enabled and the user closes the mobile menu
- **THEN** the checkbox input element has `aria-expanded="false"` and the nav element has `aria-expanded="false"`

