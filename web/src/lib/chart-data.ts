import type {
  BenchmarkDetail,
  FixtureAttempts,
  FixtureDetail,
  RawAttempt,
} from "./report-store.ts";
import type {
  BaseModelGroup,
  CellData,
  ChartScope,
  FixtureQualityMetric,
  FixtureResult,
  GitBenchData,
  ModelInfo,
  ModelRuntimeSummary,
  ModelSummary,
  ModelTokenSummary,
} from "./types.ts";

export type ChartKey =
  | "pass-rate"
  | "cost"
  | "runtime"
  | "tokens"
  | "quadrant"
  | "heatmap";

export interface HeatmapChartData {
  models: GitBenchData["models"];
  benchmarks: GitBenchData["benchmarks"];
  base_model_groups: GitBenchData["base_model_groups"];
  matrix: Record<string, ([number, number, number] | null)[]>;
}

export interface ScopedChartSource {
  benchmark?: BenchmarkDetail;
  fixture?: FixtureDetail;
  attempts?: FixtureAttempts;
}

type ChartScopeInput = ChartScope | string | undefined;

interface ScopedMetricRow {
  modelKey: string;
  benchmark: string;
  fixtureId: string;
  passed: boolean | null;
  similarity: number | null;
  error: string | null;
  status?: string;
  inputTokens: number | null;
  outputTokens: number | null;
  totalTokens: number | null;
  reasoningTokens: number | null;
  costUsd: number | null;
  apiDurationMs: number | null;
}

interface RowAggregate {
  modelKey: string;
  totalCostUsd: number;
  costCount: number;
  totalMs: number;
  minMs: number;
  maxMs: number;
  runtimeCount: number;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  reasoningTokens: number;
  reasoningTokenCount: number;
  validCount: number;
  passingCount: number;
  similarityTotal: number;
  similarityCount: number;
  hasIntermediateSimilarity: boolean;
}

function emptyData(
  summary: GitBenchData,
  scope: ChartScope = { type: "global" }
): GitBenchData {
  return {
    models: summary.models,
    benchmarks: [],
    model_summaries: {},
    model_runtimes: {},
    model_token_summaries: {},
    matrix: {},
    fixtures: {},
    fixture_index: {},
    runs_meta: [],
    base_model_groups: summary.base_model_groups,
    chart_scope: scope,
  };
}

function matrixForBenchmark(
  matrix: GitBenchData["matrix"],
  benchmark: string
): GitBenchData["matrix"] {
  const result: GitBenchData["matrix"] = {};
  for (const [model, byBenchmark] of Object.entries(matrix)) {
    const cell = byBenchmark[benchmark];
    if (cell) result[model] = { [benchmark]: cell };
  }
  return result;
}

function minimalModelSummaries(
  summary: GitBenchData
): GitBenchData["model_summaries"] {
  return Object.fromEntries(
    Object.entries(summary.model_summaries).map(([model, modelSummary]) => [
      model,
      {
        total_runs: modelSummary.total_runs,
        total_fixtures: modelSummary.total_fixtures,
        total_passed: modelSummary.total_passed,
        pass_at_k: modelSummary.pass_at_k,
        total_cost_usd: modelSummary.total_cost_usd,
        avg_cost_usd: modelSummary.avg_cost_usd,
        total_valid_attempts: modelSummary.total_valid_attempts,
        total_passing_attempts: modelSummary.total_passing_attempts,
      },
    ])
  ) as GitBenchData["model_summaries"];
}

function modelModeKey(modelName: string, outputMode: string): string {
  return outputMode === "text" ? modelName : `${modelName}__${outputMode}`;
}

function compactHeatmapMatrix(
  summary: GitBenchData
): HeatmapChartData["matrix"] {
  return Object.fromEntries(
    summary.models.map((model) => [
      modelModeKey(model.name, model.output_mode ?? "text"),
      summary.benchmarks.map((benchmark) => {
        const cell =
          summary.matrix[
            modelModeKey(model.name, model.output_mode ?? "text")
          ]?.[benchmark];
        if (!cell) return null;
        return [cell.pass_at_k, cell.passed, cell.total];
      }),
    ])
  );
}

