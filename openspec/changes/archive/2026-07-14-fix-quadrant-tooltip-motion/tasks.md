## 1. Tooltip Motion Implementation

- [x] 1.1 Add hover-cycle priming state and cleanup refs to `QuadrantComparisonChart`.
- [x] 1.2 Add a small Recharts tooltip content component that observes active payload state, primes motion after the first active render, resets priming after a short inactive grace window, and delegates rendering to `QuadrantPairTooltip`.
- [x] 1.3 Wire the Recharts `<Tooltip>` animation props so first hover renders with positional animation disabled, primed point-to-point hover uses a short reduced-motion-aware transform animation, and existing cursor/content/pair lookup behavior is preserved.
- [x] 1.4 Preserve the last displayed wrapper transform during the inactive grace window so quick re-entry animates from the prior tooltip position instead of the chart origin.

## 2. Verification

- [x] 2.1 Run the web build/typecheck from `web/` and resolve any TypeScript or Astro errors introduced by the tooltip changes.
- [x] 2.2 Manually verify on a quadrant chart that first hover pops in-place, direct point-to-point hover animates to the next location, a later fresh hover pops in-place again, and keyboard focus tooltip behavior remains unchanged.
- [x] 2.3 Reproduce and verify the inactive-grace re-entry path does not animate from the chart origin, including with reduced motion.
