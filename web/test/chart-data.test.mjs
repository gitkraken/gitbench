import assert from "node:assert/strict";
import test from "node:test";

import { buildTokenUsageRows } from "../src/components/charts/model-groups.ts";
import { chartData } from "../src/lib/chart-data.ts";

function cell(passAtK, passed, total) {
  return {
    pass_at_k: passAtK,
    passed,
    total,
    avg_similarity: passAtK,
  };
}

test("heatmap chart data preserves JSON-schema matrix keys", () => {
  const data = chartData("heatmap", {
    models: [
      {
        name: "openai/gpt-test:high",
        provider: "openai",
        baseModel: "gpt-test",
        reasoningLevel: "high",
        output_mode: "text",
      },
      {
        name: "openai/gpt-test:high",
        provider: "openai",
        baseModel: "gpt-test",
        reasoningLevel: "high",
        output_mode: "json_schema",
      },
    ],
    benchmarks: ["commit_messages"],
    model_summaries: {},
    model_runtimes: {},
    model_token_summaries: {},
    matrix: {
      "openai/gpt-test:high": {
        commit_messages: cell(1, 1, 1),
      },
      "openai/gpt-test:high__json_schema": {
        commit_messages: cell(0, 0, 1),
      },
    },
    fixtures: {},
    fixture_index: {},
    runs_meta: [],
    base_model_groups: [],
  });

  assert.deepEqual(data.matrix["openai/gpt-test:high"], [[1, 1, 1]]);
  assert.deepEqual(data.matrix["openai/gpt-test:high__json_schema"], [
    [0, 0, 1],
  ]);
});

const modelKey = "openai/gpt-test:high";

function modelSummary(overrides = {}) {
  return {
    total_runs: 1,
    total_fixtures: 3,
    total_passed: 3,
    pass_at_k: 1,
    total_cost_usd: 9.99,
    avg_cost_usd: 3.33,
    ...overrides,
  };
}

function summaryForScopedTests() {
  return {
    models: [
      {
        name: modelKey,
        provider: "openai",
        baseModel: "gpt-test",
        reasoningLevel: "high",
        output_mode: "text",
      },
    ],
    benchmarks: ["commit_messages", "branch_cleanup"],
    model_summaries: {
      [modelKey]: modelSummary(),
    },
    model_runtimes: {
      [modelKey]: {
        total_ms: 9999,
        avg_ms: 3333,
        min_ms: 1111,
        max_ms: 5555,
        fixture_count: 3,
      },
    },
    model_token_summaries: {
      [modelKey]: {
        input_tokens: 900,
        output_tokens: 450,
        total_tokens: 1350,
        reasoning_tokens: null,
      },
    },
    matrix: {
      [modelKey]: {
        commit_messages: cell(0.5, 1, 2),
        branch_cleanup: cell(1, 1, 1),
      },
    },
    fixtures: {},
    fixture_index: {},
    runs_meta: [],
    base_model_groups: [
      {
        provider: "openai",
        baseModel: "gpt-test",
        levels: [
          {
            level: "high",
            modelName: modelKey,
            pass_at_k: 1,
            total_cost_usd: 9.99,
          },
        ],
      },
    ],
  };
}

