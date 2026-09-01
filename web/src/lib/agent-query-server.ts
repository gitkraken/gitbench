import { chartData } from "./chart-data.ts";
import { attachModelPresets } from "./model-presets.ts";
import { getReportStore } from "./node-sqlite-report-store.ts";
import { ReportClientError } from "./report-client-error.ts";
import { resolveCampaignFromQuery } from "./report-api.ts";
import type { GitBenchToolDependencies } from "./agent-query-service.ts";

function missing(message: string): never {
  throw new ReportClientError(message, 404, "/api/agent/v1");
}

export function createServerAgentQueryDependencies(): GitBenchToolDependencies {
  const store = getReportStore();
  return {
    async loadSummary() {
      const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(
        store,
        {},
      );
      return {
        ...attachModelPresets(store.getSummary({ campaign_id })),
        campaign_id,
        campaign_metadata,
      };
    },
    async loadModels() {
      return { models: store.getModels() };
    },
    async loadModelResults(model, filters = {}) {
      const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(
        store,
        { model, output_mode: filters.output_mode },
      );
      const result = store.getModelResults(model, {
        benchmark: filters.benchmark,
        difficulty: filters.difficulty,
        tag: filters.tag,
        output_mode: filters.output_mode,
        campaign_id: campaign_id ?? undefined,
      });
      if (!result) missing(`Model not found: ${model}`);
      return { ...result, campaign_id, campaign_metadata };
    },
    async loadBenchmark(benchmark) {
      const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(
        store,
        { benchmark },
      );
      const result = store.getBenchmark(benchmark, { campaign_id });
      if (!result) missing(`Benchmark not found: ${benchmark}`);
      return Object.assign(result, { campaign_id, campaign_metadata });
    },
    async loadFixture(benchmark, fixture) {
      const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(
        store,
        { benchmark },
      );
      const result = store.getFixture(benchmark, fixture, { campaign_id });
      if (!result) missing(`Fixture not found: ${benchmark}/${fixture}`);
      return Object.assign(result, { campaign_id, campaign_metadata });
    },
    async loadQuadrantChart(scope = {}) {
      const { campaign_id, campaign_metadata } = resolveCampaignFromQuery(
        store,
        { benchmark: scope.benchmark },
      );
      const summary = attachModelPresets(store.getSummary({ campaign_id }));
      if (scope.benchmark) {
        const benchmark = store.getBenchmark(scope.benchmark, { campaign_id });
        if (!benchmark) missing(`Benchmark not found: ${scope.benchmark}`);
        return {
          ...chartData(
            "quadrant",
            summary,
            { type: "benchmark", benchmark: scope.benchmark },
            { benchmark },
          ),
          campaign_id,
          campaign_metadata,
        };
      }
      return {
        ...chartData("quadrant", summary),
        campaign_id,
        campaign_metadata,
      };
    },
  };
}
