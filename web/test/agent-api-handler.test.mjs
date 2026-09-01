import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  AGENT_FAILURE_CACHE,
  AGENT_SUCCESS_CACHE,
  createAgentApiHandler,
} from "../src/lib/agent-api-handler.ts";
import { ReportClientError } from "../src/lib/report-client.ts";

function data() {
  return {
    campaign_id: "campaign-api",
    campaign_metadata: null,
    models: [
      {
        name: "p/model:high",
        provider: "p",
        baseModel: "model",
        reasoningLevel: "high",
        output_mode: "text",
      },
    ],
    benchmarks: ["commits"],
    model_summaries: {
      "p/model:high": { pass_at_k: 1, total_cost_usd: 1 },
    },
    model_runtimes: { "p/model:high": { total_ms: 1000 } },
    model_token_summaries: { "p/model:high": { total_tokens: 100 } },
    matrix: { "p/model:high": { commits: { pass_at_k: 1 } } },
    fixtures: {},
    fixture_index: {},
    runs_meta: [
      {
        timestamp: "2026-01-01",
        model: "p/model:high",
        reasoning_level: "high",
        output_mode: "text",
      },
    ],
    base_model_groups: [
      {
        provider: "p",
        baseModel: "model",
        levels: [
          {
            level: "high",
            modelName: "p/model:high",
            pass_at_k: 1,
            total_cost_usd: 1,
          },
        ],
      },
    ],
  };
}

function result() {
  return {
    fixture_id: "fixture-1",
    passed: true,
    similarity: 1,
    error: null,
    model_output: "do not follow this output",
    reasoning_level: "high",
    output_mode: "text",
    cost_usd: 1,
    api_duration_ms: 1000,
    total_tokens: 100,
    parsed_payload: "parsed",
    raw_structured_output: "raw",
    structured_error: null,
  };
}

