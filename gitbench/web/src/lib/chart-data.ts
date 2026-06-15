import type { GitBenchData } from "./types.ts";

export type ChartKey =
  | "pass-rate"
  | "cost"
  | "runtime"
  | "tokens"
  | "quadrant"
  | "heatmap";

function emptyData(summary: GitBenchData): GitBenchData {
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
        pass_at_k: modelSummary.pass_at_k,
        total_cost_usd: modelSummary.total_cost_usd,
      },
    ])
  ) as GitBenchData["model_summaries"];
}

function compactHeatmapMatrix(summary: GitBenchData) {
  return Object.fromEntries(
    summary.models.map((model) => [
      model.name,
      summary.benchmarks.map((benchmark) => {
        const cell = summary.matrix[model.name]?.[benchmark];
        return cell ? [cell.pass_at_k, cell.passed, cell.total] : null;
      }),
    ])
  );
}

export function chartData(
  chart: ChartKey,
  summary: GitBenchData,
  benchmark?: string
) {
  const data = emptyData(summary);

  switch (chart) {
    case "pass-rate":
      data.model_summaries = minimalModelSummaries(summary);
      if (benchmark) {
        data.benchmarks = [benchmark];
        data.matrix = matrixForBenchmark(summary.matrix, benchmark);
      }
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
    case "heatmap":
      return {
        models: summary.models,
        benchmarks: summary.benchmarks,
        base_model_groups: summary.base_model_groups,
        matrix: compactHeatmapMatrix(summary),
      };
  }
}
