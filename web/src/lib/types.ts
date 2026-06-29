// Types for GitBench aggregated results JSON

export interface ModelInfo {
  name: string;
  provider: string;
  baseModel: string;
  reasoningLevel: string | null;
  output_mode: string;
}

export interface BaseModelGroupLevel {
  level: string | null;
  modelName: string;
  pass_at_k: number;
  total_cost_usd: number | null;
}

export interface BaseModelGroup {
  provider: string;
  baseModel: string;
  levels: BaseModelGroupLevel[];
}

export interface ModelSummary {
  total_runs: number;
  total_fixtures: number;
  total_passed: number;
  pass_at_k: number;
  total_cost_usd: number | null;
  avg_cost_usd: number | null;
  total_valid_attempts?: number;
  total_passing_attempts?: number;
}

export interface CellData {
  pass_at_k: number;
  total: number;
  passed: number;
  avg_similarity: number;
}

export interface FixtureResult {
  fixture_id: string;
  passed: boolean;
  similarity: number;
  error: string | null;
  model_output: string;
  reasoning_level: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  reasoning_tokens: number | null;
  cost_usd: number | null;
  duration_ms: number | null;
  api_duration_ms: number | null;
  purpose: string | null;
  difficulty: string | null;
  tags: string[] | null;
  output_mode: string;
  parsed_payload: string | null;
  raw_structured_output: string | null;
  structured_error: string | null;
}

export interface ModelRuntimeSummary {
  total_ms: number;
  avg_ms: number;
  min_ms: number;
  max_ms: number;
  fixture_count: number;
}

export interface ModelTokenSummary {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  reasoning_tokens: number | null;
}

export interface FixtureInfo {
  id: string;
  benchmark: string;
  prompt: string;
  expected: string;
  description: string;
  setup: string[];
  purpose: string;
  difficulty: string;
  tags: string[];
}

export interface RunMeta {
  timestamp: string;
  model: string;
  profile: string;
  git_sha: string;
  benchmark_suite_version: string;
  reasoning_level: string;
  output_mode: string;
}

export interface CampaignSummary {
  campaign_id: string;
  created_at: string;
  state: string;
  publication_state: string;
  legacy: boolean;
  planned_trials: number;
  completed_trials: number;
  valid_attempts: number;
  passing_attempts: number;
  excluded_attempts: number;
  mean_success_rate: number | null;
  incomplete: boolean;
  publishable: boolean;
}

export interface CampaignAwareGitBenchData extends GitBenchData {
  campaign_id: string | null;
  campaign_metadata: CampaignSummary | null;
}

export interface FixtureReliability {
  fixture_id: string;
  benchmark: string;
  planned_trials: number;
  completed_trials: number;
  valid_attempts: number;
  passing_attempts: number;
  failing_attempts: number;
  excluded_attempts: number;
  mean_success_rate: number | null;
  pass_any_at_n: Record<string, boolean>;
  classification: "stable_pass" | "flaky" | "stable_fail" | "unknown";
  incomplete: boolean;
}

export interface ModelCampaignSummary {
  model: string;
  output_mode: string;
  planned_trials: number;
  completed_trials: number;
  valid_attempts: number;
  passing_attempts: number;
  excluded_attempts: number;
  mean_success_rate: number | null;
  stable_pass_count: number;
  flaky_count: number;
  stable_fail_count: number;
  incomplete: boolean;
}

export interface GitBenchData {
  models: ModelInfo[];
  benchmarks: string[];
  model_summaries: Record<string, ModelSummary>;
  model_runtimes: Record<string, ModelRuntimeSummary>;
  model_token_summaries: Record<string, ModelTokenSummary>;
  matrix: Record<string, Record<string, CellData>>;
  fixtures: Record<string, Record<string, FixtureResult[]>>;
  fixture_index: Record<string, FixtureInfo>;
  runs_meta: RunMeta[];
  base_model_groups: BaseModelGroup[];
}
