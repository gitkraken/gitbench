/** Ordinal sort orders used across the app. Single source of truth. */

export const REASONING_LEVEL_ORDER: Record<string, number> = {
  "": 0,
  none: 0,
  default: 0,
  low: 1,
  medium: 2,
  high: 3,
  xhigh: 4,
  max: 5,
};

export const DIFFICULTY_ORDER: Record<string, number> = {
  trivial: 0,
  easy: 1,
  medium: 2,
  hard: 3,
  expert: 4,
};

/** Compare two reasoning level strings using natural effort order.
 *  Unknown values sort after all known levels (order 99), then alphabetically. */
export function compareReasoningLevels(a: string, b: string): number {
  const aKey = a?.toLowerCase() ?? "";
  const bKey = b?.toLowerCase() ?? "";
  const aOrder = REASONING_LEVEL_ORDER[aKey] ?? 99;
  const bOrder = REASONING_LEVEL_ORDER[bKey] ?? 99;
  if (aOrder !== bOrder) return aOrder - bOrder;
  return aKey.localeCompare(bKey);
}
