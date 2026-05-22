import type {
  BaseModelGroup,
  FixtureResult,
  GitBenchData,
  ModelInfo,
} from "@/lib/types";

export type ModelGroupId = string;

export interface ModelGroupEffort {
  groupId: ModelGroupId;
  modelName: string;
  provider: string;
  baseModel: string;
  reasoningLevel: string | null;
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
  avgMs?: number;
  fixtureCount?: number;
}

export interface GroupedMetricRow {
  id: ModelGroupId;
  name: ModelGroupId;
  provider: string;
  baseModel: string;
  efforts: MetricEffort[];
  minValue: number;
  maxValue: number;
  representativeValue: number;
  representativeEffort: MetricEffort;
  range: [number, number];
}

export type MetricExtractor = (
  effort: ModelGroupEffort,
  data: GitBenchData
) => MetricEffort | null;

const REASONING_LEVEL_ORDER = new Map<string, number>([
  ["", 0],
  ["none", 0],
  ["default", 0],
  ["low", 1],
  ["medium", 2],
  ["high", 3],
  ["xhigh", 4],
  ["max", 5],
]);

function compareReasoningEfforts(a: MetricEffort, b: MetricEffort): number {
  const aLevel = String(a.reasoningLevel ?? "").toLowerCase();
  const bLevel = String(b.reasoningLevel ?? "").toLowerCase();
  const aOrder = REASONING_LEVEL_ORDER.get(aLevel) ?? Number.MAX_SAFE_INTEGER;
  const bOrder = REASONING_LEVEL_ORDER.get(bLevel) ?? Number.MAX_SAFE_INTEGER;
  if (aOrder !== bOrder) return aOrder - bOrder;
  if (aLevel !== bLevel) return aLevel.localeCompare(bLevel);
  return a.modelName.localeCompare(b.modelName);
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
  const summary = data.model_summaries[model.name];
  const groupId = modelGroupId(model.provider, model.baseModel);
  return {
    groupId,
    modelName: model.name,
    provider: model.provider,
    baseModel: model.baseModel,
    reasoningLevel: model.reasoningLevel,
    passRate: summary?.pass_at_k ?? null,
    totalCostUsd: summary?.total_cost_usd ?? null,
  };
}

function effortFromGroupLevel(
  group: BaseModelGroup,
  level: BaseModelGroup["levels"][number],
  data: GitBenchData
): ModelGroupEffort {
  const modelInfo = data.models.find((model) => model.name === level.modelName);
  const summary = data.model_summaries[level.modelName];
  const provider = modelInfo?.provider ?? group.provider;
  const baseModel = modelInfo?.baseModel ?? group.baseModel;
  return {
    groupId: modelGroupId(provider, baseModel),
    modelName: level.modelName,
    provider,
    baseModel,
    reasoningLevel: modelInfo?.reasoningLevel ?? level.level,
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

function sumFixtureTokens(
  fixtures: Record<string, FixtureResult[]> | undefined
) {
  let total = 0;
  let input = 0;
  let output = 0;
  if (!fixtures) return { total, input, output };

  for (const fixtureRuns of Object.values(fixtures)) {
    for (const fixture of fixtureRuns) {
      total += fixture.total_tokens ?? 0;
      input += fixture.input_tokens ?? 0;
      output += fixture.output_tokens ?? 0;
    }
  }

  return { total, input, output };
}

export function tokenMetric(
  effort: ModelGroupEffort,
  data: GitBenchData
): MetricEffort {
  const tokens = sumFixtureTokens(data.fixtures[effort.modelName]);
  return {
    ...effort,
    value: tokens.total,
    inputTokens: tokens.input,
    outputTokens: tokens.output,
  };
}

export function buildGroupedMetricRows(
  data: GitBenchData,
  selectedGroupIds: string[],
  extractor: MetricExtractor,
  representative: "min" | "max"
): GroupedMetricRow[] {
  const selected = new Set(
    sanitizeGroupSelection(selectedGroupIds, deriveModelGroups(data))
  );
  return deriveModelGroups(data)
    .filter((group) => selected.has(group.id))
    .map((group) => {
      const efforts = group.efforts
        .map((effort) => extractor(effort, data))
        .filter((effort): effort is MetricEffort => effort !== null)
        .sort(compareReasoningEfforts);
      if (efforts.length === 0) return null;
      const values = efforts.map((effort) => effort.value);
      const minValue = Math.min(...values);
      const maxValue = Math.max(...values);
      const representativeValue =
        representative === "min" ? minValue : maxValue;
      const representativeEffort =
        efforts.find((effort) => effort.value === representativeValue) ??
        efforts[0];
      return {
        id: group.id,
        name: group.id,
        provider: group.provider,
        baseModel: group.baseModel,
        efforts,
        minValue,
        maxValue,
        representativeValue,
        representativeEffort,
        range: [minValue, maxValue] as [number, number],
      };
    })
    .filter((row): row is GroupedMetricRow => row !== null);
}
