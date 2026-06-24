## ADDED Requirements

### Requirement: Model detail page lays out comparison sections without an empty central column

The Model Detail page
(`/models/[provider]/[model]/[level]`) SHALL render the
"Reliability by Benchmark" section and the "Text vs JSON Schema
Comparison" section as full-width blocks at desktop and tablet widths.
Neither section SHALL use a multi-column grid that leaves more than
~10% of its width as empty whitespace between the metadata block and
the data block.

#### Scenario: Reliability section is a single full-width block
- **WHEN** a user navigates to `/models/<provider>/<base-model>/<level>/` at a desktop viewport
- **THEN** the "Reliability by Benchmark" section's content occupies the full available width inside its `.card` wrapper
- **AND** the left and right blocks of that section are stacked vertically (or the data table fills the full row) with no empty central column wider than ~10% of the section

#### Scenario: Text vs JSON comparison section is a single full-width block
- **WHEN** a user navigates to `/models/<provider>/<base-model>/<level>/` at a desktop viewport
- **THEN** the "Text vs JSON Schema Comparison" section's content occupies the full available width inside its `.card` wrapper
- **AND** the four summary tiles and the benchmark delta table are not split into two side-by-side groups separated by empty whitespace

#### Scenario: Tablet layout already single-column is preserved
- **WHEN** a user navigates to `/models/<provider>/<base-model>/<level>/` at a tablet viewport (601–960px)
- **THEN** both sections continue to render as a single column without regression
