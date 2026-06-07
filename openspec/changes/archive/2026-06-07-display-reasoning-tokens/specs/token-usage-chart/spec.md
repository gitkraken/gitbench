## ADDED Requirements

### Requirement: TokenUsageChart renders reasoning tokens as a stacked bar segment

The `TokenUsageChart` component SHALL render reasoning tokens as a third stacked segment in each bar when any effort in the group has a reasoning level set. The reasoning segment SHALL use a lighter tint of the provider color. Groups with no reasoning-level efforts SHALL render as two-segment bars (input | output) only.

#### Scenario: Reasoning segment for reasoning models
- **WHEN** a model group has efforts at `low`, `medium`, `high` with reasoning tokens [150, 200, 300]
- **THEN** each bar shows three stacked segments: input, output, and reasoning

#### Scenario: No reasoning segment for non-reasoning models
- **WHEN** a model group's efforts all have `reasoning_level: null`
- **THEN** each bar shows only input and output segments (no reasoning segment)

#### Scenario: Reasoning segment uses lighter color tint
- **WHEN** a provider's color is `#3B82F6` (blue)
- **THEN** the reasoning segment uses a translucent variant (e.g., `rgba(59, 130, 246, 0.35)`) visually distinct from output

### Requirement: TokenUsageChart tooltip shows reasoning token breakdown

The chart tooltip's `renderEffort` line SHALL display `in / out / r` when the effort has a reasoning level. Without a reasoning level, the line SHALL display `in / out` only. The breakdown SHALL use the same compact formatting as other values.

#### Scenario: Tooltip with reasoning tokens
- **WHEN** hovering a bar for an effort with `reasoningTokens: 150`, `inputTokens: 500`, `outputTokens: 200`
- **THEN** the effort line reads `low: 850 (in 500 / out 200 / r 150)`

#### Scenario: Tooltip without reasoning level
- **WHEN** hovering a bar for an effort with `reasoningLevel: null`
- **THEN** the effort line reads `default: 700 (in 500 / out 200)` with no reasoning mention

#### Scenario: Tooltip with zero reasoning tokens
- **WHEN** hovering a bar for an effort with `reasoningLevel: "high"` and `reasoningTokens: 0`
- **THEN** the effort line reads `high: 700 (in 500 / out 200 / r 0)`

## MODIFIED Requirements

### Requirement: TokenUsageChart computes total tokens from fixture data

Token sums SHALL be unaffected by this change. Reasoning tokens are already included in `total_tokens` from the API response.

(All original scenarios remain unchanged.)

#### Scenario: Reasoning tokens included in total
- **WHEN** a model effort has 3 fixtures with reasoning_tokens [50, null, 100]
- **THEN** those reasoning tokens are included in the effort's total via the `total_tokens` sum (since total_tokens already includes reasoning from the API)
