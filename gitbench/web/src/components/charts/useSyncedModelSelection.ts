import { useCallback, useEffect, useRef, useState } from "react";
import type { GitBenchData } from "@/lib/types";
import {
  deriveModelGroups,
  expandGroupSelectionWithMode,
  sanitizeGroupSelection,
  getAvailableOutputModes,
  readStoredOutputMode,
  writeStoredOutputMode,
  type ModelGroup,
  type OutputMode,
} from "@/components/charts/model-groups";

const STORAGE_KEY = "gitbench-model-selection";
const EVENT_NAME = "model-selection-changed";
const OUTPUT_MODE_EVENT_NAME = "output-mode-changed";

function arraysEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  return a.every((value, index) => value === b[index]);
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

function writeSelection(selection: string[]): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(selection));
}

export function useSyncedModelSelection(data: GitBenchData | null) {
  const [selectedGroups, setSelectedGroupsState] = useState<string[]>([]);
  const [outputMode, setOutputModeState] = useState<OutputMode>(
    readStoredOutputMode()
  );
  const selectedRef = useRef<string[]>([]);
  const outputModeRef = useRef<OutputMode>(outputMode);
  const groupsRef = useRef<ModelGroup[]>([]);

  // Derive selected models based on groups + output mode
  const selectedModels = data
    ? expandGroupSelectionWithMode(selectedGroups, data, outputMode)
    : [];

  useEffect(() => {
    const groups = data ? deriveModelGroups(data) : [];
    groupsRef.current = groups;

    if (groups.length === 0) {
      if (selectedRef.current.length === 0) return;
      selectedRef.current = [];
      setSelectedGroupsState([]);
      return;
    }

    const stored = readStoredSelection(groups);
    const next =
      stored && stored.length > 0 ? stored : groups.map((group) => group.id);
    selectedRef.current = next;
    setSelectedGroupsState(next);
    writeSelection(next);
  }, [data]);

  const setSelectedGroups = useCallback((nextSelection: string[]) => {
    const next = sanitizeGroupSelection(nextSelection, groupsRef.current);
    if (arraysEqual(selectedRef.current, next)) return;

    selectedRef.current = next;
    setSelectedGroupsState(next);
    writeSelection(next);
    window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: next }));
  }, []);

  const setOutputMode = useCallback((mode: OutputMode) => {
    if (outputModeRef.current === mode) return;
    outputModeRef.current = mode;
    setOutputModeState(mode);
    writeStoredOutputMode(mode);
    window.dispatchEvent(
      new CustomEvent(OUTPUT_MODE_EVENT_NAME, { detail: mode })
    );
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (!Array.isArray(detail)) return;

      const next = sanitizeGroupSelection(
        detail.filter((value): value is string => typeof value === "string"),
        groupsRef.current
      );

      if (arraysEqual(selectedRef.current, next)) return;
      selectedRef.current = next;
      setSelectedGroupsState(next);
      writeSelection(next);
    };

    window.addEventListener(EVENT_NAME, handler);
    return () => window.removeEventListener(EVENT_NAME, handler);
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const mode = (event as CustomEvent).detail;
      if (mode !== "text" && mode !== "json_schema" && mode !== "both") return;
      if (outputModeRef.current === mode) return;

      outputModeRef.current = mode;
      setOutputModeState(mode);
      writeStoredOutputMode(mode);
    };

    window.addEventListener(OUTPUT_MODE_EVENT_NAME, handler);
    return () => window.removeEventListener(OUTPUT_MODE_EVENT_NAME, handler);
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
