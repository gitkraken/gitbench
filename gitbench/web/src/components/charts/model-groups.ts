import type {
  BaseModelGroup,
  GitBenchData,
  ModelInfo,
} from "../../lib/types.ts";
import { decomposeOutputTokens } from "../../lib/token-usage.ts";
import { compareReasoningLevels } from "../../lib/sort-orders.ts";

export type ModelGroupId = string;
export type OutputMode = "text" | "json_schema" | "both";
export type ConcreteOutputMode = Exclude<OutputMode, "both">;

const JSON_SCHEMA_SUFFIX = "__json_schema";

export interface ModelGroupEffort {
  groupId: ModelGroupId;
  modelName: string;
  provider: string;
  baseModel: string;
  reasoningLevel: string | null;
  outputMode: string;
  passRate: number | null;
  totalCostUsd: number | null;
}

export interface ModelGroup {
  id: ModelGroupId;
  provider: string;
  baseModel: string;
  efforts: ModelGroupEffort[];
}

export interface MetricEffort extends ModelGroupEffort {
  value: number;
  inputTokens?: number;
  outputTokens?: number;
  visibleOutputTokens?: number | null;
  reasoningTokens?: number | null;
  avgMs?: number;
  fixtureCount?: number;
}

export interface GroupedMetricModeSummary {
  outputMode: ConcreteOutputMode;
  efforts: MetricEffort[];
  minValue: number;
  maxValue: number;
  representativeValue: number;
  rangeWhisker: [number, number];
}

export interface GroupedMetricRow {
  id: ModelGroupId;
  name: ModelGroupId;
  provider: string;
  baseModel: string;
  efforts: MetricEffort[];
  modes: Partial<Record<ConcreteOutputMode, GroupedMetricModeSummary>>;
  textRepresentativeValue: number | null;
  jsonRepresentativeValue: number | null;
  textRangeWhisker: [number, number] | null;
  jsonRangeWhisker: [number, number] | null;
  minValue: number;
  maxValue: number;
  representativeValue: number;
  sortValue: number;
  textInputTokens?: number;
  textVisibleOutputTokens?: number;
  textReasoningTokens?: number;
  textHasReasoningData?: boolean;
  jsonInputTokens?: number;
  jsonVisibleOutputTokens?: number;
  jsonReasoningTokens?: number;
  jsonHasReasoningData?: boolean;
  hasReasoningData?: boolean;
}

export interface ModelVariantPair {
  id: string;
  label: string;
  textModelName?: string;
  jsonModelName?: string;
}

export type MetricExtractor = (
  effort: ModelGroupEffort,
  data: GitBenchData
) => MetricEffort | null;

type RepresentativeMetric = "min" | "max" | "median";

function median(values: number[]): number {
  const medianIndex = Math.floor(values.length / 2);
  return values.length % 2 === 0
    ? (values[medianIndex - 1] + values[medianIndex]) / 2
    : values[medianIndex];
}

function modelVariantKey(modelName: string, outputMode: string): string {
  return outputMode === "text" ? modelName : `${modelName}__${outputMode}`;
}

export function splitModelVariantKey(modelName: string): {
  canonicalModelName: string;
  outputMode: ConcreteOutputMode;
} {
  return modelName.endsWith(JSON_SCHEMA_SUFFIX)
    ? {
        canonicalModelName: modelName.slice(0, -JSON_SCHEMA_SUFFIX.length),
        outputMode: "json_schema",
      }
    : { canonicalModelName: modelName, outputMode: "text" };
}

export function canonicalModelVariantKey(modelName: string): string {
  return splitModelVariantKey(modelName).canonicalModelName;
}

export function pairModelVariants(modelNames: string[]): ModelVariantPair[] {
  const pairs = new Map<string, ModelVariantPair>();
  for (const modelName of modelNames) {
    const { canonicalModelName, outputMode } = splitModelVariantKey(modelName);
    const pair = pairs.get(canonicalModelName) ?? {
      id: canonicalModelName,
      label: canonicalModelName,
    };
    if (outputMode === "text") {
      pair.textModelName = modelName;
    } else {
      pair.jsonModelName = modelName;
    }
    pairs.set(canonicalModelName, pair);
  }
  return Array.from(pairs.values());
}

function outputModeFromVariantKey(modelName: string): ConcreteOutputMode {
  return splitModelVariantKey(modelName).outputMode;
}

