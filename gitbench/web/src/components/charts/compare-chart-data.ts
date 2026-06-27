import type { GitBenchData } from "../../lib/types.ts";
import {
  deriveModelGroups,
  pairModelVariants,
  sanitizeGroupSelection,
  visibleOutputModes,
  type ConcreteOutputMode,
  type ModelVariantPair,
  type OutputMode,
} from "./model-groups.ts";

export interface CompareOverallRow {
  id: string;
  label: string;
  pair: ModelVariantPair;
  textPassRate: number | null;
  jsonPassRate: number | null;
  textRaw: number | null;
  jsonRaw: number | null;
  sortValue: number;
}

export interface CompareBenchmarkSeries {
  pairId: string;
  label: string;
  outputMode: ConcreteOutputMode;
  dataKey: string;
  color: string;
  modelName?: string;
}

export interface CompareBenchmarkRow {
  benchmark: string;
  [dataKey: string]: string | number | null;
}

export interface CompareBenchmarkChartData {
  pairs: ModelVariantPair[];
  rows: CompareBenchmarkRow[];
  series: CompareBenchmarkSeries[];
  seriesByDataKey: Map<string, CompareBenchmarkSeries>;
}

function outputModePriority(outputMode: OutputMode): ConcreteOutputMode[] {
  return outputMode === "both" ? ["text", "json_schema"] : [outputMode];
}

function comparePassRateDesc(
  a: { passRate: number | null },
  b: { passRate: number | null }
): number {
  if (a.passRate == null && b.passRate == null) return 0;
  if (a.passRate == null) return 1;
  if (b.passRate == null) return -1;
  return b.passRate - a.passRate;
}

function passRateForModel(
  data: GitBenchData,
  modelName: string | undefined
): { percent: number | null; raw: number | null } {
  if (!modelName) return { percent: null, raw: null };
  const raw = data.model_summaries[modelName]?.pass_at_k;
  return raw == null
    ? { percent: null, raw: null }
    : { percent: Math.round(raw * 1000) / 10, raw };
}

function meanAvailable(values: Array<number | null>): number {
  const available = values.filter((value): value is number => value != null);
  if (available.length === 0) return 0;
  return (
    available.reduce((total, value) => total + value, 0) / available.length
  );
}

export function buildCompareOverallRows(
  data: GitBenchData,
  selectedModelNames: string[]
): CompareOverallRow[] {
  return pairModelVariants(selectedModelNames)
    .map((pair) => {
      const text = passRateForModel(data, pair.textModelName);
      const json = passRateForModel(data, pair.jsonModelName);
      return {
        id: pair.id,
        label: pair.label,
        pair,
        textPassRate: text.percent,
        jsonPassRate: json.percent,
        textRaw: text.raw,
        jsonRaw: json.raw,
        sortValue: meanAvailable([text.percent, json.percent]),
      };
    })
    .filter((row) => row.textPassRate != null || row.jsonPassRate != null)
    .sort(
      (a, b) => b.sortValue - a.sortValue || a.label.localeCompare(b.label)
    );
}

export function buildCompareBenchmarkData(
  data: GitBenchData,
  selectedModelNames: string[],
  outputMode: OutputMode,
  colors: string[]
): CompareBenchmarkChartData {
  const pairs = pairModelVariants(selectedModelNames);
  const series = pairs.flatMap((pair, pairIndex) =>
    visibleOutputModes(outputMode).map((mode) => ({
      pairId: pair.id,
      label: pair.label,
      outputMode: mode,
      dataKey: `series_${pairIndex}_${mode}`,
      color: colors[pairIndex % colors.length],
      modelName: mode === "text" ? pair.textModelName : pair.jsonModelName,
    }))
  );
  const rows = data.benchmarks.map((benchmark) => {
    const row: CompareBenchmarkRow = { benchmark };
    for (const item of series) {
      const cell = item.modelName
        ? data.matrix[item.modelName]?.[benchmark]
        : undefined;
      row[item.dataKey] =
        cell == null ? null : Math.round(cell.pass_at_k * 1000) / 10;
    }
    return row;
  });

  return {
    pairs,
    rows,
    series,
    seriesByDataKey: new Map(series.map((item) => [item.dataKey, item])),
  };
}

export function compareBenchmarkPairValues(
  row: CompareBenchmarkRow,
  series: CompareBenchmarkSeries[],
  pairId: string
): Partial<Record<ConcreteOutputMode, number | null>> {
  const values: Partial<Record<ConcreteOutputMode, number | null>> = {};
  for (const item of series) {
    if (item.pairId !== pairId) continue;
    const value = row[item.dataKey];
    values[item.outputMode] = typeof value === "number" ? value : null;
  }
  return values;
}

export function buildCompareReliabilityPair(
  data: GitBenchData,
  selectedGroupIds: string[],
  outputMode: OutputMode
): string[] {
  const groups = deriveModelGroups(data);
  const groupById = new Map(groups.map((group) => [group.id, group]));
  const selectedGroups = sanitizeGroupSelection(selectedGroupIds, groups);
  const modes = outputModePriority(outputMode);
  const pair: string[] = [];

  for (const groupId of selectedGroups) {
    const group = groupById.get(groupId);
    if (!group) continue;

    for (const mode of modes) {
      const effort = group.efforts
        .filter((item) => item.outputMode === mode)
        .sort(comparePassRateDesc)[0];
      if (!effort) continue;
      pair.push(effort.modelName);
      break;
    }

    if (pair.length >= 2) break;
  }

  return pair;
}
