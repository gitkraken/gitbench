import assert from "node:assert/strict";
import test from "node:test";

import {
  buildQuadrantPoints,
  pairQuadrantPoints,
  quadrantPairForPoint,
  rankQuadrantPoints,
} from "../src/components/charts/quadrant-data.ts";

function data(models) {
  return {
    models,
    benchmarks: [],
    model_summaries: {},
    model_runtimes: {},
    model_token_summaries: {},
    matrix: {},
    fixtures: {},
    fixture_index: {},
    runs_meta: [],
    base_model_groups: [],
  };
}

function model(provider, baseModel, level, outputMode) {
  return {
    name: `${provider}/${baseModel}:${level}`,
    provider,
    baseModel,
    reasoningLevel: level,
    output_mode: outputMode,
  };
}

function metric(values) {
  return {
    better: "higher",
    extractor(effort) {
      const value = values[effort.modelName];
      return value == null ? null : { ...effort, value };
    },
  };
}

test("quadrant selection chooses the best effort independently per mode", () => {
  const chartData = data([
    model("openai", "gpt-a", "low", "text"),
    model("openai", "gpt-a", "high", "text"),
    model("openai", "gpt-a", "medium", "json_schema"),
    model("openai", "gpt-a", "high", "json_schema"),
  ]);
  const xMetric = metric({
    "openai/gpt-a:low": 1,
    "openai/gpt-a:high": 10,
    "openai/gpt-a:medium__json_schema": 9,
    "openai/gpt-a:high__json_schema": 2,
  });
  const yMetric = metric({
    "openai/gpt-a:low": 1,
    "openai/gpt-a:high": 10,
    "openai/gpt-a:medium__json_schema": 9,
    "openai/gpt-a:high__json_schema": 2,
  });

  const points = buildQuadrantPoints(
    chartData,
    ["openai/gpt-a"],
    xMetric,
    yMetric,
    "both"
  );

  assert.deepEqual(
    points.map((point) => [
      point.outputMode,
      point.reasoningLevel,
      point.x,
      point.y,
    ]),
    [
      ["text", "high", 10, 10],
      ["json_schema", "medium", 9, 9],
    ]
  );
});

test("quadrant pairs retain missing siblings and resolve from either point", () => {
  const chartData = data([
    model("openai", "gpt-a", "high", "text"),
    model("anthropic", "claude-b", "medium", "text"),
    model("anthropic", "claude-b", "medium", "json_schema"),
  ]);
  const values = {
    "openai/gpt-a:high": 8,
    "anthropic/claude-b:medium": 7,
    "anthropic/claude-b:medium__json_schema": 6,
  };
  const points = buildQuadrantPoints(
    chartData,
    ["openai/gpt-a", "anthropic/claude-b"],
    metric(values),
    metric(values),
    "both"
  );
  const pairs = pairQuadrantPoints(points);
  const missingJson = pairs.find((pair) => pair.id === "openai/gpt-a");
  const fullPair = pairs.find((pair) => pair.id === "anthropic/claude-b");

  assert.ok(missingJson.text);
  assert.equal(missingJson.json, undefined);
  assert.equal(quadrantPairForPoint(pairs, fullPair.json), fullPair);
});

test("coincident quadrant points remain one solid point plus a ring pair", () => {
  const chartData = data([
    model("openai", "gpt-a", "high", "text"),
    model("openai", "gpt-a", "high", "json_schema"),
  ]);
  const values = {
    "openai/gpt-a:high": 5,
    "openai/gpt-a:high__json_schema": 5,
  };
  const points = buildQuadrantPoints(
    chartData,
    ["openai/gpt-a"],
    metric(values),
    metric(values),
    "both"
  );
  const [pair] = pairQuadrantPoints(points);

  assert.equal(pair.coincident, true);
  assert.deepEqual([pair.text.x, pair.text.y], [pair.json.x, pair.json.y]);
});

test("quadrant rankings treat output-mode points independently", () => {
  const points = [
    {
      id: "a::text",
      pairId: "a",
      outputMode: "text",
      compositeScore: 0.9,
    },
    {
      id: "a::json_schema",
      pairId: "a",
      outputMode: "json_schema",
      compositeScore: 0.8,
    },
    {
      id: "b::text",
      pairId: "b",
      outputMode: "text",
      compositeScore: 0.7,
    },
  ];

  assert.deepEqual(
    rankQuadrantPoints(points, 2).map((point) => point.id),
    ["a::text", "a::json_schema"]
  );
});