function normalizeScope(scope: ChartScopeInput): ChartScope {
  if (!scope) return { type: "global" };
  if (typeof scope === "string") {
    return { type: "benchmark", benchmark: scope };
  }
  return scope;
}

function modelInfoKey(model: ModelInfo): string {
  return modelModeKey(model.name, model.output_mode ?? "text");
}

function filterModels(summary: GitBenchData, modelKeys: Set<string>): ModelInfo[] {
  if (modelKeys.size === 0) return [];
  return summary.models.filter((model) => modelKeys.has(modelInfoKey(model)));
}

function scopedBaseModelGroups(
  summary: GitBenchData,
  modelSummaries: GitBenchData["model_summaries"],
  modelKeys: Set<string>
): BaseModelGroup[] {
  return summary.base_model_groups
    .map((group) => ({
      ...group,
      levels: group.levels
        .filter((level) => modelKeys.has(level.modelName))
        .map((level) => {
          const scopedSummary = modelSummaries[level.modelName];
          return {
            ...level,
            pass_at_k: scopedSummary?.pass_at_k ?? 0,
            total_cost_usd: scopedSummary?.total_cost_usd ?? null,
          };
        }),
    }))
    .filter((group) => group.levels.length > 0);
}

function fixtureRowFromResult(
  modelKey: string,
  benchmark: string,
  result: FixtureResult
): ScopedMetricRow {
  return {
    modelKey,
    benchmark,
    fixtureId: result.fixture_id,
    passed: result.passed,
    similarity: result.similarity,
    error: result.error,
    inputTokens: result.input_tokens,
    outputTokens: result.output_tokens,
    totalTokens: result.total_tokens,
    reasoningTokens: result.reasoning_tokens,
    costUsd: result.cost_usd,
    apiDurationMs: result.api_duration_ms,
  };
}

function fixtureRowFromAttempt(attempt: RawAttempt): ScopedMetricRow {
  return {
    modelKey: modelModeKey(attempt.model_name, attempt.output_mode),
    benchmark: attempt.benchmark_name,
    fixtureId: attempt.fixture_id,
    passed: attempt.passed,
    similarity: attempt.similarity,
    error: attempt.error,
    status: attempt.status,
    inputTokens: attempt.input_tokens,
    outputTokens: attempt.output_tokens,
    totalTokens: attempt.total_tokens,
    reasoningTokens: attempt.reasoning_tokens,
    costUsd: attempt.cost_usd,
    apiDurationMs: attempt.api_duration_ms,
  };
}

function rowsFromBenchmarkDetail(detail?: BenchmarkDetail): ScopedMetricRow[] {
  if (!detail) return [];
  const rows: ScopedMetricRow[] = [];
  for (const [modelKey, byBenchmark] of Object.entries(detail.results)) {
    for (const result of byBenchmark[detail.benchmark] ?? []) {
      rows.push(fixtureRowFromResult(modelKey, detail.benchmark, result));
    }
  }
  return rows;
}

function rowsFromFixtureDetail(detail?: FixtureDetail): ScopedMetricRow[] {
  if (!detail) return [];
  return detail.outputs.map((result) =>
    fixtureRowFromResult(result.model, detail.fixture.benchmark, result)
  );
}

function rowsFromFixtureAttempts(attempts?: FixtureAttempts): ScopedMetricRow[] {
  if (!attempts) return [];
  return attempts.attempts.map(fixtureRowFromAttempt);
}

