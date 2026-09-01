import type {
  BenchmarkDetail,
  CampaignListItem,
  FixtureAttempts,
  FixtureDetail,
  ModelResultsFilters,
  RawAttempt,
} from "@/lib/report-store";
import type { HeatmapChartData } from "@/lib/chart-data";
import type { CampaignAwareGitBenchData, FixtureResult } from "@/lib/types";

export class ReportClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly url: string,
  ) {
    super(message);
    this.name = "ReportClientError";
  }
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    throw new ReportClientError(
      `Failed to load ${url}: ${response.status}`,
      response.status,
      url,
    );
  }
  return response.json() as Promise<T>;
}

export interface CampaignsResponse {
  campaigns: CampaignListItem[];
}

export interface CampaignResponse {
  campaign: CampaignListItem;
}

export interface RawAttemptsResponse {
  campaign_id: string;
  publishable: boolean;
  attempts: RawAttempt[];
}

export interface CampaignAwareResponse {
  campaign_id: string | null;
  campaign_metadata: CampaignAwareGitBenchData["campaign_metadata"];
}

export interface ModelResultsResponse extends CampaignAwareResponse {
  model: string;
  results: Record<string, FixtureResult[]>;
}

export type CampaignAwareHeatmapChartData = HeatmapChartData &
  CampaignAwareResponse;

export function loadCampaigns(
  filters: Record<string, string> = {},
): Promise<CampaignsResponse> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  const suffix = params.size ? `?${params}` : "";
  return getJson<CampaignsResponse>(`/api/campaigns${suffix}`);
}

export function loadCampaign(campaignId: string): Promise<CampaignResponse> {
  return getJson<CampaignResponse>(
    `/api/campaigns/${encodeURIComponent(campaignId)}`,
  );
}

export function loadRawAttempts(
  campaignId: string,
  options: {
    fixture_id?: string;
    limit?: number;
    offset?: number;
    include_output?: boolean;
  } = {},
): Promise<RawAttemptsResponse> {
  const params = new URLSearchParams();
  if (options.fixture_id) params.set("fixture_id", options.fixture_id);
  if (options.limit !== undefined) params.set("limit", String(options.limit));
  if (options.offset !== undefined)
    params.set("offset", String(options.offset));
  if (options.include_output) params.set("include_output", "true");
  const suffix = params.size ? `?${params}` : "";
  return getJson<RawAttemptsResponse>(
    `/api/campaigns/${encodeURIComponent(campaignId)}/raw-attempts${suffix}`,
  );
}

export function loadRawAttemptByIdentity(
  campaignId: string,
  identity: {
    trial_index: number;
    model_name: string;
    output_mode: string;
    fixture_id: string;
  },
  options: { include_output?: boolean } = {},
): Promise<{ campaign_id: string; attempt: RawAttempt }> {
  const params = new URLSearchParams();
  if (options.include_output) params.set("include_output", "true");
  const suffix = params.size ? `?${params}` : "";
  const path = [
    encodeURIComponent(String(identity.trial_index)),
    encodeURIComponent(identity.model_name),
    encodeURIComponent(identity.output_mode),
    encodeURIComponent(identity.fixture_id),
  ].join("/");
  return getJson<{ campaign_id: string; attempt: RawAttempt }>(
    `/api/campaigns/${encodeURIComponent(campaignId)}/attempts/${path}${suffix}`,
  );
}

export function getSelectedCampaignId(): string | null {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get("campaign");
}

function loadCampaignAwareData(
  path: string,
  params: Record<string, string | undefined> = {},
): string {
  const campaignId = getSelectedCampaignId();
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) query.set(key, value);
  }
  if (campaignId) query.set("campaign", campaignId);
  const suffix = query.size ? `?${query.toString()}` : "";
  return `${path}${suffix}`;
}

export function loadSummary(
  signal?: AbortSignal,
): Promise<CampaignAwareGitBenchData> {
  return getJson<CampaignAwareGitBenchData>(
    loadCampaignAwareData("/api/summary"),
    signal,
  );
}

function loadChartData(
  chart: "pass-rate" | "cost" | "runtime" | "tokens" | "quadrant",
  params: ChartScopeParams = {},
  signal?: AbortSignal,
): Promise<CampaignAwareGitBenchData> {
  return getJson<CampaignAwareGitBenchData>(
    loadCampaignAwareData(`/api/charts/${chart}`, { ...params }),
    signal,
  );
}

export function loadPassRateChart(
  benchmark?: string,
): Promise<CampaignAwareGitBenchData> {
  return loadChartData("pass-rate", { benchmark });
}

export interface ChartScopeParams {
  benchmark?: string;
  fixture?: string;
}

export function loadCostChart(
  scope: ChartScopeParams = {},
): Promise<CampaignAwareGitBenchData> {
  return loadChartData("cost", scope);
}

export function loadRuntimeChart(
  scope: ChartScopeParams = {},
): Promise<CampaignAwareGitBenchData> {
  return loadChartData("runtime", scope);
}

export function loadTokenChart(
  scope: ChartScopeParams = {},
): Promise<CampaignAwareGitBenchData> {
  return loadChartData("tokens", scope);
}

export function loadQuadrantChart(
  scope: ChartScopeParams = {},
  signal?: AbortSignal,
): Promise<CampaignAwareGitBenchData> {
  return loadChartData("quadrant", scope, signal);
}

export function loadHeatmapChart(): Promise<CampaignAwareHeatmapChartData> {
  return getJson<CampaignAwareHeatmapChartData>(
    loadCampaignAwareData("/api/charts/heatmap"),
  );
}

export function loadBenchmark(
  benchmark: string,
  signal?: AbortSignal,
): Promise<BenchmarkDetail> {
  return getJson<BenchmarkDetail>(
    loadCampaignAwareData(`/api/benchmarks/${encodeURIComponent(benchmark)}`),
    signal,
  );
}

export function loadModelResults(
  model: string,
  filters: ModelResultsFilters = {},
  signal?: AbortSignal,
): Promise<ModelResultsResponse> {
  const params: Record<string, string> = {};
  for (const [key, value] of Object.entries(filters)) {
    if (value) params[key] = value;
  }
  const path = model.split("/").map(encodeURIComponent).join("/");
  return getJson<ModelResultsResponse>(
    loadCampaignAwareData(`/api/models/${path}/results`, params),
    signal,
  );
}

export function loadFixture(
  benchmark: string,
  fixture: string,
  signal?: AbortSignal,
): Promise<FixtureDetail> {
  return getJson<FixtureDetail>(
    loadCampaignAwareData(
      `/api/fixtures/${encodeURIComponent(benchmark)}/${encodeURIComponent(
        fixture,
      )}`,
    ),
    signal,
  );
}

export function loadModels(
  signal?: AbortSignal,
): Promise<{ models: CampaignAwareGitBenchData["models"] }> {
  return getJson<{ models: CampaignAwareGitBenchData["models"] }>(
    "/api/models",
    signal,
  );
}

export function loadFixtureAttempts(
  benchmark: string,
  fixture: string,
): Promise<FixtureAttempts> {
  return getJson<FixtureAttempts>(
    loadCampaignAwareData(
      `/api/fixtures/${encodeURIComponent(benchmark)}/${encodeURIComponent(
        fixture,
      )}/attempts`,
    ),
  );
}
