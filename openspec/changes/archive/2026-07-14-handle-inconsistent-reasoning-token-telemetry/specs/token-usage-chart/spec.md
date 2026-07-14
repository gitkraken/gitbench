## MODIFIED Requirements

### Requirement: TokenUsageChart renders reasoning tokens as a stacked bar segment
The `TokenUsageChart` component SHALL render reasoning tokens as a stacked decomposition of provider-reported output when the representative effort has reasoning data. Each representative bar SHALL stack input tokens, derived visible output tokens, and bounded reasoning-within-output tokens so the full stack equals the representative effort's `total_tokens` when provider totals are internally consistent. When a representative effort reports more reasoning tokens than output tokens, the chart SHALL preserve the raw reasoning value for tooltip disclosure, but SHALL cap the stacked reasoning segment at provider output and SHALL not stack reasoning overflow as additional total tokens. The reasoning segment SHALL use a lighter tint of the provider color. Groups with no reasoning data SHALL render input and output only.

#### Scenario: Reasoning stack does not double-count output
- **WHEN** the representative effort has input 500, provider output 200, reasoning 150, and total 700
- **THEN** the bar SHALL stack 500 input, 50 visible output, and 150 reasoning to a height of 700

#### Scenario: Representative effort supplies stack segments
- **WHEN** a mode contains multiple effort levels and its median representative is `medium`
- **THEN** the bar segments SHALL use the `medium` effort's token decomposition rather than sums across all effort levels

#### Scenario: No reasoning segment for non-reasoning data
- **WHEN** a representative effort has no reasoning token data
- **THEN** its bar SHALL render input and provider output segments with no reasoning segment

#### Scenario: Reasoning segment uses lighter color tint
- **WHEN** a provider's color is `#3B82F6`
- **THEN** the reasoning segment SHALL use a translucent variant visually distinct from visible output

#### Scenario: Inconsistent provider counts are capped
- **WHEN** a representative effort reports input 500, output 100, total 600, and reasoning 120
- **THEN** the visible-output segment SHALL be zero
- **AND** the stacked reasoning segment SHALL be capped at 100
- **AND** the bar SHALL not render a negative segment
- **AND** the bar SHALL not stack the 20-token reasoning overflow above the provider total

### Requirement: TokenUsageChart tooltip shows reasoning token breakdown
The chart tooltip SHALL place a compact, color-coded `Total · (in / out / reasoning)` legend above its mode sections. Each effort SHALL render its total and grouped input, provider output, and bounded reasoning values on one line using the same effort-row font size as other chart tooltips. The grouped values SHALL use colors that correspond to the legend and SHALL use compact number formatting so the tooltip remains narrow without reducing the effort-row type size. Missing reasoning data SHALL use an unavailable marker in the reasoning position rather than verbose explanatory copy.

When raw reasoning tokens exceed provider output tokens, the reasoning position SHALL show bounded reasoning plus overflow using compact `bounded+overflow*` notation. The tooltip SHALL explain the marker once with a shared provider-overflow footnote and SHALL not repeat overflow prose on every effort row. The grouped values and footnote together SHALL preserve the raw reasoning value without presenting overflow as additional output or chart height. The tooltip content SHALL be capped at 300 CSS pixels wide.

#### Scenario: Tooltip with reasoning tokens
- **WHEN** an effort has input 500, provider output 200, reasoning 150, and total 700
- **THEN** the tooltip SHALL show a single effort row equivalent to `700 · (500 / 200 / 150)` under the color-coded grouping legend
- **AND** the effort row SHALL use the same font size as effort rows in other chart tooltips

#### Scenario: Tooltip without reasoning data
- **WHEN** an effort has input 500, output 200, and no reasoning token data
- **THEN** the tooltip SHALL show a grouped value equivalent to `(500 / 200 / —)` without adding an explanatory line

#### Scenario: Tooltip with zero reasoning tokens
- **WHEN** an effort has a reasoning level, provider output 200, and `reasoning_tokens: 0`
- **THEN** the tooltip SHALL show zero in the color-coded reasoning position

#### Scenario: Tooltip with inconsistent provider telemetry
- **WHEN** an effort has input 500, provider output 100, reasoning 120, and total 600
- **THEN** the tooltip SHALL show a single effort row equivalent to `600 · (500 / 100 / 100+20*)`
- **AND** the tooltip SHALL show one shared footnote identifying `*` as provider-reported reasoning overflow
- **AND** the tooltip SHALL not render a separate verbose overflow line for the effort

#### Scenario: Dense tooltip remains compact and readable
- **WHEN** both output modes contain multiple effort levels
- **THEN** every effort's total and grouped token values SHALL remain on one row
- **AND** the tooltip content width SHALL not exceed 300 CSS pixels
- **AND** the implementation SHALL use compact number formatting rather than a smaller effort-row font to satisfy the width constraint