function cleanModelName(modelName: string): string {
  return canonicalModelVariantKey(modelName);
}

function compareReasoningEfforts(a: MetricEffort, b: MetricEffort): number {
  return (
    compareReasoningLevels(
      String(a.reasoningLevel ?? ""),
      String(b.reasoningLevel ?? "")
    ) || a.modelName.localeCompare(b.modelName)
  );
}

export function modelGroupId(
  provider: string,
  baseModel: string
): ModelGroupId {
  return `${provider}/${baseModel}`;
}

function effortFromModelInfo(
  model: ModelInfo,
  data: GitBenchData
): ModelGroupEffort {
  const outputMode = model.output_mode ?? "text";
  const modelName = modelVariantKey(model.name, outputMode);
  const summary = data.model_summaries[modelName];
  const groupId = modelGroupId(model.provider, model.baseModel);
  return {
    groupId,
    modelName,
    provider: model.provider,
    baseModel: model.baseModel,
    reasoningLevel: model.reasoningLevel,
    outputMode,
    passRate: summary?.pass_at_k ?? null,
    totalCostUsd: summary?.total_cost_usd ?? null,
  };
}

function effortFromGroupLevel(
  group: BaseModelGroup,
  level: BaseModelGroup["levels"][number],
  data: GitBenchData
): ModelGroupEffort {
  const outputMode = outputModeFromVariantKey(level.modelName);
  const baseModelName = cleanModelName(level.modelName);
  const modelInfo = data.models.find(
    (model) =>
      model.name === baseModelName &&
      (model.output_mode ?? "text") === outputMode
  );
  const summary = data.model_summaries[level.modelName];
  const provider = modelInfo?.provider ?? group.provider;
  const baseModel = modelInfo?.baseModel ?? group.baseModel;
  return {
    groupId: modelGroupId(provider, baseModel),
    modelName: level.modelName,
    provider,
    baseModel,
    reasoningLevel: modelInfo?.reasoningLevel ?? level.level,
    outputMode,
    passRate: summary?.pass_at_k ?? level.pass_at_k ?? null,
    totalCostUsd: summary?.total_cost_usd ?? level.total_cost_usd ?? null,
  };
}

export function deriveModelGroups(data: GitBenchData): ModelGroup[] {
  if (data.base_model_groups?.length) {
    return data.base_model_groups.map((group) => {
      const efforts = group.levels.map((level) =>
        effortFromGroupLevel(group, level, data)
      );
      const first = efforts[0];
      return {
        id: modelGroupId(
          first?.provider ?? group.provider,
          first?.baseModel ?? group.baseModel
        ),
        provider: first?.provider ?? group.provider,
        baseModel: first?.baseModel ?? group.baseModel,
        efforts,
      };
    });
  }

  const groups = new Map<ModelGroupId, ModelGroup>();
  for (const model of data.models) {
    const effort = effortFromModelInfo(model, data);
    const existing = groups.get(effort.groupId);
    if (existing) {
      existing.efforts.push(effort);
    } else {
      groups.set(effort.groupId, {
        id: effort.groupId,
        provider: effort.provider,
        baseModel: effort.baseModel,
        efforts: [effort],
      });
    }
  }
  return Array.from(groups.values());
}

export function groupIdsForData(data: GitBenchData): ModelGroupId[] {
  return deriveModelGroups(data).map((group) => group.id);
}

export function sanitizeGroupSelection(
  selection: string[],
  groups: ModelGroup[]
): ModelGroupId[] {
  const groupIds = new Set(groups.map((group) => group.id));
  const modelToGroup = new Map<string, ModelGroupId>();
  for (const group of groups) {
    for (const effort of group.efforts) {
      modelToGroup.set(effort.modelName, group.id);
    }
  }

  const result: ModelGroupId[] = [];
  const seen = new Set<ModelGroupId>();
  for (const value of selection) {
    const mapped = groupIds.has(value) ? value : modelToGroup.get(value);
    if (!mapped || seen.has(mapped)) continue;
    seen.add(mapped);
    result.push(mapped);
  }
  return result;
}

export function expandGroupSelection(
  selection: string[],
  data: GitBenchData
): string[] {
  const selectedGroups = new Set(
    sanitizeGroupSelection(selection, deriveModelGroups(data))
  );
  return deriveModelGroups(data)
    .filter((group) => selectedGroups.has(group.id))
    .flatMap((group) => group.efforts.map((effort) => effort.modelName));
}

