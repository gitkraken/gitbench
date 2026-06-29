import assert from "node:assert/strict";
import test from "node:test";

import {
  REASONING_WITHIN_OUTPUT_LABEL,
  TOTAL_OUTPUT_LABEL,
  decomposeOutputTokens,
  formatAggregateTokenUsage,
  formatCompactTokenUsage,
} from "../src/lib/token-usage.ts";

test("decomposeOutputTokens preserves raw output and derives visible output", () => {
  assert.deepEqual(decomposeOutputTokens(1349, 1343), {
    totalOutputTokens: 1349,
    visibleOutputTokens: 6,
    reasoningTokens: 1343,
    hasReasoningData: true,
  });
  assert.deepEqual(decomposeOutputTokens(200, null), {
    totalOutputTokens: 200,
    visibleOutputTokens: 200,
    reasoningTokens: null,
    hasReasoningData: false,
  });
  assert.deepEqual(decomposeOutputTokens(null, 10), {
    totalOutputTokens: null,
    visibleOutputTokens: null,
    reasoningTokens: 10,
    hasReasoningData: true,
  });
  assert.deepEqual(decomposeOutputTokens(100, 120), {
    totalOutputTokens: 100,
    visibleOutputTokens: 0,
    reasoningTokens: 120,
    hasReasoningData: true,
  });
});

test("compact labels describe reasoning as part of output", () => {
  assert.equal(
    formatCompactTokenUsage(127, 166, "high", 150),
    "127 in → 166 out (150 reasoning)",
  );
  assert.equal(
    formatCompactTokenUsage(127, 166, "none", 0),
    "127 in → 166 out (0 reasoning)",
  );
  assert.equal(
    formatCompactTokenUsage(127, 166, "high", null),
    "127 in → 166 out (reasoning unavailable)",
  );
  assert.equal(
    formatCompactTokenUsage(127, 16, null, null),
    "127 in → 16 out",
  );
});

test("aggregate labels and fixture labels make output inclusion explicit", () => {
  assert.equal(
    formatAggregateTokenUsage(127, 166, "high", 150),
    "127 input / 166 total output / 150 reasoning within output tokens",
  );
  assert.equal(
    formatAggregateTokenUsage(127, 166, "none", 0),
    "127 input / 166 total output / 0 reasoning within output tokens",
  );
  assert.equal(TOTAL_OUTPUT_LABEL, "Total output");
  assert.equal(REASONING_WITHIN_OUTPUT_LABEL, "Reasoning within output");
});