function emptyAggregate(modelKey: string): RowAggregate {
  return {
    modelKey,
    totalCostUsd: 0,
    costCount: 0,
    totalMs: 0,
    minMs: Number.POSITIVE_INFINITY,
    maxMs: Number.NEGATIVE_INFINITY,
    runtimeCount: 0,
    inputTokens: 0,
    outputTokens: 0,
    totalTokens: 0,
    reasoningTokens: 0,
    reasoningTokenCount: 0,
    validCount: 0,
    passingCount: 0,
    similarityTotal: 0,
    similarityCount: 0,
    hasIntermediateSimilarity: false,
  };
}

function isValidQualityRow(row: ScopedMetricRow): boolean {
  if (row.status) return row.status === "valid_pass" || row.status === "valid_fail";
  return row.error == null;
}

function aggregateRows(rows: ScopedMetricRow[]): Map<string, RowAggregate> {
  const aggregates = new Map<string, RowAggregate>();
  for (const row of rows) {
    const aggregate = aggregates.get(row.modelKey) ?? emptyAggregate(row.modelKey);
    aggregates.set(row.modelKey, aggregate);

    if (row.costUsd != null) {
      aggregate.totalCostUsd += row.costUsd;
      aggregate.costCount += 1;
    }
    if (row.apiDurationMs != null) {
      aggregate.totalMs += row.apiDurationMs;
      aggregate.minMs = Math.min(aggregate.minMs, row.apiDurationMs);
      aggregate.maxMs = Math.max(aggregate.maxMs, row.apiDurationMs);
      aggregate.runtimeCount += 1;
    }
    if (row.inputTokens != null) aggregate.inputTokens += row.inputTokens;
    if (row.outputTokens != null) aggregate.outputTokens += row.outputTokens;
    const totalTokens =
      row.totalTokens ??
      (row.inputTokens != null || row.outputTokens != null
        ? (row.inputTokens ?? 0) + (row.outputTokens ?? 0)
        : null);
    if (totalTokens != null) aggregate.totalTokens += totalTokens;
    if (row.reasoningTokens != null) {
      aggregate.reasoningTokens += row.reasoningTokens;
      aggregate.reasoningTokenCount += 1;
    }

    if (!isValidQualityRow(row)) continue;
    aggregate.validCount += 1;
    if (row.passed) aggregate.passingCount += 1;
    if (row.similarity != null) {
      aggregate.similarityTotal += row.similarity;
      aggregate.similarityCount += 1;
      if (row.similarity > 0 && row.similarity < 1) {
        aggregate.hasIntermediateSimilarity = true;
      }
    }
  }
  return aggregates;
}

function addRuntimeAndTokenSummaries(
  data: GitBenchData,
  aggregates: Map<string, RowAggregate>
): void {
  for (const [modelKey, aggregate] of aggregates) {
    if (aggregate.runtimeCount > 0) {
      data.model_runtimes[modelKey] = {
        total_ms: aggregate.totalMs,
        avg_ms: aggregate.totalMs / aggregate.runtimeCount,
        min_ms: aggregate.minMs,
        max_ms: aggregate.maxMs,
        fixture_count: aggregate.runtimeCount,
      } satisfies ModelRuntimeSummary;
    }
    data.model_token_summaries[modelKey] = {
      input_tokens: aggregate.inputTokens,
      output_tokens: aggregate.outputTokens,
      total_tokens: aggregate.totalTokens,
      reasoning_tokens:
        aggregate.reasoningTokenCount > 0 ? aggregate.reasoningTokens : null,
    } satisfies ModelTokenSummary;
  }
}

function ensureModelSummary(
  summaries: GitBenchData["model_summaries"],
  modelKey: string
): ModelSummary {
  summaries[modelKey] = summaries[modelKey] ?? {
    total_runs: 0,
    total_fixtures: 0,
    total_passed: 0,
    pass_at_k: 0,
    total_cost_usd: null,
    avg_cost_usd: null,
  };
  return summaries[modelKey];
}

