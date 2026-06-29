import assert from "node:assert/strict";
import test from "node:test";

import {
  buildGroupedMetricRows,
  buildTokenUsageRows,
  getGroupedMetricSortValue,
  pairModelVariants,
  passRateMetric,
} from "../src/components/charts/model-groups.ts";

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

function chartData({ text = [], json = [], secondGroup }) {
  const models = [];
  const model_summaries = {};

  function addGroup(provider, baseModel, values, outputMode) {
    values.forEach((value, index) => {
      const level = ["low", "medium", "high", "xhigh", "max"][index];
      const name = `${provider}/${baseModel}:${level}`;
      models.push({
        name,
        provider,
        baseModel,
        reasoningLevel: level,
        output_mode: outputMode,
      });
      const key = outputMode === "json_schema" ? `${name}__json_schema` : name;
      model_summaries[key] = summary(value / 100);
    });
  }

  addGroup("openai", "gpt-test", text, "text");
  addGroup("openai", "gpt-test", json, "json_schema");
  if (secondGroup) {
    addGroup("anthropic", "claude-test", secondGroup.text ?? [], "text");
    addGroup("anthropic", "claude-test", secondGroup.json ?? [], "json_schema");
  }

  return {
    models,
    benchmarks: [],
    model_summaries,
    model_runtimes: {},
    model_token_summaries: {},
    matrix: {},
    fixtures: {},
    fixture_index: {},
    runs_meta: [],
    base_model_groups: [],
  };
}

test("buildGroupedMetricRows aggregates each output mode independently", () => {
  const data = chartData({
    text: [10, 10, 10, 20, 50],
    json: [80, 90],
  });

  const [row] = buildGroupedMetricRows(
    data,
    ["openai/gpt-test"],
    passRateMetric,
    "median",
    "both"
  );

  assert.equal(row.modes.text.representativeValue, 20);
  assert.equal(row.modes.text.minValue, 10);
  assert.equal(row.modes.text.maxValue, 50);
  assert.deepEqual(row.modes.text.rangeWhisker, [10, 30]);
  assert.equal(row.modes.json_schema.representativeValue, 85);
  assert.deepEqual(row.modes.json_schema.rangeWhisker, [5, 5]);
  assert.equal(row.sortValue, 52.5);
});

test("buildGroupedMetricRows preserves a group with one available mode", () => {
  const data = chartData({ text: [72, 81, 85] });

  const [row] = buildGroupedMetricRows(
    data,
    ["openai/gpt-test"],
    passRateMetric,
    "median",
    "both"
  );

  assert.equal(row.modes.text.representativeValue, 81);
  assert.equal(row.modes.json_schema, undefined);
  assert.equal(row.jsonRepresentativeValue, null);
  assert.equal(getGroupedMetricSortValue(row, "both"), 81);
});

test("Both-mode sort values use the mean of available representatives", () => {
  const data = chartData({
    text: [90],
    json: [70],
    secondGroup: { text: [78], json: [76] },
  });

  const rows = buildGroupedMetricRows(
    data,
    ["openai/gpt-test", "anthropic/claude-test"],
    passRateMetric,
    "median",
    "both"
  ).sort((a, b) => b.sortValue - a.sortValue);

  assert.deepEqual(
    rows.map((row) => [row.id, row.sortValue]),
    [
      ["openai/gpt-test", 80],
      ["anthropic/claude-test", 77],
    ]
  );
});

test("pairModelVariants groups concrete storage keys by canonical effort", () => {
  assert.deepEqual(
    pairModelVariants([
      "openai/gpt-test:high",
      "openai/gpt-test:high__json_schema",
      "anthropic/claude-test:medium__json_schema",
    ]),
    [
      {
        id: "openai/gpt-test:high",
        label: "openai/gpt-test:high",
        textModelName: "openai/gpt-test:high",
        jsonModelName: "openai/gpt-test:high__json_schema",
      },
      {
        id: "anthropic/claude-test:medium",
        label: "anthropic/claude-test:medium",
        jsonModelName: "anthropic/claude-test:medium__json_schema",
      },
    ]
  );
});

