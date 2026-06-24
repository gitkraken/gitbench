## ADDED Requirements

### Requirement: CostValueChart y-axis ticks never use scientific notation

The y-axis tick formatter on the `CostValueChart` SHALL render every
tick value as a USD currency string with no scientific notation. Tick
value `0` SHALL render as `$0`. Tick values smaller than `0.01` SHALL
render with up to four fraction digits (e.g. `$0.0052`). Non-finite
values (`NaN`, `Infinity`) SHALL render as `—`. The formatter SHALL be
shared by the chart's tooltip and the bar value labels.

#### Scenario: Zero tick renders as $0
- **WHEN** the y-axis includes the tick value `0`
- **THEN** the rendered tick label is `$0` and never contains `e+`, `e-`, or `E+`

#### Scenario: Sub-cent tick renders with enough precision
- **WHEN** a tick value is `0.00516`
- **THEN** the rendered tick label is `$0.0052` (or `$0.00516` if four fraction digits are kept), never `$5.2e-3`

#### Scenario: Non-finite tick renders as em dash
- **WHEN** the y-axis domain would otherwise include `NaN` or `Infinity`
- **THEN** the rendered tick label is `—`
