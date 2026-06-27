import { useCallback, useEffect, useRef, useState } from "react";
import type { GitBenchData } from "@/lib/types";
import {
  deriveModelGroups,
  expandGroupSelectionWithMode,
  sanitizeGroupSelection,
  getAvailableOutputModes,
  type ModelGroup,
  type OutputMode,
} from "@/components/charts/model-groups";
import {
  encodeReportViewState,
  resolveReportViewState,
  writeReportViewStateToHistory,
} from "@/lib/report-url-state";

const EVENT_NAME = "model-selection-changed";
const OUTPUT_MODE_EVENT_NAME = "output-mode-changed";

interface SyncedModelSelectionOptions {
  defaultSelectedGroups?: string[];
  defaultOutputMode?: OutputMode;
}

function arraysEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((value, index) => value === b[index]);
}

function reportOptions(
  data: GitBenchData,
  options: SyncedModelSelectionOptions
) {
  return {
    defaultSelectedGroups: options.defaultSelectedGroups,
    defaultOutputMode: options.defaultOutputMode,
    availableOutputModes: getAvailableOutputModes(data),
  };
}

function canonicalStateKey(
  selectedGroups: string[],
  outputMode: OutputMode,
  groups: ModelGroup[],
  data: GitBenchData,
  options: SyncedModelSelectionOptions
): string {
  return encodeReportViewState(
    { selectedGroups, outputMode },
    groups,
    reportOptions(data, options)
  );
}