function tokenChartData(tokenSummaries) {
  const levels = ["low", "medium", "high"];
  const models = levels.map((level) => ({
    name: `openai/gpt-test:${level}`,
    provider: "openai",
    baseModel: "gpt-test",
    reasoningLevel: level,
    output_mode: "text",
  }));
  return {
    models,
    benchmarks: [],
    model_summaries: Object.fromEntries(
      models.map((model) => [model.name, summary(1)]),
    ),
    model_runtimes: {},
    model_token_summaries: Object.fromEntries(
      levels.map((level, index) => [
        `openai/gpt-test:${level}`,
        tokenSummaries[index],
      ]),
    ),
    matrix: {},
    fixtures: {},
    fixture_index: {},
    runs_meta: [],
    base_model_groups: [],
  };
}

test("token rows use one representative effort instead of summing efforts", () => {
  const data = tokenChartData([
    {
      input_tokens: 40,
      output_tokens: 60,
      reasoning_tokens: 10,
      total_tokens: 100,
    },
    {
      input_tokens: 80,
      output_tokens: 120,
      reasoning_tokens: 20,
      total_tokens: 200,
    },
    {
      input_tokens: 120,
      output_tokens: 180,
      reasoning_tokens: 30,
      total_tokens: 300,
    },
  ]);

  const [row] = buildTokenUsageRows(
    data,
    ["openai/gpt-test"],
    "text",
  );

  assert.equal(row.textRepresentativeValue, 200);
  assert.equal(row.textInputTokens, 80);
  assert.equal(row.textVisibleOutputTokens, 100);
  assert.equal(row.textReasoningTokens, 20);
  assert.equal(
    row.textInputTokens +
      row.textVisibleOutputTokens +
      row.textReasoningTokens,
    200,
  );
});

test("token rows preserve no-reasoning, zero, and inconsistent counts", () => {
  const noReasoning = buildTokenUsageRows(
    tokenChartData([
      {
        input_tokens: 40,
        output_tokens: 60,
        reasoning_tokens: null,
        total_tokens: 100,
      },
      {
        input_tokens: 80,
        output_tokens: 120,
        reasoning_tokens: null,
        total_tokens: 200,
      },
      {
        input_tokens: 120,
        output_tokens: 180,
        reasoning_tokens: null,
        total_tokens: 300,
      },
    ]),
    ["openai/gpt-test"],
    "text",
  )[0];
  assert.equal(noReasoning.textVisibleOutputTokens, 120);
  assert.equal(noReasoning.textReasoningTokens, 0);
  assert.equal(noReasoning.textHasReasoningData, false);
  assert.equal(noReasoning.hasReasoningData, false);

  const zeroReasoning = buildTokenUsageRows(
    tokenChartData([
      {
        input_tokens: 40,
        output_tokens: 60,
        reasoning_tokens: 0,
        total_tokens: 100,
      },
      {
        input_tokens: 80,
        output_tokens: 120,
        reasoning_tokens: 0,
        total_tokens: 200,
      },
      {
        input_tokens: 120,
        output_tokens: 180,
        reasoning_tokens: 0,
        total_tokens: 300,
      },
    ]),
    ["openai/gpt-test"],
    "text",
  )[0];
  assert.equal(zeroReasoning.textVisibleOutputTokens, 120);
  assert.equal(zeroReasoning.textReasoningTokens, 0);
  assert.equal(zeroReasoning.textHasReasoningData, true);
  assert.equal(zeroReasoning.hasReasoningData, true);

  const inconsistent = buildTokenUsageRows(
    tokenChartData([
      {
        input_tokens: 40,
        output_tokens: 60,
        reasoning_tokens: 10,
        total_tokens: 100,
      },
      {
        input_tokens: 80,
        output_tokens: 100,
        reasoning_tokens: 120,
        total_tokens: 180,
      },
      {
        input_tokens: 120,
        output_tokens: 180,
        reasoning_tokens: 30,
        total_tokens: 300,
      },
    ]),
    ["openai/gpt-test"],
    "text",
  )[0];
  assert.equal(inconsistent.textVisibleOutputTokens, 0);
  assert.equal(inconsistent.textReasoningTokens, 120);
});
