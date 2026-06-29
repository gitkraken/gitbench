import type {
  GitBenchData,
  FixtureInfo,
  FixtureResult,
  CellData,
} from "./types.ts";

export interface CampaignListItem {
  campaign_id: string;
  created_at: string;
  config_hash: string;
  state: string;
  publication_state: string;
  legacy: boolean;
  planned_trials: number;
  completed_trials: number;
  valid_attempts: number;
  passing_attempts: number;
  excluded_attempts: number;
  mean_success_rate: number | null;
  compatible: boolean;
  incomplete: boolean;
  publishable: boolean;
}

export interface CampaignFilters {
  benchmark?: string;
  model?: string;
  output_mode?: string;
}

export interface ReportQueryOptions {
  campaign_id?: string | null;
}

export interface RawAttempt {
  trial_index: number;
  model_name: string;
  reasoning_level: string | null;
  output_mode: string;
  benchmark_name: string;
  fixture_id: string;
  status: string;
  passed: boolean | null;
  similarity: number | null;
  error: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  reasoning_tokens: number | null;
  cost_usd: number | null;
  api_duration_ms: number | null;
  model_output?: string | null;
  parsed_payload?: string | null;
  raw_structured_output?: string | null;
  structured_error?: string | null;
  safety_state?: string | null;
}

export interface ModelResultsFilters {
  benchmark?: string;
  difficulty?: string;
  tag?: string;
  output_mode?: string;
  campaign_id?: string;
}

export interface BenchmarkDetail {
  benchmark: string;
  tag_counts: Record<string, number>;
  leaderboard: {
    model: string;
    pass_at_k: number;
    total: number;
    passed: number;
    avg_similarity: number;
  }[];
  fixtures: Record<string, FixtureInfo>;
  results: Record<string, Record<string, FixtureResult[]>>;
}

export interface FixtureDetail {
  fixture: FixtureInfo;
  outputs: (FixtureResult & { model: string })[];
}

export interface FixtureAttemptGroup {
  model_name: string;
  output_mode: string;
  planned_trials: number;
  completed_trials: number;
  valid_attempts: number;
  passing_attempts: number;
  failing_attempts: number;
  excluded_attempts: number;
  mean_success_rate: number | null;
  classification: "stable_pass" | "flaky" | "stable_fail" | "unknown";
}

export interface FixtureAttempts {
  fixture: FixtureInfo;
  campaign_id: string | null;
  campaign_metadata: CampaignListItem | null;
  groups: FixtureAttemptGroup[];
  attempts: RawAttempt[];
}

export interface ReportStore {
  getSummary(options?: ReportQueryOptions): GitBenchData;
  getModels(): GitBenchData["models"];
  getModelResults(
    model: string,
    filters?: ModelResultsFilters
  ): { model: string; results: Record<string, FixtureResult[]> } | null;
  getBenchmark(
    benchmark: string,
    options?: ReportQueryOptions
  ): BenchmarkDetail | null;
  getFixture(
    benchmark: string,
    fixtureId: string,
    options?: ReportQueryOptions
  ): FixtureDetail | null;
  getHistory(): GitBenchData["runs_meta"];
  // Campaign-aware queries
  getCampaigns(filters?: CampaignFilters): CampaignListItem[];
  getDefaultCampaign(filters?: CampaignFilters): CampaignListItem | null;
  checkCampaignCompatibility(
    campaignId: string,
    filters?: CampaignFilters
  ): boolean;
  getCampaignAggregate(campaignId: string, benchmark: string): CellData | null;
  getCampaign(campaignId: string): CampaignListItem | null;
  getRawAttempts(
    campaignId: string,
    options?: {
      limit?: number;
      offset?: number;
      fixture_id?: string;
      includeOutput?: boolean;
    }
  ): RawAttempt[];
  getRawAttemptByIdentity(
    campaignId: string,
    identity: {
      trial_index: number;
      model_name: string;
      reasoning_level?: string | null;
      output_mode: string;
      benchmark_name?: string;
      fixture_id: string;
    },
    options?: { includeOutput?: boolean }
  ): RawAttempt | null;
  getFixtureAttempts(
    benchmark: string,
    fixtureId: string,
    options?: { campaign_id?: string }
  ): FixtureAttempts | null;
  isCampaignPublicationAllowed(campaignId: string): boolean;
}