function applyCostSummaries(
  summaries: GitBenchData["model_summaries"],
  aggregates: Map<string, RowAggregate>
): void {
  for (const [modelKey, aggregate] of aggregates) {
    const summary = ensureModelSummary(summaries, modelKey);
    summary.total_cost_usd =
      aggregate.costCount > 0 ? aggregate.totalCostUsd : null;
    summary.avg_cost_usd =
      aggregate.costCount > 0 ? aggregate.totalCostUsd / aggregate.costCount : null;
  }
}

function benchmarkScopedData(
  summary: GitBenchData,
  benchmark: string,
  source?: ScopedChartSource
): GitBenchData {
  const scope: ChartScope = { type: "benchmark", benchmark };
  const data = emptyData(summary, scope);
  data.benchmarks = [benchmark];

  const modelKeys = new Set<string>();
  if (source?.benchmark) {
    for (const row of source.benchmark.leaderboard) {
      modelKeys.add(row.model);
      data.model_summaries[row.model] = {
        total_runs: 0,
        total_fixtures: row.total,
        total_passed: row.passed,
        pass_at_k: row.pass_at_k,
        total_cost_usd: null,
        avg_cost_usd: null,
        total_valid_attempts: row.total,
        total_passing_attempts: row.passed,
      };
      data.matrix[row.model] = {
        [benchmark]: {
          pass_at_k: row.pass_at_k,
          total: row.total,
          passed: row.passed,
          avg_similarity: row.avg_similarity,
        },
      };
    }
  } else {
    data.matrix = matrixForBenchmark(summary.matrix, benchmark);
    for (const [modelKey, byBenchmark] of Object.entries(data.matrix)) {
      const cell = byBenchmark[benchmark];
      if (!cell) continue;
      modelKeys.add(modelKey);
      data.model_summaries[modelKey] = {
        total_runs: 0,
        total_fixtures: cell.total,
        total_passed: cell.passed,
        pass_at_k: cell.pass_at_k,
        total_cost_usd: null,
        avg_cost_usd: null,
        total_valid_attempts: cell.total,
        total_passing_attempts: cell.passed,
      };
    }
  }

  const aggregates = aggregateRows(rowsFromBenchmarkDetail(source?.benchmark));
  for (const modelKey of aggregates.keys()) modelKeys.add(modelKey);
  applyCostSummaries(data.model_summaries, aggregates);
  addRuntimeAndTokenSummaries(data, aggregates);

  data.models = filterModels(summary, modelKeys);
  data.base_model_groups = scopedBaseModelGroups(
    summary,
    data.model_summaries,
    modelKeys
  );
  return data;
}

function chooseFixtureQualityMetric(
  rows: ScopedMetricRow[],
  aggregates: Map<string, RowAggregate>
): FixtureQualityMetric {
  const hasCampaignRows = rows.some((row) => row.status != null);
  const hasRepeatedAttempts =
    hasCampaignRows &&
    Array.from(aggregates.values()).some((aggregate) => aggregate.validCount > 1);
  if (hasRepeatedAttempts) {
    return { kind: "repeated_success", label: "Success (%)" };
  }
  const hasIntermediateSimilarity = Array.from(aggregates.values()).some(
    (aggregate) => aggregate.hasIntermediateSimilarity
  );
  if (hasIntermediateSimilarity) {
    return { kind: "similarity", label: "Similarity (%)" };
  }
  return { kind: "binary_success", label: "Success (%)" };
}

function qualityValueForAggregate(
  aggregate: RowAggregate,
  metric: FixtureQualityMetric
): number | null {
  if (metric.kind === "similarity") {
    return aggregate.similarityCount > 0
      ? aggregate.similarityTotal / aggregate.similarityCount
      : null;
  }
  return aggregate.validCount > 0
    ? aggregate.passingCount / aggregate.validCount
    : null;
}