export function passRateMetric(effort: ModelGroupEffort): MetricEffort | null {
  if (effort.passRate == null) return null;
  return { ...effort, value: effort.passRate * 100 };
}

export function benchPassRateMetric(benchName: string): MetricExtractor {
  return (
    effort: ModelGroupEffort,
    data: GitBenchData
  ): MetricEffort | null => {
    const cell = data.matrix[effort.modelName]?.[benchName];
    if (!cell) return null;
    return { ...effort, value: cell.pass_at_k * 100 };
  };
}

export function costMetric(effort: ModelGroupEffort): MetricEffort | null {
  if (effort.totalCostUsd == null) return null;
  return { ...effort, value: effort.totalCostUsd };
}

export function runtimeMetric(
  effort: ModelGroupEffort,
  data: GitBenchData
): MetricEffort | null {
  const runtime = data.model_runtimes[effort.modelName];
  if (!runtime) return null;
  return {
    ...effort,
    value: runtime.total_ms / 1000,
    avgMs: runtime.avg_ms,
    fixtureCount: runtime.fixture_count,
  };
}

export function tokenMetric(
  effort: ModelGroupEffort,
  data: GitBenchData
): MetricEffort {
  const tokens = data.model_token_summaries[effort.modelName] ?? {
    input_tokens: 0,
    output_tokens: 0,
    total_tokens: 0,
    reasoning_tokens: null,
  };
  const decomposition = decomposeOutputTokens(
    tokens.output_tokens,
    tokens.reasoning_tokens
  );
  return {
    ...effort,
    value: tokens.total_tokens,
    inputTokens: tokens.input_tokens,
    outputTokens: decomposition.totalOutputTokens ?? undefined,
    visibleOutputTokens: decomposition.visibleOutputTokens,
    reasoningTokens: decomposition.reasoningTokens,
  };
}

function closestRepresentativeEffort(
  summary: GroupedMetricModeSummary
): MetricEffort {
  return summary.efforts.reduce((closest, effort) => {
    const distance = Math.abs(effort.value - summary.representativeValue);
    const closestDistance = Math.abs(
      closest.value - summary.representativeValue
    );
    if (distance < closestDistance) return effort;
    if (distance === closestDistance && effort.value < closest.value) {
      return effort;
    }
    return closest;
  });
}

function applyTokenSegments(
  row: GroupedMetricRow,
  mode: ConcreteOutputMode
): void {
  const summary = row.modes[mode];
  if (!summary) return;

  const representative = closestRepresentativeEffort(summary);
  summary.representativeValue = representative.value;
  summary.rangeWhisker = [
    representative.value - summary.minValue,
    summary.maxValue - representative.value,
  ];

  const inputTokens = representative.inputTokens ?? 0;
  const visibleOutputTokens = representative.visibleOutputTokens ?? 0;
  const reasoningTokens = representative.reasoningTokens ?? 0;
  const hasReasoningData =
    representative.reasoningLevel != null &&
    representative.reasoningTokens != null;

  if (mode === "text") {
    row.textRepresentativeValue = representative.value;
    row.textRangeWhisker = summary.rangeWhisker;
    row.textInputTokens = inputTokens;
    row.textVisibleOutputTokens = visibleOutputTokens;
    row.textReasoningTokens = reasoningTokens;
    row.textHasReasoningData = hasReasoningData;
  } else {
    row.jsonRepresentativeValue = representative.value;
    row.jsonRangeWhisker = summary.rangeWhisker;
    row.jsonInputTokens = inputTokens;
    row.jsonVisibleOutputTokens = visibleOutputTokens;
    row.jsonReasoningTokens = reasoningTokens;
    row.jsonHasReasoningData = hasReasoningData;
  }
  row.hasReasoningData = row.hasReasoningData || hasReasoningData;
}

export function buildTokenUsageRows(
  data: GitBenchData,
  selectedGroupIds: string[],
  outputMode: OutputMode
): GroupedMetricRow[] {
  const rows = buildGroupedMetricRows(
    data,
    selectedGroupIds,
    tokenMetric,
    "median",
    outputMode
  );
  for (const row of rows) {
    applyTokenSegments(row, "text");
    applyTokenSegments(row, "json_schema");
    row.sortValue = getGroupedMetricSortValue(row, outputMode);
    row.representativeValue = row.sortValue;
  }
  return rows;
}

