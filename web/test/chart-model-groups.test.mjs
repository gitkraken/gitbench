import assert from "node:assert/strict";
import test from "node:test";

import {
  buildGroupedMetricRows,
  buildTokenUsageRows,
  costMetric,
  getGroupedMetricSortValue,
  pairModelVariants,
  passRateMetric,
  runtimeMetric,
  sortGroupedMetricRowsDescending,
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
    "both",
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
    "both",
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
    "both",
  ).sort((a, b) => b.sortValue - a.sortValue);

  assert.deepEqual(
    rows.map((row) => [row.id, row.sortValue]),
    [
      ["openai/gpt-test", 80],
      ["anthropic/claude-test", 77],
    ],
  );
});

function resourceChartData(groups) {
  const levels = ["low", "medium", "high", "xhigh", "max"];
  const models = [];
  const model_summaries = {};
  const model_runtimes = {};
  const model_token_summaries = {};

  function addMode(provider, baseModel, outputMode, values) {
    values.forEach((metrics, index) => {
      const level = levels[index] ?? `level-${index}`;
      const name = `${provider}/${baseModel}:${level}`;
      const key = outputMode === "json_schema" ? `${name}__json_schema` : name;
      models.push({
        name,
        provider,
        baseModel,
        reasoningLevel: level,
        output_mode: outputMode,
      });
      model_summaries[key] = {
        ...summary(1),
        total_cost_usd: metrics.cost,
        avg_cost_usd: metrics.cost,
      };
      model_runtimes[key] = {
        total_ms: metrics.runtimeSeconds * 1000,
        avg_ms: metrics.runtimeSeconds * 1000,
        min_ms: metrics.runtimeSeconds * 1000,
        max_ms: metrics.runtimeSeconds * 1000,
        fixture_count: 1,
      };
      const inputTokens = Math.floor(metrics.tokens / 2);
      model_token_summaries[key] = {
        input_tokens: inputTokens,
        output_tokens: metrics.tokens - inputTokens,
        reasoning_tokens: null,
        total_tokens: metrics.tokens,
      };
    });
  }

  for (const group of groups) {
    addMode(group.provider, group.baseModel, "text", group.text ?? []);
    addMode(
      group.provider,
      group.baseModel,
      "json_schema",
      group.json ?? [],
    );
  }

  return {
    models,
    benchmarks: [],
    model_summaries,
    model_runtimes,
    model_token_summaries,
    matrix: {},
    fixtures: {},
    fixture_index: {},
    runs_meta: [],
    base_model_groups: [],
  };
}

test("resource chart rows sort single-mode representatives highest-first", () => {
  const data = resourceChartData([
    {
      provider: "openai",
      baseModel: "gpt-test",
      text: [
        { cost: 10, runtimeSeconds: 5, tokens: 5000 },
        { cost: 10, runtimeSeconds: 5, tokens: 5000 },
        { cost: 10, runtimeSeconds: 5, tokens: 5000 },
        { cost: 20, runtimeSeconds: 12, tokens: 8000 },
        { cost: 50, runtimeSeconds: 30, tokens: 12000 },
      ],
    },
    {
      provider: "anthropic",
      baseModel: "claude-test",
      text: [{ cost: 80, runtimeSeconds: 60, tokens: 15000 }],
    },
    {
      provider: "google",
      baseModel: "gemini-test",
      text: [{ cost: 50, runtimeSeconds: 30, tokens: 12000 }],
    },
  ]);
  const selectedGroups = [
    "openai/gpt-test",
    "anthropic/claude-test",
    "google/gemini-test",
  ];

  const costRows = sortGroupedMetricRowsDescending(
    buildGroupedMetricRows(data, selectedGroups, costMetric, "median", "text"),
  );
  assert.deepEqual(
    costRows.map((row) => [row.id, row.sortValue]),
    [
      ["anthropic/claude-test", 80],
      ["google/gemini-test", 50],
      ["openai/gpt-test", 20],
    ],
  );
  assert.equal(costRows[2].modes.text.representativeValue, 20);

  const runtimeRows = sortGroupedMetricRowsDescending(
    buildGroupedMetricRows(
      data,
      selectedGroups,
      runtimeMetric,
      "median",
      "text",
    ),
  );
  assert.deepEqual(
    runtimeRows.map((row) => [row.id, row.sortValue]),
    [
      ["anthropic/claude-test", 60],
      ["google/gemini-test", 30],
      ["openai/gpt-test", 12],
    ],
  );
  assert.equal(runtimeRows[2].modes.text.representativeValue, 12);

  const tokenRows = sortGroupedMetricRowsDescending(
    buildTokenUsageRows(data, selectedGroups, "text"),
  );
  assert.deepEqual(
    tokenRows.map((row) => [row.id, row.sortValue]),
    [
      ["anthropic/claude-test", 15000],
      ["google/gemini-test", 12000],
      ["openai/gpt-test", 8000],
    ],
  );
  assert.equal(tokenRows[2].modes.text.representativeValue, 8000);
});

