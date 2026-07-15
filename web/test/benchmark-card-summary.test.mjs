import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  buildBenchmarkCardSummary,
  formatBenchmarkPercent,
} from "../src/lib/benchmark-card-summary.ts";

const BENCHMARK = "commit_messages";

function model(name, outputMode = "text") {
  const cleanName = name.replace(/__json_schema$/, "");
  const [providerAndModel, reasoningLevel] = cleanName.split(":");
  const [provider, baseModel] = providerAndModel.split("/");
  return {
    name,
    provider,
    baseModel,
    reasoningLevel: reasoningLevel ?? null,
    output_mode: outputMode,
  };
}

function cell(passAtK) {
  return {
    pass_at_k: passAtK,
    total: 2,
    passed: Math.round(passAtK * 2),
    avg_similarity: passAtK,
  };
}

function fixtureResult(overrides = {}) {
  return {
    fixture_id: "f001",
    passed: false,
    similarity: 0,
    error: null,
    model_output: "",
    reasoning_level: null,
    input_tokens: null,
    output_tokens: null,
    total_tokens: null,
    reasoning_tokens: null,
    cost_usd: null,
    duration_ms: null,
    api_duration_ms: null,
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

function fixtureRows(passStates, overrides = {}) {
  return passStates.map((passed, index) =>
    fixtureResult({
      fixture_id: `f${String(index + 1).padStart(3, "0")}`,
      passed,
      similarity: passed ? 1 : 0,
      ...overrides,
    }),
  );
}

function data(overrides) {
  return {
    models: [],
    benchmarks: [BENCHMARK],
    model_summaries: {},
    model_runtimes: {},
    model_token_summaries: {},
    matrix: {},
    fixtures: {},
    fixture_index: {},
    runs_meta: [],
    base_model_groups: [],
    ...overrides,
  };
}

test("benchmark card summary shows unique best and worst labels with average score", () => {
  const summary = buildBenchmarkCardSummary(
    data({
      models: [
        model("openai/gpt-a:high"),
        model("openai/gpt-b:low", "json_schema"),
      ],
      matrix: {
        "openai/gpt-a:high": {
          [BENCHMARK]: cell(1),
        },
        "openai/gpt-b:low__json_schema": {
          [BENCHMARK]: cell(1),
        },
      },
      fixtures: {
        "openai/gpt-a:high": {
          [BENCHMARK]: fixtureRows([true, true, true, false]),
        },
        "openai/gpt-b:low__json_schema": {
          [BENCHMARK]: fixtureRows([true, false, false, false], {
            output_mode: "json_schema",
          }),
        },
      },
    }),
    BENCHMARK,
  );

  assert.equal(summary.eligibleScoreCount, 2);
  assert.deepEqual(summary.best, {
    score: 0.75,
    label: "openai/gpt-a",
    modelCount: 1,
    isTie: false,
  });
  assert.deepEqual(summary.worst, {
    score: 0.25,
    label: "openai/gpt-b",
    modelCount: 1,
    isTie: false,
  });
  assert.equal(formatBenchmarkPercent(summary.averageScore), "50.0%");
  assert.doesNotMatch(summary.worst.label, /__json_schema/);
});

test("benchmark card summary scores by fixture pass percentage instead of matrix pass_at_k", () => {
  const summary = buildBenchmarkCardSummary(
    data({
      models: [model("openai/gpt-a:high")],
      matrix: {
        "openai/gpt-a:high": {
          [BENCHMARK]: cell(1),
        },
      },
      fixtures: {
        "openai/gpt-a:high": {
          [BENCHMARK]: fixtureRows([true, false, false, false]),
        },
      },
    }),
    BENCHMARK,
  );

  assert.equal(summary.eligibleScoreCount, 1);
  assert.equal(summary.best.score, 0.25);
  assert.equal(summary.worst.score, 0.25);
  assert.equal(formatBenchmarkPercent(summary.averageScore), "25.0%");
});

test("benchmark card summary renders tied best and worst results as model counts", () => {
  const summary = buildBenchmarkCardSummary(
    data({
      models: [
        model("openai/gpt-a:high"),
        model("openai/gpt-b:high"),
        model("anthropic/claude-a:low"),
        model("anthropic/claude-b:low"),
      ],
      matrix: {
        "openai/gpt-a:high": {
          [BENCHMARK]: cell(1),
        },
        "openai/gpt-b:high": {
          [BENCHMARK]: cell(1),
        },
        "anthropic/claude-a:low": {
          [BENCHMARK]: cell(0.2),
        },
        "anthropic/claude-b:low": {
          [BENCHMARK]: cell(0.2),
        },
      },
      fixtures: {
        "openai/gpt-a:high": {
          [BENCHMARK]: fixtureRows([true, true, true, true, true]),
        },
        "openai/gpt-b:high": {
          [BENCHMARK]: fixtureRows([true, true, true, true, true]),
        },
        "anthropic/claude-a:low": {
          [BENCHMARK]: fixtureRows([true, false, false, false, false]),
        },
        "anthropic/claude-b:low": {
          [BENCHMARK]: fixtureRows([true, false, false, false, false]),
        },
      },
    }),
    BENCHMARK,
  );

  assert.deepEqual(summary.best, {
    score: 1,
    label: "2 models",
    modelCount: 2,
    isTie: true,
  });
  assert.deepEqual(summary.worst, {
    score: 0.2,
    label: "2 models",
    modelCount: 2,
    isTie: true,
  });
  assert.equal(formatBenchmarkPercent(summary.averageScore), "60.0%");
});

test("benchmark card summary counts tied models instead of tied effort levels", () => {
  const summary = buildBenchmarkCardSummary(
    data({
      models: [
        model("openai/gpt-a:low"),
        model("openai/gpt-a:high"),
        model("openai/gpt-b:high"),
        model("anthropic/claude-a:low"),
        model("anthropic/claude-a:high"),
      ],
      matrix: {
        "openai/gpt-a:low": {
          [BENCHMARK]: cell(1),
        },
        "openai/gpt-a:high": {
          [BENCHMARK]: cell(1),
        },
        "openai/gpt-b:high": {
          [BENCHMARK]: cell(1),
        },
        "anthropic/claude-a:low": {
          [BENCHMARK]: cell(0.2),
        },
        "anthropic/claude-a:high": {
          [BENCHMARK]: cell(0.2),
        },
      },
      fixtures: {
        "openai/gpt-a:low": {
          [BENCHMARK]: fixtureRows([true, true, true, true, true]),
        },
        "openai/gpt-a:high": {
          [BENCHMARK]: fixtureRows([true, true, true, true, true]),
        },
        "openai/gpt-b:high": {
          [BENCHMARK]: fixtureRows([true, true, true, true, true]),
        },
        "anthropic/claude-a:low": {
          [BENCHMARK]: fixtureRows([true, false, false, false, false]),
        },
        "anthropic/claude-a:high": {
          [BENCHMARK]: fixtureRows([true, false, false, false, false]),
        },
      },
    }),
    BENCHMARK,
  );

  assert.deepEqual(summary.best, {
    score: 1,
    label: "2 models",
    modelCount: 2,
    isTie: true,
  });
  assert.deepEqual(summary.worst, {
    score: 0.2,
    label: "anthropic/claude-a",
    modelCount: 1,
    isTie: false,
  });
  assert.equal(summary.eligibleScoreCount, 3);
  assert.equal(formatBenchmarkPercent(summary.averageScore), "73.3%");
});

test("benchmark card summary aggregates fixture outcomes across effort levels before ranking models", () => {
  const summary = buildBenchmarkCardSummary(
    data({
      models: [
        model("openai/gpt-a:low"),
        model("openai/gpt-a:high"),
        model("openai/gpt-b:high"),
      ],
      fixtures: {
        "openai/gpt-a:low": {
          [BENCHMARK]: fixtureRows([true, true, true, true]),
        },
        "openai/gpt-a:high": {
          [BENCHMARK]: fixtureRows([false, false, false, false]),
        },
        "openai/gpt-b:high": {
          [BENCHMARK]: fixtureRows([true, true, true, false]),
        },
      },
    }),
    BENCHMARK,
  );

  assert.equal(summary.eligibleScoreCount, 2);
  assert.deepEqual(summary.best, {
    score: 0.75,
    label: "openai/gpt-b",
    modelCount: 1,
    isTie: false,
  });
  assert.deepEqual(summary.worst, {
    score: 0.5,
    label: "openai/gpt-a",
    modelCount: 1,
    isTie: false,
  });
  assert.equal(formatBenchmarkPercent(summary.averageScore), "62.5%");
});

test("benchmark card summary excludes strict unsupported JSON-schema zero scores", () => {
  const unsupportedJson = "openai/gpt-json:high__json_schema";
  const summary = buildBenchmarkCardSummary(
    data({
      models: [
        model("openai/gpt-text:high"),
        model("openai/gpt-json:high", "json_schema"),
      ],
      matrix: {
        "openai/gpt-text:high": {
          [BENCHMARK]: cell(0.5),
        },
        [unsupportedJson]: {
          [BENCHMARK]: cell(0),
        },
      },
      fixtures: {
        "openai/gpt-text:high": {
          [BENCHMARK]: fixtureRows([true, false]),
        },
        [unsupportedJson]: {
          [BENCHMARK]: [
            fixtureResult({
              fixture_id: "f001",
              structured_error: "structured output is not supported",
            }),
            fixtureResult({
              fixture_id: "f002",
              structured_error: "structured output is not supported",
            }),
          ],
        },
      },
    }),
    BENCHMARK,
  );

  assert.equal(summary.eligibleScoreCount, 1);
  assert.equal(summary.best.label, "openai/gpt-text");
  assert.equal(summary.worst.label, "openai/gpt-text");
  assert.equal(formatBenchmarkPercent(summary.averageScore), "50.0%");
});

test("benchmark card summary keeps valid JSON-schema zero scores eligible", () => {
  const validJsonZero = "openai/gpt-json:high__json_schema";
  const summary = buildBenchmarkCardSummary(
    data({
      models: [
        model("openai/gpt-text:high"),
        model("openai/gpt-json:high__json_schema", "json_schema"),
      ],
      matrix: {
        "openai/gpt-text:high": {
          [BENCHMARK]: cell(0.5),
        },
        [validJsonZero]: {
          [BENCHMARK]: cell(0),
        },
      },
      fixtures: {
        "openai/gpt-text:high": {
          [BENCHMARK]: fixtureRows([true, false]),
        },
        [validJsonZero]: {
          [BENCHMARK]: [
            fixtureResult({
              fixture_id: "f001",
              output_mode: "json_schema",
              structured_error: "structured output is not supported",
            }),
            fixtureResult({
              fixture_id: "f002",
              output_mode: "json_schema",
              structured_error: null,
            }),
          ],
        },
      },
    }),
    BENCHMARK,
  );

  assert.equal(summary.eligibleScoreCount, 2);
  assert.deepEqual(summary.worst, {
    score: 0,
    label: "openai/gpt-json",
    modelCount: 1,
    isTie: false,
  });
  assert.equal(formatBenchmarkPercent(summary.averageScore), "25.0%");
});

test("benchmark card summary returns an empty state when no eligible scores remain", () => {
  const unsupportedJson = "openai/gpt-json:high__json_schema";
  const summary = buildBenchmarkCardSummary(
    data({
      models: [model("openai/gpt-json:high", "json_schema")],
      matrix: {
        [unsupportedJson]: {
          [BENCHMARK]: cell(0),
        },
      },
      fixtures: {
        [unsupportedJson]: {
          [BENCHMARK]: [
            fixtureResult({
              output_mode: "json_schema",
              structured_error: "structured output is not supported",
            }),
          ],
        },
      },
    }),
    BENCHMARK,
  );

  assert.equal(summary.eligibleScoreCount, 0);
  assert.equal(summary.best, null);
  assert.equal(summary.worst, null);
  assert.equal(summary.averageScore, null);
});

test("benchmarks page uses summary rows instead of fixture counts", () => {
  const page = readFileSync("src/pages/benchmarks/index.astro", "utf8");

  assert.match(page, /buildBenchmarkCardSummary/);
  assert.match(page, /Best:/);
  assert.match(page, /Worst:/);
  assert.match(page, /Avg:/);
  assert.match(page, /No eligible scores/);
  assert.doesNotMatch(page, /Object\.values\(data\.fixture_index\)/);
  assert.doesNotMatch(page, /\{fixtures\.length\} fixtures/);
});
