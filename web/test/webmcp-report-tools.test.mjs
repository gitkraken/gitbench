import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { ReportClientError } from "../src/lib/report-client.ts";
import {
  WEBMCP_LIMITS,
  buildGenerationLookup,
  createGitBenchToolDefinitions,
  evaluationIdentityKey,
  generatedAt,
  gitBenchToolSchemas,
  installGitBenchWebMcpTools,
  rankModels,
  registerGitBenchWebMcpTools,
} from "../src/lib/webmcp-report-tools.ts";

function model(
  name,
  provider,
  baseModel,
  reasoningLevel,
  output_mode = "text",
) {
  return { name, provider, baseModel, reasoningLevel, output_mode };
}

function emptySummary() {
  return {
    models: [],
    benchmarks: [],
    model_summaries: {},
    model_runtimes: {},
    model_token_summaries: {},
    matrix: {},
    fixtures: {},
    fixture_index: {},
    runs_meta: [],
    base_model_groups: [],
    campaign_id: null,
    campaign_metadata: null,
  };
}

function rankingData() {
  const data = emptySummary();
  data.benchmarks = ["commits"];
  data.models = [
    model("openai/a:low", "openai", "a", "low"),
    model("openai/a:high", "openai", "a", "high"),
    model("openai/a:high", "openai", "a", "high", "json_schema"),
    model("anthropic/b:medium", "anthropic", "b", "medium"),
    model("google/c:high", "google", "c", "high"),
  ];
  data.model_summaries = {
    "openai/a:low": { pass_at_k: 0.6, total_cost_usd: 1 },
    "openai/a:high": { pass_at_k: 0.9, total_cost_usd: 3 },
    "openai/a:high__json_schema": { pass_at_k: 0.8, total_cost_usd: 2 },
    "anthropic/b:medium": { pass_at_k: 0.8, total_cost_usd: 2 },
    "google/c:high": { pass_at_k: 0.95, total_cost_usd: 0 },
  };
  data.matrix = Object.fromEntries(
    Object.entries(data.model_summaries).map(([key, summary]) => [
      key,
      {
        commits: {
          pass_at_k: summary.pass_at_k,
          total: 10,
          passed: 8,
          avg_similarity: summary.pass_at_k,
        },
      },
    ]),
  );
  data.model_runtimes = {
    "openai/a:low": {
      total_ms: 4_000,
      avg_ms: 400,
      min_ms: 300,
      max_ms: 500,
      fixture_count: 10,
    },
    "openai/a:high": {
      total_ms: 10_000,
      avg_ms: 1_000,
      min_ms: 900,
      max_ms: 1_100,
      fixture_count: 10,
    },
    "openai/a:high__json_schema": {
      total_ms: 8_000,
      avg_ms: 800,
      min_ms: 700,
      max_ms: 900,
      fixture_count: 10,
    },
    "anthropic/b:medium": {
      total_ms: 8_000,
      avg_ms: 800,
      min_ms: 700,
      max_ms: 900,
      fixture_count: 10,
    },
  };
  data.model_token_summaries = {
    "openai/a:low": {
      input_tokens: 60,
      output_tokens: 40,
      total_tokens: 100,
      reasoning_tokens: null,
    },
    "openai/a:high": {
      input_tokens: 120,
      output_tokens: 80,
      total_tokens: 200,
      reasoning_tokens: 20,
    },
    "openai/a:high__json_schema": {
      input_tokens: 90,
      output_tokens: 60,
      total_tokens: 150,
      reasoning_tokens: 10,
    },
    "anthropic/b:medium": {
      input_tokens: 90,
      output_tokens: 60,
      total_tokens: 150,
      reasoning_tokens: 10,
    },
  };
  data.base_model_groups = [
    {
      provider: "openai",
      baseModel: "a",
      levels: [
        {
          level: "low",
          modelName: "openai/a:low",
          pass_at_k: 0.6,
          total_cost_usd: 1,
        },
        {
          level: "high",
          modelName: "openai/a:high",
          pass_at_k: 0.9,
          total_cost_usd: 3,
        },
        {
          level: "high",
          modelName: "openai/a:high__json_schema",
          pass_at_k: 0.8,
          total_cost_usd: 2,
        },
      ],
    },
    {
      provider: "anthropic",
      baseModel: "b",
      levels: [
        {
          level: "medium",
          modelName: "anthropic/b:medium",
          pass_at_k: 0.8,
          total_cost_usd: 2,
        },
      ],
    },
    {
      provider: "google",
      baseModel: "c",
      levels: [
        {
          level: "high",
          modelName: "google/c:high",
          pass_at_k: 0.95,
          total_cost_usd: 0,
        },
      ],
    },
  ];
  return data;
}

