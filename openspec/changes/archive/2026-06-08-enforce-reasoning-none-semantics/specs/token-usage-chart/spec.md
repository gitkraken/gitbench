## MODIFIED Requirements

### Requirement: TokenUsageChart renders reasoning tokens as a stacked bar segment
The `TokenUsageChart` component SHALL render reasoning tokens as a stacked decomposition of provider-reported output when the representative effort has reasoning data. Each representative bar SHALL stack input tokens, derived visible output tokens, and reasoning tokens so the full stack equals the representative effort's `total_tokens`. The reasoning segment SHALL use a lighter tint of the provider color. Groups with no reasoning data SHALL render input and output only.

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

#### Scenario: Inconsistent provider counts are clamped
- **WHEN** a representative effort reports more reasoning tokens than output tokens
- **THEN** the visible-output segment SHALL be zero and the chart SHALL not render a negative segment

### Requirement: TokenUsageChart tooltip shows reasoning token breakdown
The chart tooltip's effort line SHALL display provider total output and reasoning as an included subset when reasoning data exists. It MAY also display derived visible output, but SHALL not present reasoning as additional to provider output. Without reasoning data, the line SHALL display input and output only.

#### Scenario: Tooltip with reasoning tokens
- **WHEN** an effort has input 500, provider output 200, reasoning 150, and total 700
- **THEN** the tooltip SHALL show total 700 and communicate that the 200 output includes 150 reasoning

#### Scenario: Tooltip without reasoning data
- **WHEN** an effort has input 500, output 200, and no reasoning token data
- **THEN** the tooltip SHALL read `in 500 / out 200` or equivalent with no reasoning mention

#### Scenario: Tooltip with zero reasoning tokens
- **WHEN** an effort has a reasoning level, provider output 200, and `reasoning_tokens: 0`
- **THEN** the tooltip SHALL identify zero reasoning within the 200 output tokens