test("resource chart rows sort Both-mode mean representatives highest-first", () => {
  const data = resourceChartData([
    {
      provider: "openai",
      baseModel: "gpt-test",
      text: [{ cost: 10, runtimeSeconds: 40, tokens: 5000 }],
      json: [{ cost: 50, runtimeSeconds: 60, tokens: 15000 }],
    },
    {
      provider: "anthropic",
      baseModel: "claude-test",
      text: [{ cost: 20, runtimeSeconds: 45, tokens: 8000 }],
      json: [{ cost: 30, runtimeSeconds: 50, tokens: 10000 }],
    },
  ]);
  const selectedGroups = ["openai/gpt-test", "anthropic/claude-test"];

  const costRows = sortGroupedMetricRowsDescending(
    buildGroupedMetricRows(data, selectedGroups, costMetric, "median", "both"),
  );
  assert.deepEqual(
    costRows.map((row) => [
      row.id,
      row.sortValue,
      row.modes.text.representativeValue,
      row.modes.json_schema.representativeValue,
    ]),
    [
      ["openai/gpt-test", 30, 10, 50],
      ["anthropic/claude-test", 25, 20, 30],
    ],
  );

  const runtimeRows = sortGroupedMetricRowsDescending(
    buildGroupedMetricRows(
      data,
      selectedGroups,
      runtimeMetric,
      "median",
      "both",
    ),
  );
  assert.deepEqual(
    runtimeRows.map((row) => [
      row.id,
      row.sortValue,
      row.modes.text.representativeValue,
      row.modes.json_schema.representativeValue,
    ]),
    [
      ["openai/gpt-test", 50, 40, 60],
      ["anthropic/claude-test", 47.5, 45, 50],
    ],
  );

  const tokenRows = sortGroupedMetricRowsDescending(
    buildTokenUsageRows(data, selectedGroups, "both"),
  );
  assert.deepEqual(
    tokenRows.map((row) => [
      row.id,
      row.sortValue,
      row.modes.text.representativeValue,
      row.modes.json_schema.representativeValue,
    ]),
    [
      ["openai/gpt-test", 10000, 5000, 15000],
      ["anthropic/claude-test", 9000, 8000, 10000],
    ],
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
    ],
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

  const [row] = buildTokenUsageRows(data, ["openai/gpt-test"], "text");

  assert.equal(row.textRepresentativeValue, 200);
  assert.equal(row.textInputTokens, 80);
  assert.equal(row.textVisibleOutputTokens, 100);
  assert.equal(row.textReasoningWithinOutputTokens, 20);
  assert.equal(row.textRawReasoningTokens, 20);
  assert.equal(row.textReasoningOverflowTokens, 0);
  assert.equal(
    row.textInputTokens +
      row.textVisibleOutputTokens +
      row.textReasoningWithinOutputTokens,
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
  assert.equal(noReasoning.textReasoningWithinOutputTokens, 0);
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
  assert.equal(zeroReasoning.textReasoningWithinOutputTokens, 0);
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
  assert.equal(inconsistent.textReasoningWithinOutputTokens, 100);
  assert.equal(inconsistent.textRawReasoningTokens, 120);
  assert.equal(inconsistent.textReasoningOverflowTokens, 20);
  assert.equal(inconsistent.textHasInconsistentReasoningTelemetry, true);
  assert.equal(
    inconsistent.textInputTokens +
      inconsistent.textVisibleOutputTokens +
      inconsistent.textReasoningWithinOutputTokens,
    inconsistent.textRepresentativeValue,
  );
});
