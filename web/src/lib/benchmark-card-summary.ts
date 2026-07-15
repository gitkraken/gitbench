import type { FixtureResult, GitBenchData, ModelInfo } from "./types";

const JSON_SCHEMA_SUFFIX = "__json_schema";

export interface BenchmarkCardExtrema {
  score: number;
  label: string;
  modelCount: number;
  isTie: boolean;
}

export interface BenchmarkCardSummary {
  benchmark: string;
  eligibleScoreCount: number;
  best: BenchmarkCardExtrema | null;
  worst: BenchmarkCardExtrema | null;
  averageScore: number | null;
}

interface EligibleBenchmarkScore {
  label: string;
  score: number;
}

interface EligibleModelResults {
  label: string;
  results: FixtureResult[];
}

function stripJsonSchemaSuffix(modelName: string): string {
  return modelName.endsWith(JSON_SCHEMA_SUFFIX)
    ? modelName.slice(0, -JSON_SCHEMA_SUFFIX.length)
    : modelName;
}

function modelVariantKey(modelName: string, outputMode: string): string {
  if (outputMode !== "json_schema") return modelName;
  return modelName.endsWith(JSON_SCHEMA_SUFFIX)
    ? modelName
    : `${modelName}${JSON_SCHEMA_SUFFIX}`;
}

function buildModelInfoLookup(models: ModelInfo[]): Map<string, ModelInfo> {
  const lookup = new Map<string, ModelInfo>();
  for (const model of models) {
    const outputMode = model.output_mode ?? "text";
    const variantKey = modelVariantKey(model.name, outputMode);
    lookup.set(variantKey, model);
    if (outputMode !== "json_schema" || model.name.endsWith(JSON_SCHEMA_SUFFIX)) {
      lookup.set(model.name, model);
    }
  }
  return lookup;
}

function outputModeForModelKey(
  modelKey: string,
  modelInfo: ModelInfo | undefined,
): string {
  if (modelInfo?.output_mode) return modelInfo.output_mode;
  return modelKey.endsWith(JSON_SCHEMA_SUFFIX) ? "json_schema" : "text";
}

function modelIdentityLabel(
  modelKey: string,
  modelInfo: ModelInfo | undefined,
): string {
  if (modelInfo?.provider && modelInfo.baseModel) {
    return `${modelInfo.provider}/${modelInfo.baseModel}`;
  }

  const cleanName = stripJsonSchemaSuffix(modelKey);
  const slashIndex = cleanName.indexOf("/");
  const effortSeparatorIndex = cleanName.lastIndexOf(":");
  if (slashIndex >= 0 && effortSeparatorIndex > slashIndex) {
    return cleanName.slice(0, effortSeparatorIndex);
  }
  return cleanName;
}

function hasStructuredOutputError(result: FixtureResult): boolean {
  return (
    typeof result.structured_error === "string" &&
    result.structured_error.trim().length > 0
  );
}

function fixtureResultsForModel(
  data: GitBenchData,
  modelKey: string,
  benchmark: string,
): FixtureResult[] {
  const direct = data.fixtures[modelKey]?.[benchmark];
  if (direct) return direct;

  const canonicalKey = stripJsonSchemaSuffix(modelKey);
  return data.fixtures[canonicalKey]?.[benchmark] ?? [];
}

function fixturePassRate(results: FixtureResult[]): number | null {
  if (results.length === 0) return null;

  const byFixture = new Map<string, FixtureResult[]>();
  for (const result of results) {
    const fixtureResults = byFixture.get(result.fixture_id) ?? [];
    fixtureResults.push(result);
    byFixture.set(result.fixture_id, fixtureResults);
  }

  if (byFixture.size === 0) return null;

  let scoreTotal = 0;
  for (const fixtureResults of byFixture.values()) {
    const passed = fixtureResults.filter((result) => result.passed).length;
    scoreTotal += passed / fixtureResults.length;
  }

  return scoreTotal / byFixture.size;
}

function isStrictUnsupportedJsonSchemaZero(
  modelInfo: ModelInfo | undefined,
  modelKey: string,
  score: number,
  results: FixtureResult[],
): boolean {
  if (outputModeForModelKey(modelKey, modelInfo) !== "json_schema") {
    return false;
  }
  if (score !== 0) return false;

  return results.length > 0 && results.every(hasStructuredOutputError);
}

function collectEligibleScores(
  data: GitBenchData,
  benchmark: string,
): EligibleBenchmarkScore[] {
  const modelInfoByKey = buildModelInfoLookup(data.models);
  const resultsByModel = new Map<string, EligibleModelResults>();

  for (const [modelKey, byBenchmark] of Object.entries(data.fixtures)) {
    if (!(benchmark in byBenchmark)) continue;
    const results = fixtureResultsForModel(data, modelKey, benchmark);
    const score = fixturePassRate(results);
    if (score == null) continue;
    const modelInfo = modelInfoByKey.get(modelKey);
    if (
      isStrictUnsupportedJsonSchemaZero(
        modelInfo,
        modelKey,
        score,
        results,
      )
    ) {
      continue;
    }

    const modelIdentity = modelIdentityLabel(modelKey, modelInfo);
    const modelResults = resultsByModel.get(modelIdentity) ?? {
      label: modelIdentity,
      results: [],
    };
    modelResults.results.push(...results);
    resultsByModel.set(modelIdentity, modelResults);
  }

  return Array.from(resultsByModel.values(), (modelResults) => ({
    label: modelResults.label,
    score: fixturePassRate(modelResults.results) ?? 0,
  }));
}

function extremaForScore(
  scores: EligibleBenchmarkScore[],
  score: number,
): BenchmarkCardExtrema {
  const tied = scores.filter((entry) => entry.score === score);
  const modelCount = tied.length;
  return {
    score,
    label: modelCount === 1 ? tied[0].label : `${modelCount} models`,
    modelCount,
    isTie: modelCount > 1,
  };
}

export function buildBenchmarkCardSummary(
  data: GitBenchData,
  benchmark: string,
): BenchmarkCardSummary {
  const scores = collectEligibleScores(data, benchmark);
  if (scores.length === 0) {
    return {
      benchmark,
      eligibleScoreCount: 0,
      best: null,
      worst: null,
      averageScore: null,
    };
  }

  const scoreValues = scores.map((entry) => entry.score);
  const bestScore = Math.max(...scoreValues);
  const worstScore = Math.min(...scoreValues);
  const totalScore = scoreValues.reduce((sum, score) => sum + score, 0);

  return {
    benchmark,
    eligibleScoreCount: scores.length,
    best: extremaForScore(scores, bestScore),
    worst: extremaForScore(scores, worstScore),
    averageScore: totalScore / scores.length,
  };
}

export function formatBenchmarkPercent(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}
