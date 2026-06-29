import assert from "node:assert/strict";
import test from "node:test";

import {
  classifyReliabilityDelta,
  computeFixtureReliability,
  computeReliabilityDeltas,
  reliabilityDeltaSummary,
} from "../src/lib/fixture-reliability.ts";

function result(overrides = {}) {
  return {
    fixture_id: "f001",
    passed: false,
    similarity: 0.5,
    error: null,
    model_output: "",
    reasoning_level: null,
    input_tokens: 10,
    output_tokens: 5,
    total_tokens: 15,
    reasoning_tokens: null,
    cost_usd: 0.01,
    duration_ms: 100,
    api_duration_ms: 50,
    purpose: null,
    difficulty: null,
    tags: [],
    output_mode: "text",
    parsed_payload: null,
    raw_structured_output: null,
    structured_error: null,
    ...overrides,
  };
}

test("computeFixtureReliability excludes errored attempts from the denominator", () => {
  const r = computeFixtureReliability(
    [result({ passed: true }), result({ error: "timeout" })],
    "commit_messages",
    "f001",
  );
  assert.equal(r.validCount, 1);
  assert.equal(r.passCount, 1);
  assert.equal(r.ratio, 1);
});

test("computeFixtureReliability returns null ratio when no valid attempts", () => {
  const r = computeFixtureReliability(
    [result({ error: "timeout" })],
    "commit_messages",
    "f001",
  );
  assert.equal(r.ratio, null);
});

test("classifyReliabilityDelta treats identical ratios as equal", () => {
  const a = computeFixtureReliability([result({ passed: true })], "b", "f001");
  const b = computeFixtureReliability([result({ passed: true })], "b", "f001");
  assert.equal(classifyReliabilityDelta(a, b), "equal");
});

test("classifyReliabilityDelta marks higher ratio as more reliable", () => {
  const a = computeFixtureReliability(
    [result({ passed: true }), result({ passed: true })],
    "b",
    "f001",
  );
  const b = computeFixtureReliability([result({ passed: false })], "b", "f001");
  assert.equal(classifyReliabilityDelta(a, b), "a_more_reliable");
});

test("classifyReliabilityDelta returns unknown when either side has no ratio", () => {
  const a = computeFixtureReliability([result({ passed: true })], "b", "f001");
  const b = computeFixtureReliability([result({ error: "x" })], "b", "f001");
  assert.equal(classifyReliabilityDelta(a, b), "unknown");
});

test("computeReliabilityDeltas produce paired pass-probability displays", () => {
  const data = {
    models: [],
    benchmarks: ["commit_messages"],
    model_summaries: {},
    model_runtimes: {},
    model_token_summaries: {},
    matrix: {},
    fixtures: {
      "model-a": {
        commit_messages: [
          result({ fixture_id: "f001", passed: true }),
          result({ fixture_id: "f001", passed: false }),
        ],
      },
      "model-b": {
        commit_messages: [
          result({ fixture_id: "f001", passed: true }),
          result({ fixture_id: "f001", passed: true }),
        ],
      },
    },
    fixture_index: {},
    runs_meta: [],
    base_model_groups: [],
  };
  const deltas = computeReliabilityDeltas(data, "model-a", "model-b");
  assert.equal(deltas.length, 1);
  const d = deltas[0];
  assert.equal(d.a?.ratio, 0.5);
  assert.equal(d.b?.ratio, 1);
  assert.equal(d.classification, "b_more_reliable");
});

test("reliabilityDeltaSummary aggregates classifications", () => {
  const deltas = [
    { classification: "a_more_reliable" },
    { classification: "b_more_reliable" },
    { classification: "equal" },
    { classification: "unknown" },
  ];
  const summary = reliabilityDeltaSummary(deltas);
  assert.deepEqual(summary, { aMore: 1, bMore: 1, equal: 1, unknown: 1 });
});
