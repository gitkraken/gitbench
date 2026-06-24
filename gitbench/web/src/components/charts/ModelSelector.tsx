import { useEffect, useMemo, useRef, useState } from "react";
import type { GitBenchData } from "@/lib/types";
import { loadData } from "@/lib/load-data";
import { Badge } from "@/components/ui/badge";
import { MultiSelect } from "@/components/ui/multi-select";
import ProviderIcon from "@/components/ProviderIcon";
import {
  deriveModelGroups,
  sanitizeGroupSelection,
  type ModelGroup,
} from "@/components/charts/model-groups";

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

const STORAGE_KEY = "gitbench-model-selection";
const EVENT_NAME = "model-selection-changed";

function getPassColor(passRate: number): string {
  if (passRate >= 0.8) return "text-pass bg-pass-bg border-pass-border";
  if (passRate >= 0.5)
    return "text-(--color-warn) bg-warn-bg border-(--color-warn-border)";
  return "text-fail bg-fail-bg border-(--color-fail-border)";
}

function readStoredSelection(groups: ModelGroup[]): string[] | null {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (!stored) return null;

  try {
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return null;
    return sanitizeGroupSelection(
      parsed.filter((value): value is string => typeof value === "string"),
      groups
    );
  } catch {
    return null;
  }
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

      const next = initialSelected
        ? sanitizeGroupSelection(initialSelected, groups)
        : readStoredSelection(groups);
      setSelected(
        next && next.length > 0 ? next : groups.map((group) => group.id)
      );
      return;
    }

    loadData().then((loaded) => {
      const groups = deriveModelGroups(loaded);
      setData(loaded);
      groupsRef.current = groups;
      if (isControlled) return;

      const next = initialSelected
        ? sanitizeGroupSelection(initialSelected, groups)
        : readStoredSelection(groups);
      setSelected(
        next && next.length > 0 ? next : groups.map((group) => group.id)
      );
    });
  }, [providedData, initialSelected, isControlled]);

  useEffect(() => {
    if (!isControlled && initialSelected && groupsRef.current.length > 0) {
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
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: next }));
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
