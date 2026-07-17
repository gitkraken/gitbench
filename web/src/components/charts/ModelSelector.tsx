import { useEffect, useMemo, useRef, useState } from "react";
import type { GitBenchData } from "@/lib/types";
import { loadData } from "@/lib/load-data";
import { MultiSelect } from "@/components/ui/multi-select";
import ProviderIcon from "@/components/ProviderIcon";
import {
  deriveModelGroups,
  getAvailableOutputModes,
  sanitizeGroupSelection,
  type ModelGroup,
} from "@/components/charts/model-groups";
import { resolveReportViewState } from "@/lib/report-url-state";
import {
  availableModelPresets,
  defaultModelGroupSelection,
} from "@/lib/model-selector-state";

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

export const MODEL_SELECTOR_TRIGGER_CLASS =
  "w-[min(18rem,calc(100vw-2rem))] max-w-full";
export const MODEL_SELECTOR_PANEL_CLASS =
  "w-[min(34rem,calc(100vw-2rem))] max-w-[calc(100vw-2rem)]";

const EVENT_NAME = "model-selection-changed";

function topPerformerDefault(data: GitBenchData, groups: ModelGroup[]): string[] {
  return defaultModelGroupSelection(
    data,
    groups.map((group) => group.id),
  );
}

function formatContext(tokens: number | null): string {
  if (tokens === null) return "Unknown context";
  if (tokens >= 1_000_000) return `${tokens / 1_000_000}M context`;
  return `${Math.round(tokens / 1_000)}K context`;
}

function formatWeight(value: "open" | "closed" | "unknown"): string {
  if (value === "open") return "Open weights";
  if (value === "closed") return "Closed weights";
  return "Unknown weights";
}

function initialSelectionForGroups(
  data: GitBenchData,
  groups: ModelGroup[],
  initialSelected: string[] | undefined,
): string[] {
  if (initialSelected && initialSelected.length > 0) {
    const selected = sanitizeGroupSelection(initialSelected, groups);
    if (selected.length > 0) return selected;
  }

  if (typeof window !== "undefined") {
    return resolveReportViewState(window.location.search, groups, {
      defaultSelectedGroups: topPerformerDefault(data, groups),
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

      setSelected(
        initialSelectionForGroups(providedData, groups, initialSelected),
      );
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

  const options = groups.map((group) => {
    const metadata = data?.model_metadata?.[group.id];
    return {
      value: group.id,
      label: group.baseModel,
      keywords: [
        group.provider,
        group.baseModel,
        group.id,
        metadata ? formatContext(metadata.contextWindowTokens) : "Unknown context",
        metadata ? formatWeight(metadata.weightAccess) : "Unknown weights",
        ...group.efforts.flatMap((effort) => [
          effort.modelName,
          effort.reasoningLevel ?? "",
        ]),
      ],
    };
  });

  const availablePresets = availableModelPresets(
    data?.model_presets,
    groups.map((group) => group.id),
    currentSelected,
  );

  const applySelection = (values: string[]) => {
    const next = sanitizeGroupSelection(values, groupsRef.current);
    if (!isControlled) setSelected(next);
    onChange?.(next);
  };

  return (
    <MultiSelect
      options={options}
      value={currentSelected}
      onChange={applySelection}
      placeholder="Select models..."
      ariaLabel="Select chart models"
      searchPlaceholder="Search models..."
      emptyMessage="No models found"
      triggerClassName={MODEL_SELECTOR_TRIGGER_CLASS}
      panelClassName={MODEL_SELECTOR_PANEL_CLASS}
      headerContent={
        availablePresets.length ? (
          <div className="px-2 py-2" aria-label="Model presets">
            <div className="mb-1.5 px-1 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
              Presets
            </div>
            <div className="grid grid-cols-2 gap-1 sm:grid-cols-3">
              {availablePresets.map((preset) => {
                return (
                  <button
                    key={preset.id}
                    type="button"
                    aria-pressed={preset.active}
                    title={preset.description}
                    className={`min-w-0 rounded-md border px-2 py-1.5 text-left text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      preset.active
                        ? "border-primary bg-primary/10 text-foreground"
                        : "border-border text-muted-foreground hover:bg-accent hover:text-foreground"
                    }`}
                    onKeyDown={(event) => event.stopPropagation()}
                    onClick={() => applySelection(preset.availableIds)}
                  >
                    <span className="block truncate font-medium">{preset.label}</span>
                    <span className="block text-[0.65rem] tabular-nums opacity-75">
                      {preset.availableIds.length} available
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : null
      }
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
        const metadata = data?.model_metadata?.[option.value];
        if (!group) return null;
        return (
          <span className="ml-2 flex shrink-0 flex-col items-end text-[0.62rem] leading-tight text-muted-foreground">
            <span>{group.provider}</span>
            <span>
              {metadata
                ? `${formatContext(metadata.contextWindowTokens)} · ${formatWeight(metadata.weightAccess)}`
                : "Unknown context · Unknown weights"}
            </span>
          </span>
        );
      }}
    />
  );
}
