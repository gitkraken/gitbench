import assert from "node:assert/strict";
import test from "node:test";

import { createAgentApiHandler } from "../src/lib/agent-api-handler.ts";
import { createGitBenchToolDefinitions } from "../src/lib/webmcp-report-tools.ts";

function dependencies() {
  const summary = {
    campaign_id: "campaign-parity",
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
    benchmarks: ["commit messages"],
    model_summaries: {
      "p/model:high": { pass_at_k: 1, total_cost_usd: 1 },
    },
    model_runtimes: { "p/model:high": { total_ms: 1000 } },
    model_token_summaries: { "p/model:high": { total_tokens: 100 } },
    matrix: { "p/model:high": { "commit messages": { pass_at_k: 1 } } },
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
  const fixtureResult = {
    fixture_id: "fixture/one",
    passed: true,
    similarity: 1,
    error: null,
    model_output: "untrusted output",
    reasoning_level: "high",
    output_mode: "text",
    cost_usd: 1,
    api_duration_ms: 1000,
    total_tokens: 100,
    parsed_payload: "parsed",
    raw_structured_output: "raw",
    structured_error: null,
  };
  return {
    loadSummary: async () => summary,
    loadModels: async () => ({ models: summary.models }),
    loadModelResults: async (model) => ({
      model,
      campaign_id: summary.campaign_id,
      campaign_metadata: null,
      results: { "commit messages": [fixtureResult] },
    }),
    loadBenchmark: async (benchmark) => ({
      benchmark,
      campaign_id: summary.campaign_id,
      tag_counts: {},
      leaderboard: [
        { model: "p/model:high", pass_at_k: 1, total: 1, passed: 1 },
      ],
      fixtures: {
        "fixture/one": {
          id: "fixture/one",
          benchmark,
          prompt: "untrusted prompt",
          expected: "expected",
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
        prompt: "untrusted prompt",
        expected: "expected",
        setup: [],
        tags: [],
      },
      outputs: [{ model: "p/model:high", ...fixtureResult }],
    }),
    loadQuadrantChart: async () => summary,
  };
}

function responseRecorder() {
  return {
    statusCode: 200,
    headers: {},
    body: "",
    status(code) {
      this.statusCode = code;
      return this;
    },
    setHeader(name, value) {
      this.headers[name] = value;
      return this;
    },
    end(body) {
      this.body = body;
    },
  };
}

test("WebMCP results match the v1 API for all equivalent inputs", async () => {
  const deps = dependencies();
  const handler = createAgentApiHandler(() => deps);
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (rawUrl, options) => {
    const url = new URL(rawUrl, "https://gitbench.dev");
    const operation = url.pathname.split("/").at(-1);
    const res = responseRecorder();
    await handler(
      {
        method: "GET",
        query: {
          chart: `agent-${operation}`,
          ...Object.fromEntries(url.searchParams),
        },
        signal: options.signal,
      },
      res,
    );
    return new Response(res.body, {
      status: res.statusCode,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const local = createGitBenchToolDefinitions(deps, "https://gitbench.dev");
    const browser = createGitBenchToolDefinitions();
    const inputs = [
      ["gitbench_get_overview", { limit: 1 }],
      ["gitbench_list_models", { limit: 1 }],
      ["gitbench_get_model_results", { model: "p/model:high" }],
      ["gitbench_get_benchmark", { benchmark: "commit messages" }],
      [
        "gitbench_get_fixture",
        {
          benchmark: "commit messages",
          fixture: "fixture/one",
          include_model_output: true,
          evidence_characters: 8,
        },
      ],
      ["gitbench_rank_models", { benchmark: "commit messages" }],
    ];
    for (const [name, input] of inputs) {
      const localTool = local.find((tool) => tool.name === name);
      const browserTool = browser.find((tool) => tool.name === name);
      assert.deepEqual(
        await browserTool.execute(input),
        JSON.parse(JSON.stringify(await localTool.execute(input))),
        name,
      );
    }

    const localError = await local
      .find((tool) => tool.name === "gitbench_rank_models")
      .execute({ benchmark: "commit messages", resource_metric: "memory" });
    const browserError = await browser
      .find((tool) => tool.name === "gitbench_rank_models")
      .execute({ benchmark: "commit messages", resource_metric: "memory" });
    assert.deepEqual(browserError, JSON.parse(JSON.stringify(localError)));
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("WebMCP cancellation aborts the v1 request and retains its category", async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = (_url, { signal }) =>
    new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () =>
        reject(new DOMException("aborted", "AbortError")),
      );
    });
  try {
    const controller = new AbortController();
    const tool = createGitBenchToolDefinitions().find(
      ({ name }) => name === "gitbench_get_fixture",
    );
    const pending = tool.execute(
      { benchmark: "commit messages", fixture: "fixture/one" },
      { signal: controller.signal },
    );
    controller.abort();
    const result = await pending;
    assert.equal(result.ok, false);
    assert.equal(result.error.category, "cancelled");
  } finally {
    globalThis.fetch = previousFetch;
  }
});