export function buildGroupedMetricRows(
  data: GitBenchData,
  selectedGroupIds: string[],
  extractor: MetricExtractor,
  representative: RepresentativeMetric,
  outputMode?: OutputMode
): GroupedMetricRow[] {
  const selected = new Set(
    sanitizeGroupSelection(selectedGroupIds, deriveModelGroups(data))
  );
  return deriveModelGroups(data)
    .filter((group) => selected.has(group.id))
    .map((group) => {
      const visibleModes = visibleOutputModes(outputMode ?? "both");
      const modes: Partial<
        Record<ConcreteOutputMode, GroupedMetricModeSummary>
      > = {};

      for (const mode of visibleModes) {
        const efforts = group.efforts
          .filter((effort) => effort.outputMode === mode)
          .map((effort) => extractor(effort, data))
          .filter((effort): effort is MetricEffort => effort !== null)
          .sort(compareReasoningEfforts);
        if (efforts.length === 0) continue;

        const values = efforts
          .map((effort) => effort.value)
          .sort((a, b) => a - b);
        const uniqueValues = Array.from(new Set(values));
        const minValue = values[0];
        const maxValue = values[values.length - 1];
        const medianValue = median(uniqueValues);
        const representativeValue =
          representative === "min"
            ? minValue
            : representative === "max"
            ? maxValue
            : medianValue;
        modes[mode] = {
          outputMode: mode,
          efforts,
          minValue,
          maxValue,
          representativeValue,
          rangeWhisker: [
            representativeValue - minValue,
            maxValue - representativeValue,
          ],
        };
      }

      const summaries = visibleModes
        .map((mode) => modes[mode])
        .filter(
          (summary): summary is GroupedMetricModeSummary =>
            summary !== undefined
        );
      if (summaries.length === 0) return null;

      const row = {
        id: group.id,
        name: group.id,
        provider: group.provider,
        baseModel: group.baseModel,
        efforts: summaries.flatMap((summary) => summary.efforts),
        modes,
        textRepresentativeValue: modes.text?.representativeValue ?? null,
        jsonRepresentativeValue: modes.json_schema?.representativeValue ?? null,
        textRangeWhisker: modes.text?.rangeWhisker ?? null,
        jsonRangeWhisker: modes.json_schema?.rangeWhisker ?? null,
        minValue: Math.min(...summaries.map((summary) => summary.minValue)),
        maxValue: Math.max(...summaries.map((summary) => summary.maxValue)),
        representativeValue: 0,
        sortValue: 0,
      };
      row.sortValue = getGroupedMetricSortValue(
        row as GroupedMetricRow,
        outputMode ?? "both"
      );
      row.representativeValue = row.sortValue;
      return row;
    })
    .filter((row): row is GroupedMetricRow => row !== null);
}

export function visibleOutputModes(
  outputMode: OutputMode
): ConcreteOutputMode[] {
  return outputMode === "both" ? ["text", "json_schema"] : [outputMode];
}

export function outputModeLabel(outputMode: ConcreteOutputMode): string {
  return outputMode === "text" ? "Text" : "JSON";
}

export function getGroupedMetricSortValue(
  row: GroupedMetricRow,
  outputMode: OutputMode
): number {
  const values = visibleOutputModes(outputMode)
    .map((mode) => row.modes[mode]?.representativeValue)
    .filter((value): value is number => value !== undefined);
  if (values.length === 0) return 0;
  return values.reduce((total, value) => total + value, 0) / values.length;
}

export function getAvailableOutputModes(data: GitBenchData): Set<string> {
  return new Set(data.models.map((m) => m.output_mode ?? "text"));
}

export function filterEffortsByOutputMode(
  efforts: ModelGroupEffort[],
  mode: OutputMode
): ModelGroupEffort[] {
  if (mode === "both") return efforts;
  return efforts.filter((e) => e.outputMode === mode);
}

/**
 * Expand group selection to model names, optionally filtering by output mode.
 * When mode is "both", all variants are included.
 */
export function expandGroupSelectionWithMode(
  selection: string[],
  data: GitBenchData,
  outputMode: OutputMode = "text"
): string[] {
  const groups = deriveModelGroups(data);
  const selectedGroups = new Set(sanitizeGroupSelection(selection, groups));
  return groups
    .filter((group) => selectedGroups.has(group.id))
    .flatMap((group) => {
      const filtered = filterEffortsByOutputMode(group.efforts, outputMode);
      return filtered.map((effort) => effort.modelName);
    });
}
