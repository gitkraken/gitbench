import { useEffect, useMemo, useRef, useState } from "react";
import type { GitBenchData } from "@/lib/types";
import { loadData } from "@/lib/load-data";
import { Badge } from "@/components/ui/badge";
import { MultiSelect } from "@/components/ui/multi-select";
import ProviderIcon from "@/components/ProviderIcon";
import {
  deriveModelGroups,
  getAvailableOutputModes,
  sanitizeGroupSelection,
  type ModelGroup,
} from "@/components/charts/model-groups";
import { resolveReportViewState } from "@/lib/report-url-state";

/**
 * Returns the top two provider/base-model group IDs sorted by mean pass
 * rate descending, skipping groups without a measurable pass rate.
 * Used as the cold-load default for the Compare page.
 */
export function defaultSelectionForCompare(data: GitBenchData): string[] {
  const groups = deriveModelGroups(data);
  const ranked = groups
    .map((group) => {
      const passRates = group.efforts
        .map((e) => e.passRate)
        .filter((r): r is number => r != null);
      if (passRates.length === 0) return null;
      const mean = passRates.reduce((sum, r) => sum + r, 0) / passRates.length;
      return { id: group.id, mean };
    })
    .filter((x): x is { id: string; mean: number } => x !== null)
    .sort((a, b) => b.mean - a.mean);
  return ranked.slice(0, 2).map((x) => x.id);
}

interface ModelSelectorProps {
  data?: GitBenchData;
  initialSelected?: string[];
  value?: string[];
  onChange?: (selected: string[]) => void;
}

const EVENT_NAME = "model-selection-changed";

function getPassColor(passRate: number): string {
  if (passRate >= 0.8) return "text-pass bg-pass-bg border-pass-border";
  if (passRate >= 0.5)
    return "text-(--color-warn) bg-warn-bg border-(--color-warn-border)";
  return "text-fail bg-fail-bg border-(--color-fail-border)";
}

function passRange(group: ModelGroup): { label: string; colorValue: number } {
  const values = group.efforts
    .map((effort) => effort.passRate)
    .filter((value): value is number => value != null)
    .map((value) => Math.round(value * 1000) / 10);
  if (values.length === 0) return { label: "N/A", colorValue: 0 };
  const min = Math.min(...values);
  const max = Math.max(...values);
  return {
    label: min === max ? `${max}%` : `${min}-${max}%`,
    colorValue: max / 100,
  };
}

function initialSelectionForGroups(
  data: GitBenchData,
  groups: ModelGroup[],
  initialSelected: string[] | undefined
): string[] {
  if (initialSelected && initialSelected.length > 0) {
    const selected = sanitizeGroupSelection(initialSelected, groups);
    if (selected.length > 0) return selected;
  }

  if (typeof window !== "undefined") {
    return resolveReportViewState(window.location.search, groups, {
      availableOutputModes: getAvailableOutputModes(data),
    }).selectedGroups;
  }

  return groups.map((group) => group.id);
}

export default function ModelSelector({
  data: providedData,
  initialSelected,
  value,
  onChange,
}: ModelSelectorProps) {
  const [data, setData] = useState<GitBenchData | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const groupsRef = useRef<ModelGroup[]>([]);
  const isControlled = value !== undefined;
  const currentSelected = value ?? selected;

  useEffect(() => {
    if (providedData) {
      const groups = deriveModelGroups(providedData);
      setData(providedData);
      groupsRef.current = groups;
      if (isControlled) return;

      setSelected(initialSelectionForGroups(providedData, groups, initialSelected));
      return;
    }

    loadData().then((loaded) => {
      const groups = deriveModelGroups(loaded);
      setData(loaded);
      groupsRef.current = groups;
      if (isControlled) return;

      setSelected(initialSelectionForGroups(loaded, groups, initialSelected));
    });
  }, [providedData, initialSelected, isControlled]);

  useEffect(() => {
    if (
      !isControlled &&
      initialSelected &&
      initialSelected.length > 0 &&
      groupsRef.current.length > 0
    ) {
      setSelected(sanitizeGroupSelection(initialSelected, groupsRef.current));
    }
  }, [initialSelected?.join(","), isControlled]);

  useEffect(() => {
    if (isControlled) {
      setSelected(value);
    }
  }, [isControlled, value?.join(",")]);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (
        !Array.isArray(detail) ||
        !detail.every((item) => typeof item === "string")
      )
        return;
      const next = sanitizeGroupSelection(detail, groupsRef.current);
      if (next.length !== detail.length && groupsRef.current.length > 0) return;
      if (!isControlled) {
        setSelected(next);
      }
      onChange?.(next);
    };
    window.addEventListener(EVENT_NAME, handler);
    return () => window.removeEventListener(EVENT_NAME, handler);
  }, [isControlled, onChange]);

  const groups = useMemo(() => (data ? deriveModelGroups(data) : []), [data]);
  useEffect(() => {
    groupsRef.current = groups;
  }, [groups]);

  const groupById = useMemo(() => {
    return new Map(groups.map((group) => [group.id, group]));
  }, [groups]);

  const options = groups.map((group) => ({
    value: group.id,
    label: group.baseModel,
    keywords: [
      group.provider,
      group.baseModel,
      group.id,
      ...group.efforts.flatMap((effort) => [
        effort.modelName,
        effort.reasoningLevel ?? "",
      ]),
    ],
  }));

  return (
    <MultiSelect
      options={options}
      value={currentSelected}
      onChange={(vals) => {
        const next = sanitizeGroupSelection(vals, groupsRef.current);
        if (!isControlled) {
          setSelected(next);
        }
        onChange?.(next);
      }}
      placeholder="Select models..."
      searchPlaceholder="Search models..."
      emptyMessage="No models found"
      renderItemStart={(option) => {
        const group = groupById.get(option.value);
        if (!group) return null;
        return (
          <span className="mr-1.5 inline-flex shrink-0 align-middle">
            <ProviderIcon provider={group.provider} size={14} />
          </span>
        );
      }}
      renderItemEnd={(option) => {
        const group = groupById.get(option.value);
        if (!group) return null;
        const range = passRange(group);
        return (
          <span className="ml-2 inline-flex shrink-0 items-center gap-1.5">
            <Badge
              className={`rounded-full border px-1.5 py-px font-mono text-[0.6rem] ${getPassColor(
                range.colorValue
              )}`}
            >
              {range.label}
            </Badge>
            <span className="font-mono text-[0.6rem] text-muted-foreground">
              {group.efforts.length}{" "}
              {group.efforts.length === 1 ? "effort" : "efforts"}
            </span>
          </span>
        );
      }}
    />
  );
}
