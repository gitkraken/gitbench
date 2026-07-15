## Context

`QuadrantComparisonChart` uses Recharts `<Tooltip>` for mouse hover tooltips. Recharts positions the tooltip wrapper with a CSS `transform` and, while active, applies a default transform transition. On the first hover after the tooltip has been inactive, that transition can interpolate from a hidden, default, or stale wrapper position to the hovered point, producing the observed off-screen fly-in.

The quadrant chart also has a separate keyboard-focus tooltip rendered as an absolute element near the chart header. This change targets the Recharts mouse-hover tooltip motion without changing tooltip content, pair lookup, cursor behavior, or keyboard-focus affordances.

## Goals / Non-Goals

**Goals:**

- Make the first tooltip in a new hover cycle appear at the active point without animated positional travel.
- Preserve a smooth, interruptible position transition when moving directly between hovered model points.
- Keep existing Recharts positioning, collision handling, cursor rendering, and tooltip payload behavior.
- Respect reduced-motion preferences and avoid introducing a new animation dependency.

**Non-Goals:**

- Replacing Recharts tooltip positioning with a custom overlay system.
- Changing quadrant point rendering, ranking, text/JSON pairing, or tooltip content.
- Changing the separate keyboard-focus tooltip layout.
- Standardizing tooltip motion across all chart components.

## Decisions

### Use Recharts tooltip positioning with dynamic animation priming

The implementation should keep Recharts `<Tooltip>` as the source of payload, coordinate, cursor, and viewport-aware positioning. The chart should control only whether the tooltip wrapper is allowed to animate its `transform`.

Recommended shape:

- Track whether the current tooltip hover cycle is "primed" for motion.
- Render the first active tooltip in a cycle with `isAnimationActive={false}` so its measured wrapper appears directly at the target coordinate.
- After the first active paint, mark the tooltip as primed.
- Once primed, allow Recharts' transform transition again, preferably with a short duration appropriate for hover movement.

Alternative considered: permanently disable tooltip animation. That removes the fly-in but also removes the desired spatial continuity when users move between nearby model points.

Alternative considered: build a fully custom tooltip overlay from scatter point mouse handlers. That would duplicate Recharts coordinate, portal, clipping, and collision logic for a small motion fix.

### Reset priming after an inactive grace period

The hover cycle should not reset immediately on inactive, because pointer movement between scatter points can pass briefly through empty chart space. A short inactive grace window, roughly 100-150ms, preserves movement continuity during intentional point-to-point hover while treating later hovers as fresh pop-ins.

Alternative considered: reset on every inactive frame. That makes every new point pop in, including normal movement between neighboring models, which contradicts the desired "animate to the next location" behavior.

### Drive priming from actual tooltip active state

The most reliable signal is the active/payload state passed to the Recharts tooltip content. A small tooltip content component can observe `active` and payload presence, schedule priming after the first active render, and schedule reset after inactive.

Alternative considered: infer activity from scatter shape `onMouseEnter`/`onMouseLeave`. That bypasses Recharts' own tooltip activation model and risks drifting from the payload/coordinate Recharts actually uses.

### Let reduced-motion disable positional animation

When the tooltip is primed, use Recharts' reduced-motion-aware animation mode rather than forcing animation on. When not primed, force animation off.

## Risks / Trade-offs

- State updates from tooltip content could cause unnecessary rerenders → keep the state small, guard repeated updates, and clean up timers/animation frames.
- A very fast second hover before priming completes may also pop instead of animate → prime after the first active paint so the initial fly-in is prevented; this edge case is preferable to reintroducing first-hover travel.
- Recharts internals may change in future versions → keep the solution expressed through public `<Tooltip>` props such as `isAnimationActive`, `animationDuration`, and custom `content`.

## Migration Plan

1. Update `QuadrantComparisonChart` to gate Recharts tooltip animation by hover-cycle priming.
2. Preserve the existing `QuadrantPairTooltip` content component and pair lookup behavior.
3. Verify the web build/typecheck.
4. Manually verify hover behavior on the quadrant chart:
   - first hover pops in-place,
   - point-to-point hover animates position,
   - later fresh hover pops in-place again,
   - keyboard focus tooltip still appears.

## Open Questions

- None.
