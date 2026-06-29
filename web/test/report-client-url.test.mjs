import assert from "node:assert/strict";
import test from "node:test";

import { loadModelResults } from "../src/lib/report-client.ts";

test("loadModelResults combines filters and selected campaign in one query string", async () => {
  const previousFetch = globalThis.fetch;
  const hadWindow = Object.hasOwn(globalThis, "window");
  const previousWindow = globalThis.window;
  let requestedUrl = "";

  globalThis.fetch = async (url) => {
    requestedUrl = String(url);
    return {
      ok: true,
      json: async () => ({ model: "openai/gpt-test:high", results: {} }),
    };
  };
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      location: {
        search: "?campaign=campaign-123",
      },
    },
  });

  try {
    await loadModelResults("openai/gpt-test:high", {
      output_mode: "text",
      benchmark: "commit_messages",
    });
  } finally {
    globalThis.fetch = previousFetch;
    if (hadWindow) {
      Object.defineProperty(globalThis, "window", {
        configurable: true,
        value: previousWindow,
      });
    } else {
      delete globalThis.window;
    }
  }

  assert.equal(
    requestedUrl,
    "/api/models/openai/gpt-test%3Ahigh/results?output_mode=text&benchmark=commit_messages&campaign=campaign-123"
  );
});