function fixtureResult(overrides = {}) {
  return {
    fixture_id: "fix-1",
    passed: true,
    similarity: 1,
    error: null,
    model_output: "model says " + "x".repeat(100),
    reasoning_level: "high",
    input_tokens: 10,
    output_tokens: 20,
    total_tokens: 30,
    reasoning_tokens: 5,
    cost_usd: 0.01,
    duration_ms: 100,
    api_duration_ms: 90,
    purpose: "test",
    difficulty: "easy",
    tags: ["tag"],
    output_mode: "text",
    parsed_payload: "parsed " + "p".repeat(100),
    raw_structured_output: "raw " + "r".repeat(100),
    structured_error: null,
    ...overrides,
  };
}

function dependencies(overrides = {}) {
  const summary = rankingData();
  summary.runs_meta = [
    {
      timestamp: "2026-01-01",
      model: "openai/a:high",
      reasoning_level: "high",
      output_mode: "text",
    },
    {
      timestamp: "2026-01-02",
      model: "openai/a:high",
      reasoning_level: "high",
      output_mode: "json_schema",
    },
  ];
  return {
    loadSummary: async () => summary,
    loadModels: async () => ({ models: summary.models }),
    loadModelResults: async (requestedModel) => ({
      model: requestedModel,
      campaign_id: null,
      campaign_metadata: null,
      results: { commits: [fixtureResult()] },
    }),
    loadBenchmark: async (benchmark) => ({
      benchmark,
      tag_counts: { tag: 1 },
      leaderboard: [
        {
          model: "openai/a:high",
          pass_at_k: 1,
          total: 1,
          passed: 1,
          avg_similarity: 1,
        },
      ],
      fixtures: {
        "fix-1": {
          id: "fix-1",
          benchmark,
          prompt: "do not expose",
          expected: "secret",
          description: "fixture",
          setup: ["secret setup"],
          purpose: "test",
          difficulty: "easy",
          tags: ["tag"],
        },
      },
      results: {},
    }),
    loadFixture: async (benchmark, fixture) => ({
      fixture: {
        id: fixture,
        benchmark,
        prompt: "prompt " + "q".repeat(100),
        expected: "expected " + "e".repeat(100),
        description: "fixture",
        setup: [],
        purpose: "test",
        difficulty: "easy",
        tags: ["tag"],
      },
      outputs: [
        { model: "openai/a:high", ...fixtureResult({ fixture_id: fixture }) },
      ],
    }),
    loadQuadrantChart: async () => summary,
    ...overrides,
  };
}

function tool(name, deps = dependencies()) {
  return createGitBenchToolDefinitions(deps, "https://example.test").find(
    (candidate) => candidate.name === name,
  );
}

test("the six stable schemas are strict, bounded, campaign-free, and read only", () => {
  const definitions = createGitBenchToolDefinitions(
    dependencies(),
    "https://example.test",
  );
  assert.deepEqual(
    definitions.map(({ name }) => name),
    [
      "gitbench_get_overview",
      "gitbench_list_models",
      "gitbench_get_model_results",
      "gitbench_get_benchmark",
      "gitbench_get_fixture",
      "gitbench_rank_models",
    ],
  );
  for (const definition of definitions) {
    assert.equal(definition.inputSchema.type, "object");
    assert.equal(definition.inputSchema.additionalProperties, false);
    assert.equal(
      Object.hasOwn(definition.inputSchema.properties ?? {}, "campaign"),
      false,
    );
    assert.equal(definition.annotations.readOnlyHint, true);
  }
  assert.equal(
    gitBenchToolSchemas.models.properties.limit.maximum,
    WEBMCP_LIMITS.listMaximum,
  );
  assert.deepEqual(gitBenchToolSchemas.ranking.required, ["benchmark"]);
  assert.equal(
    tool("gitbench_get_model_results").annotations.untrustedContentHint,
    true,
  );
  assert.equal(
    tool("gitbench_get_fixture").annotations.untrustedContentHint,
    true,
  );
});