function fixtureScopedData(
  summary: GitBenchData,
  benchmark: string,
  fixture: string,
  source?: ScopedChartSource
): GitBenchData {
  const scope: ChartScope = { type: "fixture", benchmark, fixture };
  const rows = source?.attempts?.attempts.length
    ? rowsFromFixtureAttempts(source.attempts)
    : rowsFromFixtureDetail(source?.fixture);
  const aggregates = aggregateRows(rows);
  const qualityMetric = chooseFixtureQualityMetric(rows, aggregates);

  const data = emptyData(summary, scope);
  data.benchmarks = [benchmark];
  data.fixture_quality_metric = qualityMetric;

  const modelKeys = new Set<string>(aggregates.keys());
  for (const [modelKey, aggregate] of aggregates) {
    const quality = qualityValueForAggregate(aggregate, qualityMetric);
    const passRate = quality ?? 0;
    data.model_summaries[modelKey] = {
      total_runs: aggregate.validCount,
      total_fixtures: aggregate.validCount > 0 ? 1 : 0,
      total_passed: aggregate.passingCount > 0 ? 1 : 0,
      pass_at_k: passRate,
      total_cost_usd: aggregate.costCount > 0 ? aggregate.totalCostUsd : null,
      avg_cost_usd:
        aggregate.costCount > 0 ? aggregate.totalCostUsd / aggregate.costCount : null,
      total_valid_attempts: aggregate.validCount,
      total_passing_attempts: aggregate.passingCount,
    };
    data.matrix[modelKey] = {
      [benchmark]: {
        pass_at_k: passRate,
        total: aggregate.validCount,
        passed: aggregate.passingCount,
        avg_similarity:
          aggregate.similarityCount > 0
            ? aggregate.similarityTotal / aggregate.similarityCount
            : 0,
      } satisfies CellData,
    };
  }
  addRuntimeAndTokenSummaries(data, aggregates);

  data.models = filterModels(summary, modelKeys);
  data.base_model_groups = scopedBaseModelGroups(
    summary,
    data.model_summaries,
    modelKeys
  );
  return data;
}

export function chartData(
  chart: Exclude<ChartKey, "heatmap">,
  summary: GitBenchData,
  scope?: ChartScopeInput,
  source?: ScopedChartSource
): GitBenchData;
export function chartData(
  chart: "heatmap",
  summary: GitBenchData,
  scope?: ChartScopeInput,
  source?: ScopedChartSource
): HeatmapChartData;
export function chartData(
  chart: ChartKey,
  summary: GitBenchData,
  scope?: ChartScopeInput,
  source?: ScopedChartSource
): GitBenchData | HeatmapChartData;
export function chartData(
  chart: ChartKey,
  summary: GitBenchData,
  scope?: ChartScopeInput,
  source?: ScopedChartSource
): GitBenchData | HeatmapChartData {
  const resolvedScope = normalizeScope(scope);

  if (chart === "heatmap") {
    return {
      models: summary.models,
      benchmarks: summary.benchmarks,
      base_model_groups: summary.base_model_groups,
      matrix: compactHeatmapMatrix(summary),
    };
  }

  if (resolvedScope.type === "benchmark") {
    return benchmarkScopedData(summary, resolvedScope.benchmark, source);
  }
  if (resolvedScope.type === "fixture") {
    return fixtureScopedData(
      summary,
      resolvedScope.benchmark,
      resolvedScope.fixture,
      source
    );
  }

  const data = emptyData(summary, resolvedScope);

  switch (chart) {
    case "pass-rate":
      data.model_summaries = minimalModelSummaries(summary);
      return data;
    case "cost":
      data.model_summaries = minimalModelSummaries(summary);
      return data;
    case "runtime":
      data.model_summaries = minimalModelSummaries(summary);
      data.model_runtimes = summary.model_runtimes;
      return data;
    case "tokens":
      data.model_summaries = minimalModelSummaries(summary);
      data.model_token_summaries = summary.model_token_summaries;
      return data;
    case "quadrant":
      data.model_summaries = minimalModelSummaries(summary);
      data.model_runtimes = summary.model_runtimes;
      data.model_token_summaries = summary.model_token_summaries;
      return data;
  }
}
