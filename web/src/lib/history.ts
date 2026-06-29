import type { RunMeta } from "@/lib/types";

export function modelRunCounts(runs: RunMeta[]): Record<string, number> {
  return runs.reduce<Record<string, number>>((counts, run) => {
    counts[run.model] = (counts[run.model] || 0) + 1;
    return counts;
  }, {});
}

export function hasRepeatModelRuns(runs: RunMeta[]): boolean {
  return Object.values(modelRunCounts(runs)).some((count) => count > 1);
}

export function modelsWithRepeatRuns(runs: RunMeta[]): Set<string> {
  const counts = modelRunCounts(runs);
  return new Set(
    Object.entries(counts)
      .filter(([, count]) => count > 1)
      .map(([model]) => model)
  );
}
