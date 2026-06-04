## MODIFIED Requirements

### Requirement: Prose avoids describing what is already visible
Section blurbs SHALL provide non-obvious context: caveats, insights, or orientation. They SHALL NOT restate chart titles, axis labels, or badge text that the user can see. A chart titled "Token Usage" with a labeled axis does not need a paragraph explaining that it shows token usage.

#### Scenario: Self-explanatory sections have no blurb
- **WHEN** navigating to the Overview page
- **THEN** the "Pass Rate" chart section has no prose blurb above it (the chart title and axes are sufficient)

#### Scenario: Non-obvious context is preserved
- **WHEN** navigating to the Overview page
- **THEN** the "API Time" chart section explains that the metric is API call latency, not full fixture setup or scoring time
