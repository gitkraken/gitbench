import {
  chartData,
  type ChartKey,
  type ScopedChartSource,
} from "./chart-data.ts";
import { getReportStore } from "./node-sqlite-report-store.ts";
import {
  json,
  queryString,
  rejectUnsupportedQuery,
  resolveCampaignFromQuery,
} from "./report-api.ts";
import type { ChartScope } from "./types.ts";
import { attachModelPresets } from "./model-presets.ts";

const fixtureScopedCharts = new Set<ChartKey>([
  "cost",
  "runtime",
  "tokens",
  "quadrant",
]);

function scopedChartError(chart: ChartKey, scope: ChartScope): string | null {
  if (scope.type === "global") return null;
  if (chart === "heatmap") return "Heatmap chart does not support scoped data";
  if (scope.type === "fixture" && !fixtureScopedCharts.has(chart)) {
    return `${chart} chart does not support fixture scope`;
  }
  return null;
}

export function chartHandler(req: any, res: any, chart: ChartKey): void {
  const unsupported = rejectUnsupportedQuery(
    req.query,
    new Set(["benchmark", "fixture", "chart", "campaign"])
  );
  if (unsupported) {
    json(res, 400, { error: `Unsupported query parameter: ${unsupported}` });
    return;
  }

  const store = getReportStore();
  const benchmark = queryString(req.query.benchmark);
  const fixture = queryString(req.query.fixture);
  if (fixture && !benchmark) {
    json(res, 400, { error: "fixture scope requires a benchmark parameter" });
    return;
  }
  const scope: ChartScope = fixture
    ? { type: "fixture", benchmark: benchmark as string, fixture }
    : benchmark
      ? { type: "benchmark", benchmark }
      : { type: "global" };
  const scopeError = scopedChartError(chart, scope);
  if (scopeError) {
    json(res, 400, { error: scopeError });
    return;
  }

  const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(store, {
    campaign_id: req.query?.campaign,
    benchmark,
  });
  const summary = attachModelPresets(store.getSummary({ campaign_id }));
  const source: ScopedChartSource = {};
  if (scope.type === "benchmark") {
    const detail = store.getBenchmark(scope.benchmark, { campaign_id });
    if (!detail) {
      json(res, 404, { error: `Benchmark not found: ${scope.benchmark}` });
      return;
    }
    source.benchmark = detail;
  } else if (scope.type === "fixture") {
    const detail = store.getFixture(scope.benchmark, scope.fixture, {
      campaign_id,
    });
    if (!detail) {
      json(res, 404, {
        error: `Fixture not found: ${scope.benchmark}/${scope.fixture}`,
      });
      return;
    }
    source.fixture = detail;
    if (campaign_id) {
      source.attempts =
        store.getFixtureAttempts(scope.benchmark, scope.fixture, {
          campaign_id,
        }) ?? undefined;
    }
  }

  json(res, 200, {
    ...chartData(chart, summary, scope, source),
    campaign_id,
    campaign_metadata,
  });
}
