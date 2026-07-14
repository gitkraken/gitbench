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
    reasoningWithinOutputTokens: 1343,
    reasoningOverflowTokens: 0,
    hasInconsistentReasoningTelemetry: false,
    hasReasoningData: true,
  });
  assert.deepEqual(decomposeOutputTokens(200, null), {
    totalOutputTokens: 200,
    visibleOutputTokens: 200,
    reasoningTokens: null,
    reasoningWithinOutputTokens: null,
    reasoningOverflowTokens: null,
    hasInconsistentReasoningTelemetry: false,
    hasReasoningData: false,
  });
  assert.deepEqual(decomposeOutputTokens(null, 10), {
    totalOutputTokens: null,
    visibleOutputTokens: null,
    reasoningTokens: 10,
    reasoningWithinOutputTokens: null,
    reasoningOverflowTokens: null,
    hasInconsistentReasoningTelemetry: false,
    hasReasoningData: true,
  });
  assert.deepEqual(decomposeOutputTokens(200, 0), {
    totalOutputTokens: 200,
    visibleOutputTokens: 200,
    reasoningTokens: 0,
    reasoningWithinOutputTokens: 0,
    reasoningOverflowTokens: 0,
    hasInconsistentReasoningTelemetry: false,
    hasReasoningData: true,
  });
  assert.deepEqual(decomposeOutputTokens(100, 120), {
    totalOutputTokens: 100,
    visibleOutputTokens: 0,
    reasoningTokens: 120,
    reasoningWithinOutputTokens: 100,
    reasoningOverflowTokens: 20,
    hasInconsistentReasoningTelemetry: true,
    hasReasoningData: true,
  });
});

test("decomposeOutputTokens does not add reasoning to provider totals", () => {
  const inputTokens = 500;
  const providerTotalTokens = 700;
  const decomposition = decomposeOutputTokens(200, 150);

  assert.equal(
    inputTokens +
      decomposition.visibleOutputTokens +
      decomposition.reasoningWithinOutputTokens,
    providerTotalTokens,
  );
  assert.equal(decomposition.totalOutputTokens, 200);
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
  assert.equal(formatCompactTokenUsage(127, 16, null, null), "127 in → 16 out");
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
