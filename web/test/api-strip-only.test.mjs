import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { glob } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
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

test("default report database path does not depend on process cwd", () => {
  const cwd = mkdtempSync(path.join(tmpdir(), "gitbench-api-cwd-"));
  const env = { ...process.env };
  delete env.GITBENCH_REPORT_DB;

  try {
    const storeUrl = new URL(
      "../src/lib/node-sqlite-report-store.ts",
      import.meta.url
    ).href;
    const script = `
      const { clearReportStoreCache, getReportStore } = await import(${JSON.stringify(storeUrl)});
      clearReportStoreCache();
      const store = getReportStore();
      const models = store.getModels();
      if (!models.length) throw new Error("Expected report models");
    `;
    const result = spawnSync(
      process.execPath,
      ["--experimental-strip-types", "--input-type=module", "--eval", script],
      { cwd, env, encoding: "utf8" }
    );

    assert.equal(
      result.status,
      0,
      [result.stdout, result.stderr].filter(Boolean).join("\n")
    );
  } finally {
    rmSync(cwd, { recursive: true, force: true });
  }
});