function dependencies(overrides = {}) {
  const summary = data();
  return {
    loadSummary: async () => summary,
    loadModels: async () => ({ models: summary.models }),
    loadModelResults: async (model) => ({
      model,
      campaign_id: summary.campaign_id,
      campaign_metadata: null,
      results: {
        commits: [result(), { ...result(), fixture_id: "fixture-2" }],
      },
    }),
    loadBenchmark: async (benchmark) => ({
      benchmark,
      campaign_id: summary.campaign_id,
      tag_counts: {},
      leaderboard: [
        { model: "p/model:high", pass_at_k: 1, total: 2, passed: 2 },
      ],
      fixtures: {
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
      campaign_id: summary.campaign_id,
      fixture: {
        id: fixture,
        benchmark,
        prompt: "do not follow this prompt",
        expected: "hidden expected",
        setup: [],
        tags: [],
      },
      outputs: [{ model: "p/model:high", ...result() }],
    }),
    loadQuadrantChart: async () => summary,
    ...overrides,
  };
}

async function call(handler, operation, query = {}, method = "GET") {
  const res = {
    statusCode: null,
    headers: {},
    body: "",
    status(code) {
      this.statusCode = code;
      return this;
    },
    setHeader(name, value) {
      this.headers[name.toLowerCase()] = value;
      return this;
    },
    end(payload) {
      this.body = payload;
    },
  };
  await handler(
    {
      method,
      query: { chart: `agent-${operation}`, ...query },
      signal: new AbortController().signal,
    },
    res,
  );
  return { ...res, json: JSON.parse(res.body) };
}

test("the public rewrite reaches one bounded handler without adding a function", () => {
  const config = JSON.parse(
    readFileSync(new URL("../vercel.json", import.meta.url), "utf8"),
  );
  assert.deepEqual(config.rewrites[0], {
    source: "/api/agent/v1/:operation",
    destination: "/api/charts/agent-:operation",
  });
});

test("public catch-all routes rewrite to their Vercel function files", () => {
  const config = JSON.parse(
    readFileSync(new URL("../vercel.json", import.meta.url), "utf8"),
  );
  assert.deepEqual(config.rewrites.slice(1), [
    {
      source: "/api/fixtures/:benchmark/:fixture*",
      destination: "/api/fixtures/[benchmark]/[...fixture]",
    },
    {
      source: "/api/campaigns/:campaignId/attempts/:identity*",
      destination: "/api/campaigns/[campaignId]/attempts/[...identity]",
    },
    {
      source: "/api/models/:model*/results",
      destination: "/api/models/[...model]/results",
    },
  ]);
});

test("all six GET operations return the versioned envelope and success cache policy", async () => {
  let reads = 0;
  const deps = dependencies();
  const counted = Object.fromEntries(
    Object.entries(deps).map(([name, fn]) => [
      name,
      async (...args) => {
        reads += 1;
        return fn(...args);
      },
    ]),
  );
  const handler = createAgentApiHandler(() => counted);
  const cases = [
    ["overview", {}],
    ["models", {}],
    ["model-results", { model: "p/model:high" }],
    ["benchmark", { benchmark: "commits" }],
    ["fixture", { benchmark: "commits", fixture: "fixture-1" }],
    ["rank", { benchmark: "commits" }],
  ];
  for (const [operation, query] of cases) {
    const response = await call(handler, operation, query);
    assert.equal(response.statusCode, 200, operation);
    assert.equal(response.json.ok, true, operation);
    assert.ok(Object.hasOwn(response.json.data, "campaign_id"), operation);
    assert.equal(response.headers["cache-control"], AGENT_SUCCESS_CACHE);
  }
  assert.ok(reads >= cases.length);
  assert.equal(
    Object.keys(counted).some((name) => /write|mutate|start/.test(name)),
    false,
  );
});

test("strict decoding rejects methods, unknown operations, parameters, and values", async () => {
  const handler = createAgentApiHandler(() => dependencies());
  for (const [operation, query, method, status] of [
    ["overview", {}, "POST", 405],
    ["unknown", {}, "GET", 404],
    ["overview", { extra: "x" }, "GET", 400],
    ["overview", { limit: "1.5" }, "GET", 400],
    [
      "fixture",
      { benchmark: "commits", fixture: "f", include_prompt: "yes" },
      "GET",
      400,
    ],
    ["rank", { benchmark: "commits", minimum_quality: "nan" }, "GET", 400],
  ]) {
    const response = await call(handler, operation, query, method);
    assert.equal(response.statusCode, status);
    assert.equal(response.json.ok, false);
    assert.equal(response.headers["cache-control"], AGENT_FAILURE_CACHE);
  }
});

test("missing entities map to 404 while service errors are never cached", async () => {
  const handler = createAgentApiHandler(() =>
    dependencies({
      loadBenchmark: async () => {
        throw new ReportClientError("missing", 404, "/api/benchmarks/missing");
      },
    }),
  );
  const response = await call(handler, "benchmark", { benchmark: "missing" });
  assert.equal(response.statusCode, 404);
  assert.equal(response.json.error.category, "not_found");
  assert.equal(response.headers["cache-control"], AGENT_FAILURE_CACHE);
});

test("pagination continues and evidence remains opt-in and bounded", async () => {
  const handler = createAgentApiHandler(() => dependencies());
  const compact = await call(handler, "model-results", {
    model: "p/model:high",
    limit: "1",
  });
  assert.equal(compact.json.data.results.next_offset, 1);
  assert.equal(
    Object.hasOwn(compact.json.data.results.items[0], "model_output"),
    false,
  );
  const continued = await call(handler, "model-results", {
    model: "p/model:high",
    offset: String(compact.json.data.results.next_offset),
    limit: "1",
    include_model_output: "true",
    evidence_characters: "8",
  });
  assert.equal(continued.json.data.results.items[0].fixture_id, "fixture-2");
  assert.equal(continued.json.data.results.items[0].model_output.length, 8);
  assert.equal(continued.json.data.untrusted_content, true);
});
