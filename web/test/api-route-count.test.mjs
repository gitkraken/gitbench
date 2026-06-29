import assert from "node:assert/strict";
import test from "node:test";
import { glob } from "node:fs/promises";

const EXPECTED_ROUTES = [
  "benchmarks/[benchmark].ts",
  "campaigns/[campaignId]/attempts/[...identity].ts",
  "campaigns/[campaignId]/index.ts",
  "campaigns/[campaignId]/raw-attempts.ts",
  "campaigns/index.ts",
  "charts/[chart].ts",
  "email-signups.ts",
  "fixtures/[benchmark]/[...fixture].ts",
  "models/[...model]/results.ts",
  "models/index.ts",
  "summary.ts",
];

/**
 * Consolidated report API should expose the expected route files while staying
 * within the 11-function Vercel budget.
 */
test("API route file set stays within the 11-function budget", async () => {
  const apiDir = new URL("../api/", import.meta.url);
  const files = [];
  for await (const entry of glob("**/*.ts", { cwd: apiDir.pathname })) {
    files.push(entry);
  }
  files.sort();
  assert.deepEqual(files, EXPECTED_ROUTES);
  assert.ok(
    files.length <= 11,
    `Expected at most 11 API route files but found ${files.length}:\n${files.join("\n")}`
  );
});
