import assert from "node:assert/strict";
import test from "node:test";

import { formatStructuredOutputFailure } from "../src/lib/structured-output-display.ts";

test("parse failures display invalid JSON and copy the raw output", () => {
  const raw = "{not json";
  const display = formatStructuredOutputFailure(
    "Failed to parse structured JSON response: bad input",
    raw,
  );

  assert.deepEqual(display, {
    message: `Invalid JSON. Output: ${raw}`,
    copyText: raw,
  });
});

test("schema failures display invalid structured output and copy the raw output", () => {
  const raw = '{"commit":42}';
  const display = formatStructuredOutputFailure(
    "Structured output schema validation failed: $.commit must be of type string",
    raw,
  );

  assert.deepEqual(display, {
    message: `Invalid structured output. Output: ${raw}`,
    copyText: raw,
  });
});
