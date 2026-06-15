import type {
  BenchmarkDetail,
  CampaignListItem,
  FixtureAttempts,
  FixtureDetail,
  ModelResultsFilters,
  RawAttempt,
} from "@/lib/report-store";
import type { GitBenchData } from "@/lib/types";

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load ${url}: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export interface HeatmapChartData {
  models: GitBenchData["models"];
  benchmarks: GitBenchData["benchmarks"];
  base_model_groups: GitBenchData["base_model_groups"];
  matrix: Record<string, ([number, number, number] | null)[]>;
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

export function loadCampaigns(
  filters: Record<string, string> = {}
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
    `/api/campaigns/${encodeURIComponent(campaignId)}`
  );
}

export function loadRawAttempts(
  campaignId: string,
  options: {
    fixture_id?: string;
    limit?: number;
    offset?: number;
    include_output?: boolean;
  } = {}
): Promise<RawAttemptsResponse> {
  const params = new URLSearchParams();
  if (options.fixture_id) params.set("fixture_id", options.fixture_id);
  if (options.limit !== undefined) params.set("limit", String(options.limit));
  if (options.offset !== undefined)
    params.set("offset", String(options.offset));
  if (options.include_output) params.set("include_output", "true");
  const suffix = params.size ? `?${params}` : "";
  return getJson<RawAttemptsResponse>(
    `/api/campaigns/${encodeURIComponent(campaignId)}/raw-attempts${suffix}`
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
  options: { include_output?: boolean } = {}
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
    `/api/campaigns/${encodeURIComponent(campaignId)}/attempts/${path}${suffix}`
  );
}

export function getSelectedCampaignId(): string | null {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get("campaign");
}

function loadCampaignAwareData(
  path: string,
  params: Record<string, string | undefined> = {}
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

export function loadSummary(): Promise<GitBenchData> {
  return getJson<GitBenchData>(loadCampaignAwareData("/api/summary"));
}

function loadChartData(
  chart: "pass-rate" | "cost" | "runtime" | "tokens" | "quadrant" | "heatmap",
  params: Record<string, string | undefined> = {}
): Promise<GitBenchData> {
  return getJson<GitBenchData>(
    loadCampaignAwareData(`/api/charts/${chart}`, params)
  );
}

export function loadPassRateChart(benchmark?: string): Promise<GitBenchData> {
  return loadChartData("pass-rate", { benchmark });
}

export function loadCostChart(): Promise<GitBenchData> {
  return loadChartData("cost");
}

export function loadRuntimeChart(): Promise<GitBenchData> {
  return loadChartData("runtime");
}

export function loadTokenChart(): Promise<GitBenchData> {
  return loadChartData("tokens");
}

export function loadQuadrantChart(): Promise<GitBenchData> {
  return loadChartData("quadrant");
}

export function loadHeatmapChart(): Promise<HeatmapChartData> {
  return getJson<HeatmapChartData>(
    loadCampaignAwareData("/api/charts/heatmap")
  );
}

export function loadBenchmark(benchmark: string): Promise<BenchmarkDetail> {
  return getJson<BenchmarkDetail>(
    loadCampaignAwareData(`/api/benchmarks/${encodeURIComponent(benchmark)}`)
  );
}

export function loadModelResults(
  model: string,
  filters: ModelResultsFilters = {}
) {
  const params: Record<string, string> = {};
  for (const [key, value] of Object.entries(filters)) {
    if (value) params[key] = value;
  }
  const suffix = new URLSearchParams(params).toString();
  const query = suffix ? `?${suffix}` : "";
  const path = model.split("/").map(encodeURIComponent).join("/");
  return getJson(loadCampaignAwareData(`/api/models/${path}/results${query}`));
}

export function loadFixture(
  benchmark: string,
  fixture: string
): Promise<FixtureDetail> {
  return getJson<FixtureDetail>(
    loadCampaignAwareData(
      `/api/fixtures/${encodeURIComponent(benchmark)}/${encodeURIComponent(
        fixture
      )}`
    )
  );
}

export function loadFixtureAttempts(
  benchmark: string,
  fixture: string
): Promise<FixtureAttempts> {
  return getJson<FixtureAttempts>(
    loadCampaignAwareData(
      `/api/fixtures/${encodeURIComponent(benchmark)}/${encodeURIComponent(
        fixture
      )}/attempts`
    )
  );
}

export function loadHistory(): Promise<Pick<GitBenchData, "runs_meta">> {
  return getJson<Pick<GitBenchData, "runs_meta">>(
    loadCampaignAwareData("/api/history")
  );
}
