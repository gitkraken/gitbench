import type { GitBenchData, FixtureInfo, FixtureResult } from "./types.ts";

export interface ModelResultsFilters {
  benchmark?: string;
  difficulty?: string;
  tag?: string;
  output_mode?: string;
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
  results: Record<string, FixtureResult[]>;
}

export interface FixtureDetail {
  fixture: FixtureInfo;
  outputs: (FixtureResult & { model: string })[];
}

export interface ReportStore {
  getSummary(): GitBenchData;
  getModels(): GitBenchData["models"];
  getModelResults(
    model: string,
    filters?: ModelResultsFilters,
  ): { model: string; results: Record<string, FixtureResult[]> } | null;
  getBenchmark(benchmark: string): BenchmarkDetail | null;
  getFixture(benchmark: string, fixtureId: string): FixtureDetail | null;
  getHistory(): GitBenchData["runs_meta"];
}
