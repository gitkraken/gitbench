import assert from "node:assert/strict";
import test from "node:test";

import { createAgentQueryService } from "../src/lib/agent-query-service.ts";
import { ReportClientError } from "../src/lib/report-client.ts";

function summary() {
  return {
    campaign_id: "campaign-1",
    campaign_metadata: null,
    models: [
      {
        name: "z/model:high",
        provider: "z",
        baseModel: "model",
        reasoningLevel: "high",
        output_mode: "text",
      },
      {
        name: "a/model:low",
        provider: "a",
        baseModel: "model",
        reasoningLevel: "low",
        output_mode: "text",
      },
    ],
    benchmarks: ["second", "first"],
    model_summaries: {
      "z/model:high": { pass_at_k: 0.9, total_cost_usd: 2 },
      "a/model:low": { pass_at_k: 0.8, total_cost_usd: 1 },
    },
    model_runtimes: {
      "z/model:high": { total_ms: 2000 },
      "a/model:low": { total_ms: 1000 },
    },
    model_token_summaries: {
      "z/model:high": { total_tokens: 200 },
      "a/model:low": { total_tokens: 100 },
    },
    matrix: {
      "z/model:high": { first: { pass_at_k: 0.9 } },
      "a/model:low": { first: { pass_at_k: 0.8 } },
    },
    fixtures: {},
    fixture_index: {},
    runs_meta: [
      {
        timestamp: "2026-01-01T00:00:00Z",
        model: "z/model:high",
        reasoning_level: "high",
        output_mode: "text",
      },
      {
        timestamp: "2026-01-02T00:00:00Z",
        model: "a/model:low",
        reasoning_level: "low",
        output_mode: "text",
      },
    ],
    base_model_groups: [
      {
        provider: "z",
        baseModel: "model",
        levels: [
          {
            level: "high",
            modelName: "z/model:high",
            pass_at_k: 0.9,
            total_cost_usd: 2,
          },
        ],
      },
      {
        provider: "a",
        baseModel: "model",
        levels: [
          {
            level: "low",
            modelName: "a/model:low",
            pass_at_k: 0.8,
            total_cost_usd: 1,
          },
        ],
      },
    ],
  };
}

function fixtureResult(overrides = {}) {
  return {
    fixture_id: "fixture-1",
    passed: true,
    similarity: 1,
    error: null,
    model_output: "untrusted-output",
    reasoning_level: "high",
    output_mode: "text",
    cost_usd: 0.1,
    api_duration_ms: 100,
    total_tokens: 10,
    parsed_payload: "parsed-value",
    raw_structured_output: "structured-value",
    structured_error: null,
    ...overrides,
  };
}

function dependencies(overrides = {}) {
  const data = summary();
  return {
    loadSummary: async () => data,
    loadModels: async () => ({ models: data.models }),
    loadModelResults: async (model) => ({
      model,
      campaign_id: data.campaign_id,
      campaign_metadata: null,
      results: {
        first: [fixtureResult({ fixture_id: "fixture-2" }), fixtureResult()],
      },
    }),
    loadBenchmark: async (benchmark) => ({
      benchmark,
      tag_counts: { git: 2 },
      leaderboard: [
        { model: "a/model:low", pass_at_k: 0.8, total: 1, passed: 1 },
        { model: "z/model:high", pass_at_k: 0.9, total: 1, passed: 1 },
      ],
      fixtures: {
        "fixture-2": {
          id: "fixture-2",
          benchmark,
          prompt: "hidden",
          expected: "hidden",
          setup: [],
          tags: [],
        },
        "fixture-1": {
          id: "fixture-1",
          benchmark,
          prompt: "hidden",
          expected: "hidden",
          setup: [],
          tags: [],
        },
      },
      results: {},
    }),
    loadFixture: async (benchmark, fixture) => ({
      fixture: {
        id: fixture,
        benchmark,
        prompt: "untrusted-prompt",
        expected: "untrusted-expected",
        setup: [],
        tags: [],
      },
      outputs: [
        { model: "z/model:high", ...fixtureResult() },
        {
          model: "a/model:low",
          ...fixtureResult({ reasoning_level: "low" }),
        },
      ],
    }),
    loadQuadrantChart: async () => data,
    ...overrides,
  };
}

