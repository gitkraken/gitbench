import assert from "node:assert/strict";
import { glob } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import test from "node:test";

test("API route dependency graph imports in Node strip-only TypeScript mode", async () => {
  const apiDir = new URL("../api/", import.meta.url);
  const routeUrls = [];
  for await (const entry of glob("**/*.ts", { cwd: apiDir.pathname })) {
    routeUrls.push(new URL(`../api/${entry}`, import.meta.url).href);
  }
  routeUrls.sort();

  const script = `
    for (const route of ${JSON.stringify(routeUrls)}) {
      await import(route);
    }
  `;
  const result = spawnSync(
    process.execPath,
    ["--experimental-strip-types", "--input-type=module", "--eval", script],
    { encoding: "utf8" }
  );

  assert.equal(
    result.status,
    0,
    [result.stdout, result.stderr].filter(Boolean).join("\n")
  );
});
