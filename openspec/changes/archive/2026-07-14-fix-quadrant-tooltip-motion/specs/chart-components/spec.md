## ADDED Requirements

### Requirement: Quadrant chart tooltip motion is localized

The `QuadrantComparisonChart` mouse-hover tooltip SHALL appear in-place at the hovered point on the first active hover in a new hover cycle. When the tooltip is already visible or still within its hover continuity window, moving hover to another quadrant point SHALL update the tooltip for the new point and animate the tooltip position from the previous displayed location to the new displayed location. The tooltip SHALL NOT animate in from an off-chart, default, or stale coordinate on a fresh hover.

#### Scenario: First hover pops in-place

- **WHEN** no quadrant mouse-hover tooltip is active and a user hovers a quadrant point
- **THEN** the paired tooltip becomes visible adjacent to that point without animated positional travel from an off-chart, default, or previously hovered coordinate

#### Scenario: Direct point-to-point hover animates position

- **WHEN** the quadrant mouse-hover tooltip is visible for one point
- **AND** the user moves hover directly to another quadrant point before the hover continuity window expires
- **THEN** the tooltip updates to the newly hovered point's paired content
- **AND** the tooltip animates its position from the previous displayed location to the new displayed location

#### Scenario: Later fresh hover resets to pop-in

- **WHEN** the quadrant mouse-hover tooltip has been inactive long enough for the hover continuity window to expire
- **AND** the user hovers a quadrant point again
- **THEN** the tooltip appears in-place at the new point without animated positional travel from the last displayed location

#### Scenario: Reduced motion disables point-to-point travel

- **WHEN** the user has requested reduced motion at the system level
- **AND** the user moves hover from one quadrant point to another
- **THEN** the tooltip updates to the newly hovered point without animated positional travel