test("the service executes all six operations with stable envelopes and provenance", async () => {
  const service = createAgentQueryService(
    dependencies(),
    "https://example.test",
  );
  const requests = [
    ["overview", { limit: 1 }],
    ["models", { limit: 1 }],
    ["model-results", { model: "z/model:high", limit: 1 }],
    ["benchmark", { benchmark: "first", limit: 1 }],
    ["fixture", { benchmark: "first", fixture: "fixture-1", limit: 1 }],
    ["rank", { benchmark: "first", limit: 1 }],
  ];

  for (const [operation, input] of requests) {
    const result = await service.execute(operation, input);
    assert.equal(result.ok, true, operation);
    assert.match(result.source_url, /^https:\/\/example\.test\//);
    assert.ok(Object.hasOwn(result.data, "campaign_id"), operation);
  }
});

test("pagination is bounded, continued without overlap, and ordered deterministically", async () => {
  const service = createAgentQueryService(dependencies());
  const first = await service.execute("model-results", {
    model: "z/model:high",
    limit: 1,
  });
  const second = await service.execute("model-results", {
    model: "z/model:high",
    offset: first.data.results.next_offset,
    limit: 100,
  });
  assert.equal(first.data.results.items[0].fixture_id, "fixture-1");
  assert.equal(second.data.results.items[0].fixture_id, "fixture-2");
  assert.equal(second.data.results.limit, 50);
  assert.equal(second.data.results.next_offset, null);

  const models = await service.execute("models", {});
  assert.deepEqual(
    models.data.items.map(({ name }) => name),
    ["a/model:low", "z/model:high"],
  );
});

test("evidence is omitted by default, independently bounded, and marked untrusted", async () => {
  const service = createAgentQueryService(dependencies());
  const compact = await service.execute("fixture", {
    benchmark: "first",
    fixture: "fixture-1",
  });
  assert.equal(Object.hasOwn(compact.data.fixture, "prompt"), false);
  assert.equal(
    Object.hasOwn(compact.data.outputs.items[0], "model_output"),
    false,
  );
  assert.equal(Object.hasOwn(compact.data, "untrusted_content"), false);

  const evidence = await service.execute("fixture", {
    benchmark: "first",
    fixture: "fixture-1",
    include_prompt: true,
    include_model_output: true,
    include_structured_output: true,
    evidence_characters: 5,
  });
  assert.equal(evidence.data.untrusted_content, true);
  assert.equal(evidence.data.fixture.prompt.length, 5);
  assert.equal(evidence.data.outputs.items[0].model_output.length, 5);
  assert.equal(evidence.data.outputs.items[0].parsed_payload.length, 5);
});

test("ranking strategies are deterministic and reject invalid choices", async () => {
  const service = createAgentQueryService(dependencies());
  for (const strategy of ["efficiency_ratio", "balanced"]) {
    const one = await service.execute("rank", {
      benchmark: "first",
      strategy,
      resource_metric: "cost",
    });
    const two = await service.execute("rank", {
      benchmark: "first",
      strategy,
      resource_metric: "cost",
    });
    assert.deepEqual(one, two);
    assert.equal(one.data.candidate_count, 2);
  }
  const invalid = await service.execute("rank", {
    benchmark: "first",
    resource_metric: "memory",
  });
  assert.equal(invalid.ok, false);
  assert.equal(invalid.error.category, "invalid_input");
});

test("failure and cancellation envelopes retain stable categories", async () => {
  for (const [error, category] of [
    [new ReportClientError("missing", 404, "/api"), "not_found"],
    [new ReportClientError("down", 503, "/api"), "unavailable"],
    [new Error("query failed"), "query_failure"],
    [new DOMException("cancelled", "AbortError"), "cancelled"],
  ]) {
    const service = createAgentQueryService(
      dependencies({
        loadBenchmark: async () => {
          throw error;
        },
      }),
    );
    const result = await service.execute("benchmark", { benchmark: "first" });
    assert.equal(result.ok, false);
    assert.equal(result.error.category, category);
  }
});
