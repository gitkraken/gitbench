import type { FixtureResult, GitBenchData } from "./types";

export interface FixtureReliability {
  benchmark: string;
  fixtureId: string;
  passCount: number;
  validCount: number;
  ratio: number | null;
}

export interface FixtureReliabilityDelta {
  benchmark: string;
  fixtureId: string;
  a: FixtureReliability | null;
  b: FixtureReliability | null;
  delta: number | null;
  classification: "a_more_reliable" | "b_more_reliable" | "equal" | "unknown";
}

export function computeFixtureReliability(
  results: FixtureResult[],
  benchmark: string,
  fixtureId: string
): FixtureReliability {
  const valid = results.filter(
    (r) => r.error == null && r.fixture_id === fixtureId
  );
  if (valid.length === 0) {
    return { benchmark, fixtureId, passCount: 0, validCount: 0, ratio: null };
  }
  const passCount = valid.filter((r) => r.passed).length;
  return {
    benchmark,
    fixtureId,
    passCount,
    validCount: valid.length,
    ratio: passCount / valid.length,
  };
}

export function classifyReliabilityDelta(
  a: FixtureReliability | null,
  b: FixtureReliability | null
): FixtureReliabilityDelta["classification"] {
  if (a?.ratio == null || b?.ratio == null) return "unknown";
  const epsilon = 1e-9;
  if (Math.abs(a.ratio - b.ratio) <= epsilon) return "equal";
  return a.ratio > b.ratio ? "a_more_reliable" : "b_more_reliable";
}

export function computeModelReliabilityMap(
  data: GitBenchData,
  modelName: string
): Map<string, FixtureReliability> {
  const map = new Map<string, FixtureReliability>();
  const resultsByBenchmark = data.fixtures[modelName];
  if (!resultsByBenchmark) return map;
  for (const [benchmark, results] of Object.entries(resultsByBenchmark)) {
    const byFixture = groupResultsByFixture(results, benchmark);
    for (const [fixtureId, fixtureResults] of byFixture) {
      const key = `${benchmark}/${fixtureId}`;
      map.set(
        key,
        computeFixtureReliability(fixtureResults, benchmark, fixtureId)
      );
    }
  }
  return map;
}

export function computeReliabilityDeltas(
  data: GitBenchData,
  modelA: string,
  modelB: string
): FixtureReliabilityDelta[] {
  const mapA = computeModelReliabilityMap(data, modelA);
  const mapB = computeModelReliabilityMap(data, modelB);
  const keys = new Set([...mapA.keys(), ...mapB.keys()]);
  const deltas: FixtureReliabilityDelta[] = [];
  for (const key of keys) {
    const [benchmark, fixtureId] = key.split("/");
    const a = mapA.get(key) ?? null;
    const b = mapB.get(key) ?? null;
    const classification = classifyReliabilityDelta(a, b);
    const delta =
      a?.ratio != null && b?.ratio != null ? a.ratio - b.ratio : null;
    deltas.push({ benchmark, fixtureId, a, b, delta, classification });
  }
  return deltas;
}

function groupResultsByFixture(
  results: FixtureResult[],
  benchmark: string
): Map<string, FixtureResult[]> {
  const map = new Map<string, FixtureResult[]>();
  for (const r of results) {
    const list = map.get(r.fixture_id) ?? [];
    list.push({ ...r, benchmark } as FixtureResult);
    map.set(r.fixture_id, list);
  }
  return map;
}

export function reliabilityDeltaSummary(deltas: FixtureReliabilityDelta[]) {
  let aMore = 0;
  let bMore = 0;
  let equal = 0;
  let unknown = 0;
  for (const d of deltas) {
    if (d.classification === "a_more_reliable") aMore++;
    else if (d.classification === "b_more_reliable") bMore++;
    else if (d.classification === "equal") equal++;
    else unknown++;
  }
  return { aMore, bMore, equal, unknown };
}
