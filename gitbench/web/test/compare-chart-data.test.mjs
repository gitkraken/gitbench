import assert from "node:assert/strict";
import test from "node:test";

import {
  buildCompareBenchmarkData,
  buildCompareOverallRows,
  buildCompareReliabilityPair,
  compareBenchmarkPairValues,
} from "../src/components/charts/compare-chart-data.ts";

const COLORS = ["#111111", "#222222"];

function summary(passAtK) {
  return {
    total_runs: 1,
    total_fixtures: 1,
    total_passed: passAtK > 0 ? 1 : 0,
    pass_at_k: passAtK,
    total_cost_usd: null,
    avg_cost_usd: null,
  };
}

function cell(passAtK) {
  return {
    pass_at_k: passAtK,
    total: 1,
    passed: passAtK > 0 ? 1 : 0,
    avg_similarity: passAtK,
  };
}

function data() {
  return {
    models: [
      {
        name: "openai/gpt-a:high",
        provider: "openai",
        baseModel: "gpt-a",
        reasoningLevel: "high",
        output_mode: "text",
      },
      {
        name: "openai/gpt-a:high",
        provider: "openai",
        baseModel: "gpt-a",
        reasoningLevel: "high",
        output_mode: "json_schema",
      },
      {
        name: "anthropic/claude-b:medium",
        provider: "anthropic",
        baseModel: "claude-b",
        reasoningLevel: "medium",
        output_mode: "text",
      },
    ],
    benchmarks: ["bench-a", "bench-b"],
    model_summaries: {
      "openai/gpt-a:high": summary(0.9),
      "openai/gpt-a:high__json_schema": summary(0.7),
      "anthropic/claude-b:medium": summary(0.78),
    },
    model_runtimes: {},
    model_token_summaries: {},
    matrix: {
      "openai/gpt-a:high": {
        "bench-a": cell(0.8),
        "bench-b": cell(0.6),
      },
      "openai/gpt-a:high__json_schema": {
        "bench-a": cell(0.7),
        "bench-b": cell(0.5),
      },
      "anthropic/claude-b:medium": {
        "bench-a": cell(0.9),
      },
    },
    fixtures: {},
    fixture_index: {},
    runs_meta: [],
    base_model_groups: [],
  };
}

test("Compare overall pairs variants and sorts by the mean available rate", () => {
  const rows = buildCompareOverallRows(data(), [
    "openai/gpt-a:high",
    "openai/gpt-a:high__json_schema",
    "anthropic/claude-b:medium",
  ]);

  assert.deepEqual(
    rows.map((row) => ({
      id: row.id,
      text: row.textPassRate,
      json: row.jsonPassRate,
      sort: row.sortValue,
    })),
    [
      {
        id: "anthropic/claude-b:medium",
        text: 78,
        json: null,
        sort: 78,
      },
      {
        id: "openai/gpt-a:high",
        text: 90,
        json: 70,
        sort: 80,
      },
    ].sort((a, b) => b.sort - a.sort)
  );
});

test("Compare reliability pair uses one representative from each selected group", () => {
  assert.deepEqual(
    buildCompareReliabilityPair(
      data(),
      ["openai/gpt-a", "anthropic/claude-b"],
      "both"
    ),
    ["openai/gpt-a:high", "anthropic/claude-b:medium"]
  );
});

test("Compare benchmark series keep each model effort's modes consecutive", () => {
  const chart = buildCompareBenchmarkData(
    data(),
    [
      "openai/gpt-a:high",
      "openai/gpt-a:high__json_schema",
      "anthropic/claude-b:medium",
    ],
    "both",
    COLORS
  );

  assert.deepEqual(
    chart.series.map((series) => [
      series.pairId,
      series.outputMode,
      series.color,
    ]),
    [
      ["openai/gpt-a:high", "text", COLORS[0]],
      ["openai/gpt-a:high", "json_schema", COLORS[0]],
      ["anthropic/claude-b:medium", "text", COLORS[1]],
      ["anthropic/claude-b:medium", "json_schema", COLORS[1]],
    ]
  );
  assert.equal(chart.rows[0].series_1_json_schema, null);
});

test("Compare benchmark tooltip lookup returns only the active pair", () => {
  const chart = buildCompareBenchmarkData(
    data(),
    [
      "openai/gpt-a:high",
      "openai/gpt-a:high__json_schema",
      "anthropic/claude-b:medium",
    ],
    "both",
    COLORS
  );
  const activeSeries = chart.seriesByDataKey.get("series_0_json_schema");

  assert.equal(activeSeries.pairId, "openai/gpt-a:high");
  assert.deepEqual(
    compareBenchmarkPairValues(
      chart.rows[0],
      chart.series,
      activeSeries.pairId
    ),
    { text: 80, json_schema: 70 }
  );
});
