import type { GitBenchData, ModelPreset } from "./types.ts";

export interface AvailableModelPreset extends ModelPreset {
  availableIds: string[];
  active: boolean;
}

export function exactModelSelection(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const selected = new Set(a);
  return b.every((id) => selected.has(id));
}

export function availableModelPresets(
  presets: ModelPreset[] | undefined,
  availableGroupIds: Iterable<string>,
  currentSelection: string[],
): AvailableModelPreset[] {
  const available = new Set(availableGroupIds);
  return (presets ?? []).map((preset) => {
    const availableIds = preset.modelGroupIds.filter((id) => available.has(id));
    return {
      ...preset,
      availableIds,
      active: exactModelSelection(currentSelection, availableIds),
    };
  });
}

export function defaultModelGroupSelection(
  data: Pick<GitBenchData, "model_presets">,
  availableGroupIds: string[],
): string[] {
  if (data.model_presets === undefined) return availableGroupIds;
  const available = new Set(availableGroupIds);
  return (
    data.model_presets.find((preset) => preset.id === "top-performers")
      ?.modelGroupIds ?? []
  ).filter((id) => available.has(id));
}
