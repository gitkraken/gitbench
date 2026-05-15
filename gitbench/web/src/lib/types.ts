// Types for GitBench aggregated results JSON

export interface ModelInfo {
  name: string;
  provider: string;
  baseModel: string;
  reasoningLevel: string | null;
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
  cost_usd: number | null;
  purpose: string | null;
  difficulty: string | null;
  tags: string[] | null;
}

export interface FixtureInfo {
  id: string;
  benchmark: string;
  prompt: string;
  expected: string;
  description: string;
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
}

export interface GitBenchData {
  models: ModelInfo[];
  benchmarks: string[];
  model_summaries: Record<string, ModelSummary>;
  matrix: Record<string, Record<string, CellData>>;
  fixtures: Record<string, Record<string, FixtureResult[]>>;
  fixture_index: Record<string, FixtureInfo>;
  runs_meta: RunMeta[];
  base_model_groups: BaseModelGroup[];
}