export function useSyncedModelSelection(
  data: GitBenchData | null,
  options: SyncedModelSelectionOptions = {}
) {
  const [selectedGroups, setSelectedGroupsState] = useState<string[]>([]);
  const [outputMode, setOutputModeState] = useState<OutputMode>("both");
  const selectedRef = useRef<string[]>([]);
  const outputModeRef = useRef<OutputMode>(outputMode);
  const canonicalRef = useRef<string>("");
  const groupsRef = useRef<ModelGroup[]>([]);
  const dataRef = useRef<GitBenchData | null>(null);
  const optionsRef = useRef<SyncedModelSelectionOptions>(options);

  optionsRef.current = options;

  // Derive selected models based on groups + output mode
  const selectedModels = data
    ? expandGroupSelectionWithMode(selectedGroups, data, outputMode)
    : [];

  useEffect(() => {
    const groups = data ? deriveModelGroups(data) : [];
    dataRef.current = data;
    groupsRef.current = groups;

    if (!data || groups.length === 0) {
      if (selectedRef.current.length === 0) return;
      selectedRef.current = [];
      setSelectedGroupsState([]);
      return;
    }

    const resolved =
      typeof window === "undefined"
        ? {
            selectedGroups: options.defaultSelectedGroups?.length
              ? sanitizeGroupSelection(options.defaultSelectedGroups, groups)
              : groups.map((group) => group.id),
            outputMode: options.defaultOutputMode ?? "both",
            source: "default" as const,
          }
        : resolveReportViewState(
            window.location.search,
            groups,
            reportOptions(data, options)
          );
    selectedRef.current = resolved.selectedGroups;
    outputModeRef.current = resolved.outputMode;
    canonicalRef.current = canonicalStateKey(
      resolved.selectedGroups,
      resolved.outputMode,
      groups,
      data,
      options
    );
    setSelectedGroupsState(resolved.selectedGroups);
    setOutputModeState(resolved.outputMode);

    if (resolved.source === "legacy") {
      writeReportViewStateToHistory(
        {
          selectedGroups: resolved.selectedGroups,
          outputMode: resolved.outputMode,
        },
        groups,
        reportOptions(data, options)
      );
    }
  }, [
    data,
    options.defaultOutputMode,
    options.defaultSelectedGroups?.join(","),
  ]);

  const setSelectedGroups = useCallback((nextSelection: string[]) => {
    const currentData = dataRef.current;
    if (!currentData) return;

    const next = sanitizeGroupSelection(nextSelection, groupsRef.current);
    if (arraysEqual(selectedRef.current, next)) return;

    selectedRef.current = next;
    setSelectedGroupsState(next);
    const nextCanonical = canonicalStateKey(
      next,
      outputModeRef.current,
      groupsRef.current,
      currentData,
      optionsRef.current
    );
    if (nextCanonical !== canonicalRef.current) {
      canonicalRef.current = nextCanonical;
      writeReportViewStateToHistory(
        { selectedGroups: next, outputMode: outputModeRef.current },
        groupsRef.current,
        reportOptions(currentData, optionsRef.current)
      );
    }
    window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: next }));
  }, []);

  const setOutputMode = useCallback((mode: OutputMode) => {
    const currentData = dataRef.current;
    if (!currentData) return;
    if (outputModeRef.current === mode) return;
    outputModeRef.current = mode;
    setOutputModeState(mode);
    const nextCanonical = canonicalStateKey(
      selectedRef.current,
      mode,
      groupsRef.current,
      currentData,
      optionsRef.current
    );
    if (nextCanonical !== canonicalRef.current) {
      canonicalRef.current = nextCanonical;
      writeReportViewStateToHistory(
        { selectedGroups: selectedRef.current, outputMode: mode },
        groupsRef.current,
        reportOptions(currentData, optionsRef.current)
      );
    }
    window.dispatchEvent(
      new CustomEvent(OUTPUT_MODE_EVENT_NAME, { detail: mode })
    );
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const currentData = dataRef.current;
      if (!currentData) return;
      const detail = (event as CustomEvent).detail;
      if (!Array.isArray(detail)) return;

      const next = sanitizeGroupSelection(
        detail.filter((value): value is string => typeof value === "string"),
        groupsRef.current
      );

      if (arraysEqual(selectedRef.current, next)) return;
      selectedRef.current = next;
      setSelectedGroupsState(next);
      canonicalRef.current = canonicalStateKey(
        next,
        outputModeRef.current,
        groupsRef.current,
        currentData,
        optionsRef.current
      );
    };

    window.addEventListener(EVENT_NAME, handler);
    return () => window.removeEventListener(EVENT_NAME, handler);
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const currentData = dataRef.current;
      if (!currentData) return;
      const mode = (event as CustomEvent).detail;
      if (mode !== "text" && mode !== "json_schema" && mode !== "both") return;
      if (outputModeRef.current === mode) return;

      outputModeRef.current = mode;
      setOutputModeState(mode);
      canonicalRef.current = canonicalStateKey(
        selectedRef.current,
        mode,
        groupsRef.current,
        currentData,
        optionsRef.current
      );
    };

    window.addEventListener(OUTPUT_MODE_EVENT_NAME, handler);
    return () => window.removeEventListener(OUTPUT_MODE_EVENT_NAME, handler);
  }, []);

  useEffect(() => {
    const handler = () => {
      const currentData = dataRef.current;
      if (!currentData) return;

      const resolved = resolveReportViewState(
        window.location.search,
        groupsRef.current,
        reportOptions(currentData, optionsRef.current)
      );
      const nextCanonical = canonicalStateKey(
        resolved.selectedGroups,
        resolved.outputMode,
        groupsRef.current,
        currentData,
        optionsRef.current
      );
      canonicalRef.current = nextCanonical;

      if (!arraysEqual(selectedRef.current, resolved.selectedGroups)) {
        selectedRef.current = resolved.selectedGroups;
        setSelectedGroupsState(resolved.selectedGroups);
      }
      if (outputModeRef.current !== resolved.outputMode) {
        outputModeRef.current = resolved.outputMode;
        setOutputModeState(resolved.outputMode);
      }
    };

    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  }, []);

  return {
    selectedGroups,
    setSelectedGroups,
    selectedModels,
    outputMode,
    setOutputMode,
    availableOutputModes: data
      ? getAvailableOutputModes(data)
      : new Set<string>(),
  };
}
