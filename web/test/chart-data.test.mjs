import assert from "node:assert/strict";
import test from "node:test";

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