test("overview and model catalog delegate, bound results, and return canonical sources", async () => {
  let summaryCalls = 0;
  let modelCalls = 0;
  const deps = dependencies({
    loadSummary: async () => {
      summaryCalls += 1;
      return rankingData();
    },
    loadModels: async () => {
      modelCalls += 1;
      return {
        models: Array.from({ length: 60 }, (_, index) =>
          model(`p/m:${index}`, "p", "m", String(index)),
        ),
      };
    },
  });
  const overview = await tool("gitbench_get_overview", deps).execute({});
  const models = await tool("gitbench_list_models", deps).execute({
    limit: 999,
  });
  assert.equal(summaryCalls, 1);
  assert.equal(modelCalls, 1);
  assert.equal(overview.source_url, "https://example.test/");
  assert.ok(Object.hasOwn(overview.data.leading_models, "next_offset"));
  assert.equal(models.source_url, "https://example.test/models");
  assert.equal(models.data.items.length, 50);
  assert.equal(models.data.truncated, true);
  assert.equal(models.data.next_offset, 50);
});

test("overview resolves provenance for suffixed JSON-schema catalog identities", async () => {
  const summary = rankingData();
  const jsonModel = summary.models.find(
    ({ output_mode }) => output_mode === "json_schema",
  );
  jsonModel.name = `${jsonModel.name}__json_schema`;
  summary.runs_meta = [
    {
      timestamp: "json-generated",
      model: "openai/a:high",
      reasoning_level: "high",
      output_mode: "json_schema",
    },
  ];
  const overview = await tool(
    "gitbench_get_overview",
    dependencies({ loadSummary: async () => summary }),
  ).execute({ limit: 50 });
  const jsonLeader = overview.data.leading_models.items.find(
    ({ model }) => model === "openai/a:high__json_schema",
  );
  assert.equal(jsonLeader.generated_at, "json-generated");
});

