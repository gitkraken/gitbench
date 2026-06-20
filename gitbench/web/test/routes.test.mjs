import assert from "node:assert/strict";
import test from "node:test";

import { fixturePath, modelResultAnchor } from "../src/lib/routes.ts";

test("model result anchors are deterministic and URL-safe", () => {
  assert.equal(
    modelResultAnchor("anthropic/claude-opus-4.7:high", "text"),
    "result-anthropic~2Fclaude-opus-4.7~3Ahigh-text"
  );
  assert.equal(
    modelResultAnchor("openai/gpt-test:high__json_schema", "json_schema"),
    "result-openai~2Fgpt-test~3Ahigh__json_schema-json_schema"
  );
});

test("fixture paths can target a specific model result", () => {
  assert.equal(
    fixturePath("commit_messages", "f001", {
      modelName: "openai/gpt-test:high",
      outputMode: "text",
    }),
    "/fixtures/commit_messages/f001#result-openai~2Fgpt-test~3Ahigh-text"
  );
});