function fixtureResult(overrides = {}) {
  return {
    fixture_id: "f001",
    passed: true,
    similarity: 1,
    error: null,
    model_output: "raw model output that must not leak",
    reasoning_level: "high",
    input_tokens: 10,
    output_tokens: 5,
    total_tokens: 15,
    reasoning_tokens: null,
    cost_usd: 0.01,
    duration_ms: 20,
    api_duration_ms: 100,
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

function benchmarkSource() {
  return {
    benchmark: {
      benchmark: "commit_messages",
      tag_counts: {},
      leaderboard: [
        {
          model: modelKey,
          pass_at_k: 0.5,
          total: 2,
          passed: 1,
          avg_similarity: 0.75,
        },
      ],
      fixtures: {},
      results: {
        [modelKey]: {
          commit_messages: [
            fixtureResult({
              fixture_id: "f001",
              passed: true,
              similarity: 1,
              cost_usd: 0.01,
              api_duration_ms: 100,
              input_tokens: 10,
              output_tokens: 5,
              total_tokens: 15,
            }),
            fixtureResult({
              fixture_id: "f002",
              passed: false,
              similarity: 0.5,
              cost_usd: 0.02,
              api_duration_ms: 200,
              input_tokens: 20,
              output_tokens: 10,
              total_tokens: 30,
            }),
          ],
        },
      },
    },
  };
}

test("benchmark scoped chart payloads use fixture rows instead of global totals", () => {
  const scoped = chartData(
    "quadrant",
    summaryForScopedTests(),
    { type: "benchmark", benchmark: "commit_messages" },
    benchmarkSource(),
  );

  assert.equal(scoped.model_summaries[modelKey].pass_at_k, 0.5);
  assert.equal(scoped.model_summaries[modelKey].total_cost_usd, 0.03);
  assert.equal(scoped.model_runtimes[modelKey].total_ms, 300);
  assert.equal(scoped.model_runtimes[modelKey].avg_ms, 150);
  assert.equal(scoped.model_token_summaries[modelKey].total_tokens, 45);
  assert.equal(scoped.matrix[modelKey].commit_messages.pass_at_k, 0.5);
});

test("benchmark scoped token rows bound aggregated reasoning to provider output", () => {
  const source = benchmarkSource();
  source.benchmark.results[modelKey].commit_messages[0].reasoning_tokens = 7;
  source.benchmark.results[modelKey].commit_messages[1].reasoning_tokens = 12;
  const scoped = chartData(
    "tokens",
    summaryForScopedTests(),
    { type: "benchmark", benchmark: "commit_messages" },
    source,
  );

  const [row] = buildTokenUsageRows(scoped, ["openai/gpt-test"], "text");
  assert.equal(row.textRepresentativeValue, 45);
  assert.equal(row.textVisibleOutputTokens, 0);
  assert.equal(row.textReasoningWithinOutputTokens, 15);
  assert.equal(row.textRawReasoningTokens, 19);
  assert.equal(row.textReasoningOverflowTokens, 4);
  assert.equal(
    row.textInputTokens +
      row.textVisibleOutputTokens +
      row.textReasoningWithinOutputTokens,
    row.textRepresentativeValue,
  );
});

test("scoped base model groups do not fall back to global cost totals", () => {
  const scoped = chartData(
    "cost",
    summaryForScopedTests(),
    { type: "benchmark", benchmark: "commit_messages" },
    benchmarkSource(),
  );

  assert.equal(scoped.model_summaries[modelKey].total_cost_usd, 0.03);
  assert.equal(scoped.base_model_groups[0].levels[0].total_cost_usd, 0.03);
});

function fixtureSource(result) {
  return {
    fixture: {
      fixture: {
        id: "f001",
        benchmark: "commit_messages",
        prompt: "prompt",
        expected: "expected",
        description: "description",
        setup: [],
        purpose: "purpose",
        difficulty: "easy",
        tags: [],
      },
      outputs: [{ model: modelKey, ...result }],
    },
  };
}

test("fixture scoped token rows use the shared bounded decomposition", () => {
  const scoped = chartData(
    "tokens",
    summaryForScopedTests(),
    {
      type: "fixture",
      benchmark: "commit_messages",
      fixture: "f001",
    },
    fixtureSource(fixtureResult({ reasoning_tokens: 7 })),
  );

  const [row] = buildTokenUsageRows(scoped, ["openai/gpt-test"], "text");
  assert.equal(row.textRepresentativeValue, 15);
  assert.equal(row.textVisibleOutputTokens, 0);
  assert.equal(row.textReasoningWithinOutputTokens, 5);
  assert.equal(row.textRawReasoningTokens, 7);
  assert.equal(row.textReasoningOverflowTokens, 2);
  assert.equal(
    row.textInputTokens +
      row.textVisibleOutputTokens +
      row.textReasoningWithinOutputTokens,
    row.textRepresentativeValue,
  );
});

test("fixture scoped quality uses repeated campaign success when attempts exist", () => {
  const scoped = chartData(
    "quadrant",
    summaryForScopedTests(),
    {
      type: "fixture",
      benchmark: "commit_messages",
      fixture: "f001",
    },
    {
      attempts: {
        fixture: fixtureSource(fixtureResult()).fixture.fixture,
        campaign_id: "cmp-test",
        campaign_metadata: null,
        groups: [],
        attempts: [
          {
            trial_index: 1,
            model_name: modelKey,
            reasoning_level: "high",
            output_mode: "text",
            benchmark_name: "commit_messages",
            fixture_id: "f001",
            status: "valid_pass",
            passed: true,
            similarity: 1,
            error: null,
            input_tokens: 10,
            output_tokens: 5,
            total_tokens: 15,
            reasoning_tokens: null,
            cost_usd: 0.01,
            api_duration_ms: 100,
          },
          {
            trial_index: 2,
            model_name: modelKey,
            reasoning_level: "high",
            output_mode: "text",
            benchmark_name: "commit_messages",
            fixture_id: "f001",
            status: "valid_fail",
            passed: false,
            similarity: 0,
            error: "bad",
            input_tokens: 10,
            output_tokens: 5,
            total_tokens: 15,
            reasoning_tokens: null,
            cost_usd: 0.01,
            api_duration_ms: 120,
          },
        ],
      },
    },
  );

  assert.equal(scoped.fixture_quality_metric.kind, "repeated_success");
  assert.equal(scoped.fixture_quality_metric.label, "Success (%)");
  assert.equal(scoped.model_summaries[modelKey].pass_at_k, 0.5);
  assert.equal(scoped.model_summaries[modelKey].total_valid_attempts, 2);
  assert.equal(scoped.model_summaries[modelKey].total_passing_attempts, 1);
});

test("fixture scoped quality uses similarity for graded fixture rows", () => {
  const scoped = chartData(
    "quadrant",
    summaryForScopedTests(),
    {
      type: "fixture",
      benchmark: "commit_messages",
      fixture: "f001",
    },
    fixtureSource(
      fixtureResult({
        passed: false,
        similarity: 0.635,
        cost_usd: 0.01,
      }),
    ),
  );

  assert.equal(scoped.fixture_quality_metric.kind, "similarity");
  assert.equal(scoped.fixture_quality_metric.label, "Similarity (%)");
  assert.equal(scoped.model_summaries[modelKey].pass_at_k, 0.635);
});

test("fixture scoped quality uses binary success for pass/fail fixtures", () => {
  const scoped = chartData(
    "quadrant",
    summaryForScopedTests(),
    {
      type: "fixture",
      benchmark: "commit_messages",
      fixture: "f001",
    },
    fixtureSource(
      fixtureResult({
        passed: true,
        similarity: 1,
      }),
    ),
  );

  assert.equal(scoped.fixture_quality_metric.kind, "binary_success");
  assert.equal(scoped.fixture_quality_metric.label, "Success (%)");
  assert.equal(scoped.model_summaries[modelKey].pass_at_k, 1);
});

test("fixture scoped payloads stay compact", () => {
  const scoped = chartData(
    "tokens",
    summaryForScopedTests(),
    {
      type: "fixture",
      benchmark: "commit_messages",
      fixture: "f001",
    },
    fixtureSource(fixtureResult()),
  );

  assert.equal(scoped.model_token_summaries[modelKey].total_tokens, 15);
  assert.equal(JSON.stringify(scoped).includes("raw model output"), false);
});