test("cancelling a pending execution aborts the underlying report fetch", async () => {
  const previousFetch = globalThis.fetch;
  const controller = new AbortController();
  let receivedSignal;
  globalThis.fetch = (_url, options) =>
    new Promise((_resolve, reject) => {
      receivedSignal = options.signal;
      options.signal.addEventListener("abort", () => {
        reject(new DOMException("aborted", "AbortError"));
      });
    });
  try {
    const definition = createGitBenchToolDefinitions().find(
      ({ name }) => name === "gitbench_list_models",
    );
    const pending = definition.execute({}, { signal: controller.signal });
    controller.abort();
    const result = await pending;
    assert.equal(receivedSignal, controller.signal);
    assert.equal(result.error.category, "cancelled");
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("the WebMCP integration never fetches the full compatibility artifact", () => {
  const adapter = readFileSync(
    new URL("../src/lib/webmcp-report-tools.ts", import.meta.url),
    "utf8",
  );
  const layout = readFileSync(
    new URL("../src/components/Layout.astro", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(adapter, /fetch\([^)]*results\.json/);
  assert.doesNotMatch(layout, /fetch\([^)]*results\.json/);
});

test("model results forward filters and signal while raw output stays opt-in and bounded", async () => {
  const controller = new AbortController();
  let delegated;
  const deps = dependencies({
    loadModelResults: async (requestedModel, filters, signal) => {
      delegated = { requestedModel, filters, signal };
      return {
        model: requestedModel,
        campaign_id: null,
        campaign_metadata: null,
        results: { commits: [fixtureResult()] },
      };
    },
  });
  const definition = tool("gitbench_get_model_results", deps);
  const compact = await definition.execute(
    {
      model: "openai/a:high",
      benchmark: "commits",
      difficulty: "easy",
      tag: "tag",
      output_mode: "text",
    },
    { signal: controller.signal },
  );
  assert.deepEqual(delegated.filters, {
    benchmark: "commits",
    difficulty: "easy",
    tag: "tag",
    output_mode: "text",
  });
  assert.equal(delegated.signal, controller.signal);
  assert.equal(
    Object.hasOwn(compact.data.results.items[0], "model_output"),
    false,
  );
  const evidence = await definition.execute({
    model: "openai/a:high",
    include_model_output: true,
    evidence_characters: 10,
  });
  assert.equal(evidence.data.results.items[0].model_output.length, 10);
  assert.ok(evidence.data.results.items[0].model_output.endsWith("…"));
  assert.equal(evidence.data.results.items[0].generated_at, "2026-01-01");
});

test("benchmark and fixture projections omit raw evidence by default and expose bounded opt-ins", async () => {
  const benchmark = await tool("gitbench_get_benchmark").execute({
    benchmark: "commits",
  });
  assert.equal(benchmark.source_url, "https://example.test/benchmarks/commits");
  assert.equal(
    benchmark.data.leaderboard.items[0].generated_at,
    "2026-01-01",
  );
  assert.equal(
    Object.hasOwn(benchmark.data.fixtures.items[0], "prompt"),
    false,
  );
  assert.equal(
    Object.hasOwn(benchmark.data.fixtures.items[0], "expected"),
    false,
  );
  const compact = await tool("gitbench_get_fixture").execute({
    benchmark: "commits",
    fixture: "fix-1",
  });
  assert.equal(Object.hasOwn(compact.data.fixture, "prompt"), false);
  assert.equal(
    Object.hasOwn(compact.data.outputs.items[0], "model_output"),
    false,
  );
  assert.equal(
    Object.hasOwn(compact.data.outputs.items[0], "parsed_payload"),
    false,
  );
  const evidence = await tool("gitbench_get_fixture").execute({
    benchmark: "commits",
    fixture: "fix-1",
    include_prompt: true,
    include_expected: true,
    include_model_output: true,
    include_structured_output: true,
    evidence_characters: 12,
  });
  assert.equal(evidence.data.fixture.prompt.length, 12);
  assert.equal(evidence.data.fixture.expected.length, 12);
  assert.equal(evidence.data.outputs.items[0].model_output.length, 12);
  assert.equal(evidence.data.outputs.items[0].raw_structured_output.length, 12);
});

test("tool failures use stable invalid, not-found, unavailable, query, and cancellation categories", async () => {
  const invalid = await tool("gitbench_get_benchmark").execute({});
  assert.equal(invalid.error.category, "invalid_input");
  for (const [error, expected] of [
    [new ReportClientError("missing", 404, "/api/x"), "not_found"],
    [new ReportClientError("offline", 503, "/api/x"), "unavailable"],
    [new Error("bad query"), "query_failure"],
    [new DOMException("aborted", "AbortError"), "cancelled"],
  ]) {
    const result = await tool(
      "gitbench_get_benchmark",
      dependencies({
        loadBenchmark: async () => {
          throw error;
        },
      }),
    ).execute({ benchmark: "commits" });
    assert.equal(result.error.category, expected);
  }
});

test("provenance keys exact model, reasoning, and output identities and rejects ambiguity", () => {
  const runs = [
    {
      timestamp: "shared",
      model: "p/a:high",
      reasoning_level: "high",
      output_mode: "text",
    },
    {
      timestamp: "shared",
      model: "p/b:high",
      reasoning_level: "high",
      output_mode: "text",
    },
    {
      timestamp: "json",
      model: "p/a:high",
      reasoning_level: "high",
      output_mode: "json_schema",
    },
    {
      timestamp: "first",
      model: "p/c:low",
      reasoning_level: "low",
      output_mode: "text",
    },
    {
      timestamp: "second",
      model: "p/c:low",
      reasoning_level: "low",
      output_mode: "text",
    },
  ];
  const lookup = buildGenerationLookup(runs);
  assert.notEqual(
    evaluationIdentityKey("p/a:high", "high", "text"),
    evaluationIdentityKey("p/a:high__json_schema", "high", undefined),
  );
  assert.equal(generatedAt(lookup, "p/a:high", "high", "text"), "shared");
  assert.equal(generatedAt(lookup, "p/b:high", "high", "text"), "shared");
  assert.equal(
    generatedAt(lookup, "p/a:high__json_schema", "high", undefined),
    "json",
  );
  assert.equal(generatedAt(lookup, "p/c:low", "low", "text"), null);
  assert.equal(generatedAt(lookup, "missing", null, "text"), null);
});

test("efficiency rankings support all resources, quality thresholds, output modes, ties, and unusable values", () => {
  const data = rankingData();
  for (const metric of ["cost", "api_time", "tokens"]) {
    const ranked = rankModels(
      data,
      "commits",
      metric,
      "efficiency_ratio",
      "both",
      0,
    );
    assert.ok(ranked.entries.length >= 2);
    assert.ok(ranked.entries.every((entry) => entry.resource > 0));
    assert.ok(
      ranked.entries.every(
        (entry, index, entries) =>
          index === 0 ||
          entries[index - 1].ranking_score >= entry.ranking_score,
      ),
    );
  }
  const text = rankModels(
    data,
    "commits",
    "cost",
    "efficiency_ratio",
    "text",
    0.7,
  );
  assert.ok(
    text.entries.every(
      (entry) => entry.output_mode === "text" && entry.quality >= 0.7,
    ),
  );
  assert.equal(text.excluded_unusable_resource, 1);
  assert.ok(text.excluded_below_quality >= 1);
  const json = rankModels(
    data,
    "commits",
    "cost",
    "efficiency_ratio",
    "json_schema",
    0,
  );
  assert.deepEqual(
    json.entries.map((entry) => entry.output_mode),
    ["json_schema"],
  );
  assert.deepEqual(
    rankModels(data, "commits", "cost", "efficiency_ratio", "text", 0)
      .entries.filter((entry) => entry.ranking_score === 0.4)
      .map((entry) => entry.model),
    ["anthropic/b:medium"],
  );
});

test("balanced ranking normalizes the eligible cohort and picks one effort per base model and mode", () => {
  const data = rankingData();
  const broad = rankModels(data, "commits", "cost", "balanced", "both", 0);
  const narrow = rankModels(data, "commits", "cost", "balanced", "both", 0.8);
  assert.equal(
    broad.entries.filter(
      (entry) => entry.pair_id === "openai/a" && entry.output_mode === "text",
    ).length,
    1,
  );
  assert.ok(
    broad.entries.every(
      (entry) => entry.quality_score >= 0 && entry.quality_score <= 1,
    ),
  );
  assert.notDeepEqual(
    broad.entries.map((entry) => entry.ranking_score),
    narrow.entries.map((entry) => entry.ranking_score),
  );
  assert.equal(
    broad.entries.some((entry) => entry.model === "google/c:high"),
    false,
  );
  assert.ok(broad.excluded_unusable_resource >= 1);
});

test("ranking tool reports counts, pagination, raw evidence, and per-result provenance", async () => {
  const result = await tool("gitbench_rank_models").execute({
    benchmark: "commits",
    resource_metric: "cost",
    strategy: "balanced",
    limit: 1,
  });
  assert.equal(result.ok, true);
  assert.equal(result.data.ranking.items.length, 1);
  assert.equal(result.data.ranking.truncated, true);
  assert.ok(result.data.candidate_count > result.data.selected_candidate_count);
  const entry = result.data.ranking.items[0];
  assert.equal(typeof entry.quality, "number");
  assert.equal(typeof entry.resource, "number");
  assert.equal(typeof entry.ranking_score, "number");
  assert.ok(Object.hasOwn(entry, "generated_at"));
});

test("registration is progressive, cleans up all tools, handles rejection, and passes registration signals", async () => {
  const unsupportedCleanup = await registerGitBenchWebMcpTools({});
  assert.doesNotThrow(unsupportedCleanup);

  const registrations = [];
  const target = {
    defaultView: { isSecureContext: true },
    modelContext: {
      registerTool(definition, options) {
        registrations.push({ definition, options });
      },
    },
  };
  const cleanup = await registerGitBenchWebMcpTools(target, dependencies());
  assert.equal(registrations.length, 6);
  assert.ok(
    registrations.every(({ options }) => options.signal.aborted === false),
  );
  cleanup();
  assert.ok(
    registrations.every(({ options }) => options.signal.aborted === true),
  );

  const previousDebug = console.debug;
  console.debug = () => {};
  try {
    const rejected = [];
    const rejectedCleanup = await registerGitBenchWebMcpTools(
      {
        modelContext: {
          registerTool(_definition, options) {
            rejected.push(options.signal);
            return Promise.reject(
              new DOMException("disabled", "NotAllowedError"),
            );
          },
        },
      },
      dependencies(),
    );
    assert.ok(rejected.every((signal) => signal.aborted));
    assert.doesNotThrow(rejectedCleanup);
  } finally {
    console.debug = previousDebug;
  }
});

test("installation preserves tools in bfcache and cleans up discarded pages", async () => {
  const registrations = [];
  const listeners = new Map();
  const lifecycle = {
    addEventListener(type, listener) {
      listeners.set(type, listener);
    },
    removeEventListener(type, listener) {
      if (listeners.get(type) === listener) listeners.delete(type);
    },
  };
  const target = {
    defaultView: { isSecureContext: true },
    modelContext: {
      registerTool(_definition, options) {
        registrations.push(options.signal);
      },
    },
  };

  installGitBenchWebMcpTools(target, lifecycle, dependencies());
  await new Promise((resolve) => setImmediate(resolve));
  listeners.get("pagehide")({ persisted: true });
  assert.ok(registrations.every((signal) => signal.aborted === false));
  assert.equal(listeners.has("pagehide"), true);

  listeners.get("pagehide")({ persisted: false });
  assert.ok(registrations.every((signal) => signal.aborted === true));
  assert.equal(listeners.has("pagehide"), false);
});
