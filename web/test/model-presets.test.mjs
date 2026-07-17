import assert from "node:assert/strict";
import test from "node:test";

import {
  attachModelPresets,
  resolveModelPresets,
  topPerformerGroupIds,
} from "../src/lib/model-presets.ts";
import { chartData } from "../src/lib/chart-data.ts";

function group(id, textRates = [], jsonRates = []) {
  const [provider, ...baseParts] = id.split("/");
  const baseModel = baseParts.join("/");
  return {
    provider,
    baseModel,
    levels: [
      ...textRates.map((pass_at_k, index) => ({
        level: `text-${index}`,
        modelName: `${id}:text-${index}`,
        pass_at_k,
        total_cost_usd: null,
      })),
      ...jsonRates.map((pass_at_k, index) => ({
        level: `json-${index}`,
        modelName: `${id}:json-${index}__json_schema`,
        pass_at_k,
        total_cost_usd: null,
      })),
    ],
  };
}

function metadata(id, contextWindowTokens, weightAccess) {
  return {
    canonicalId: id,
    contextWindowTokens,
    weightAccess,
    openRouterId: id,
    huggingFaceId: null,
    provenance: {
      contextWindowTokens: contextWindowTokens === null ? "unresolved" : "openrouter",
      weightAccess: weightAccess === "unknown" ? "unresolved" : "override",
    },
    fetchedAt: "2026-07-16T00:00:00.000Z",
  };
}

test("Top Performers uses distinct per-mode medians and cross-mode averaging", () => {
  const summary = {
    base_model_groups: [
      group("provider/a", [0.2, 0.2, 0.8], [0.6]),
      group("provider/b", [0.54]),
      group("provider/unmeasurable"),
    ],
  };
  assert.deepEqual(topPerformerGroupIds(summary), ["provider/a", "provider/b"]);
});

test("Top Performers returns exactly 20 and breaks score ties by canonical ID", () => {
  const summary = {
    base_model_groups: Array.from({ length: 25 }, (_, index) =>
      group(`provider/model-${String(index).padStart(2, "0")}`, [0.5]),
    ).reverse(),
  };
  const ids = topPerformerGroupIds(summary);
  assert.equal(ids.length, 20);
  assert.deepEqual(ids, [...ids].sort((a, b) => a.localeCompare(b)));
  assert.equal(ids.at(-1), "provider/model-19");
});

test("metadata presets enforce frontier, open-weight, unknown, and context boundaries", () => {
  const ids = [
    "openai/closed",
    "openai/open",
    "anthropic/unknown",
    "other/closed",
    "other/a",
    "other/b",
    "other/c",
    "other/d",
    "other/unknown-context",
  ];
  const summary = { base_model_groups: ids.map((id) => group(id, [0.5])) };
  const catalog = {
    "openai/closed": metadata("openai/closed", 200000, "closed"),
    "openai/open": metadata("openai/open", 200001, "open"),
    "anthropic/unknown": metadata("anthropic/unknown", 499999, "unknown"),
    "other/closed": metadata("other/closed", 500000, "closed"),
    "other/a": metadata("other/a", 999999, "open"),
    "other/b": metadata("other/b", 1000000, "open"),
    "other/c": metadata("other/c", 0, "open"),
    "other/d": metadata("other/d", 200000, "open"),
    "other/unknown-context": metadata("other/unknown-context", null, "unknown"),
  };
  const presets = Object.fromEntries(
    resolveModelPresets(summary, catalog).map((preset) => [preset.id, preset.modelGroupIds]),
  );

  assert.deepEqual(presets["frontier-models"], ["openai/closed"]);
  assert.deepEqual(presets["open-weights"], [
    "openai/open",
    "other/a",
    "other/b",
    "other/c",
    "other/d",
  ]);
  assert.deepEqual(presets["context-up-to-200k"], ["openai/closed", "other/c", "other/d"]);
  assert.deepEqual(presets["context-200k-499k"], ["anthropic/unknown", "openai/open"]);
  assert.deepEqual(presets["context-500k-999k"], ["other/a", "other/closed"]);
  assert.deepEqual(presets["context-1m-plus"], ["other/b"]);
});

test("context preset labels identify their ranges as context windows", () => {
  const presets = resolveModelPresets({ base_model_groups: [] }, {});
  const contextLabels = presets
    .filter((preset) => preset.id.startsWith("context-"))
    .map((preset) => preset.label);

  assert.deepEqual(contextLabels, [
    "Context: Up to 200K",
    "Context: 200K–499K",
    "Context: 500K–999K",
    "Context: 1M+",
  ]);
});

test("global and scoped chart payloads retain centrally resolved preset definitions", () => {
  const base = {
    models: [],
    benchmarks: ["benchmark"],
    model_summaries: {},
    model_runtimes: {},
    model_token_summaries: {},
    matrix: {},
    fixtures: {},
    fixture_index: {},
    runs_meta: [],
    base_model_groups: [group("openai/a", [0.9]), group("other/b", [0.5])],
  };
  const catalog = {
    "openai/a": metadata("openai/a", 200000, "closed"),
    "other/b": metadata("other/b", 1000000, "open"),
  };
  const summary = attachModelPresets(base, catalog);
  const global = chartData("cost", summary);
  const benchmark = chartData(
    "cost",
    summary,
    { type: "benchmark", benchmark: "benchmark" },
    { benchmark: { benchmark: "benchmark", tag_counts: {}, leaderboard: [], fixtures: {}, results: {} } },
  );
  const fixture = chartData(
    "cost",
    summary,
    { type: "fixture", benchmark: "benchmark", fixture: "f001" },
    { fixture: { fixture: { id: "f001", benchmark: "benchmark", prompt: "", expected: "", description: "", setup: [], purpose: "", difficulty: "", tags: [] }, outputs: [] } },
  );

  assert.deepEqual(global.model_presets, summary.model_presets);
  assert.deepEqual(benchmark.model_presets, summary.model_presets);
  assert.deepEqual(fixture.model_presets, summary.model_presets);
  assert.deepEqual(benchmark.model_metadata, summary.model_metadata);
});
