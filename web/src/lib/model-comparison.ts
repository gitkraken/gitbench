import type { GitBenchData } from "./types";
import type { ReportStore } from "./report-store";

export interface BenchmarkDelta {
  benchmark: string;
  textPassRate: number;
  jsonPassRate: number;
  delta: number;
}

export interface ChangedFixture {
  fixtureId: string;
  benchmark: string;
  textPassed: boolean;
  jsonPassed: boolean;
}

export interface ModeComparison {
  textModelName: string;
  jsonModelName: string;
  textPassRate: number;
  jsonPassRate: number;
  passRateDelta: number;
  gained: number; // passed in JSON but not text
  lost: number; // passed in text but not JSON
  unchangedPass: number; // passed in both
  unchangedFail: number; // failed in both
  totalFixtures: number;
  benchmarkDeltas: BenchmarkDelta[];
  changedFixtures: ChangedFixture[];
}

/**
 * Compute a comparison between text and json_schema modes for the same model
 * by querying the report store directly for fixture-level results.
 * Returns null if both modes are not present or if fixture data is unavailable.
 */
export function computeModeComparison(
  store: ReportStore,
  textModelName: string,
  jsonModelName: string
): ModeComparison | null {
  const textResults = store.getModelResults(textModelName);
  const jsonResults = store.getModelResults(jsonModelName);

  if (!textResults || !jsonResults) return null;

  const summary = store.getSummary();
  const textSummary = summary.model_summaries[textModelName];
  const jsonSummary = summary.model_summaries[jsonModelName];

  if (!textSummary || !jsonSummary) return null;

  const textPassRate = textSummary.pass_at_k;
  const jsonPassRate = jsonSummary.pass_at_k;

  // Build pass/fail maps from fixture results
  const textFixtures: Record<string, boolean> = {};
  const jsonFixtures: Record<string, boolean> = {};

  for (const [bench, results] of Object.entries(textResults.results)) {
    for (const r of results) {
      textFixtures[`${bench}/${r.fixture_id}`] = r.passed;
    }
  }
  for (const [bench, results] of Object.entries(jsonResults.results)) {
    for (const r of results) {
      jsonFixtures[`${bench}/${r.fixture_id}`] = r.passed;
    }
  }

  let gained = 0;
  let lost = 0;
  let unchangedPass = 0;
  let unchangedFail = 0;
  const changedFixtures: ChangedFixture[] = [];

  const allFixtureKeys = new Set([
    ...Object.keys(textFixtures),
    ...Object.keys(jsonFixtures),
  ]);

  for (const key of allFixtureKeys) {
    const textPassed = textFixtures[key] ?? false;
    const jsonPassed = jsonFixtures[key] ?? false;
    const [benchmark, fixtureId] = key.split("/");

    if (textPassed && jsonPassed) {
      unchangedPass++;
    } else if (!textPassed && !jsonPassed) {
      unchangedFail++;
    } else if (!textPassed && jsonPassed) {
      gained++;
      changedFixtures.push({ fixtureId, benchmark, textPassed, jsonPassed });
    } else {
      lost++;
      changedFixtures.push({ fixtureId, benchmark, textPassed, jsonPassed });
    }
  }

  // Per-benchmark deltas using matrix data
  const benchmarkDeltas: BenchmarkDelta[] = [];
  for (const bench of summary.benchmarks) {
    const textCell = summary.matrix[textModelName]?.[bench];
    const jsonCell = summary.matrix[jsonModelName]?.[bench];
    if (textCell && jsonCell) {
      benchmarkDeltas.push({
        benchmark: bench,
        textPassRate: textCell.pass_at_k,
        jsonPassRate: jsonCell.pass_at_k,
        delta: jsonCell.pass_at_k - textCell.pass_at_k,
      });
    }
  }
  benchmarkDeltas.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));

  return {
    textModelName,
    jsonModelName,
    textPassRate,
    jsonPassRate,
    passRateDelta: jsonPassRate - textPassRate,
    gained,
    lost,
    unchangedPass,
    unchangedFail,
    totalFixtures: allFixtureKeys.size,
    benchmarkDeltas,
    changedFixtures,
  };
}

/**
 * The JSON variant model name, using the `__json_schema` suffix convention.
 */
export function jsonSchemaModelName(textModelName: string): string {
  return `${textModelName}__json_schema`;
}

/**
 * Detect whether both text and json_schema modes exist for a model name
 * in the summary data.
 */
export function hasBothModes(
  data: GitBenchData,
  textModelName: string
): boolean {
  const jsonName = jsonSchemaModelName(textModelName);
  return (
    data.model_summaries[textModelName] != null &&
    data.model_summaries[jsonName] != null
  );
}
