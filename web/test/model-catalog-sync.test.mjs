import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { tmpdir } from "node:os";
import { DatabaseSync } from "node:sqlite";

import {
  generateModelCatalog,
  serializeModelCatalog,
} from "../src/lib/model-catalog-sync.ts";

const fetchedAt = "2026-07-16T00:00:00.000Z";

function overrides(value = {}) {
  return {
    schemaVersion: 1,
    aliases: {},
    models: {},
    ...value,
  };
}

test("sync uses exact IDs and does not infer open weights from Hugging Face", () => {
  const { catalog, diagnostics } = generateModelCatalog({
    currentModelGroupIds: ["provider/model"],
    upstream: {
      data: [
        {
          id: "provider/model",
          context_length: 128000,
          hugging_face_id: "provider/model",
        },
      ],
    },
    overrides: overrides(),
    fetchedAt,
  });

  assert.equal(catalog.models["provider/model"].contextWindowTokens, 128000);
  assert.equal(catalog.models["provider/model"].weightAccess, "unknown");
  assert.deepEqual(diagnostics.unknownWeightAccess, ["provider/model"]);
});

test("sync normalizes an empty optional Hugging Face ID to null", () => {
  const { catalog } = generateModelCatalog({
    currentModelGroupIds: ["provider/model"],
    upstream: {
      data: [{ id: "provider/model", context_length: 128000, hugging_face_id: "" }],
    },
    overrides: overrides(),
    fetchedAt,
  });
  assert.equal(catalog.models["provider/model"].huggingFaceId, null);
});

test("reviewed field and renamed-model overrides take precedence", () => {
  const { catalog } = generateModelCatalog({
    currentModelGroupIds: ["provider/old"],
    upstream: {
      data: [{ id: "provider/new", context_length: 32000 }],
    },
    overrides: overrides({
      aliases: { "provider/old": "provider/new" },
      models: {
        "provider/old": {
          contextWindowTokens: 64000,
          weightAccess: "open",
        },
      },
    }),
    fetchedAt,
  });

  const record = catalog.models["provider/old"];
  assert.equal(record.openRouterId, "provider/new");
  assert.equal(record.contextWindowTokens, 64000);
  assert.equal(record.weightAccess, "open");
  assert.deepEqual(record.provenance, {
    contextWindowTokens: "override",
    weightAccess: "override",
  });
});

test("sync emits explicit unknown records and stable output", () => {
  const input = {
    currentModelGroupIds: ["z/model", "a/model"],
    upstream: { data: [] },
    overrides: overrides(),
    fetchedAt,
  };
  const first = generateModelCatalog(input);
  const second = generateModelCatalog(input);

  assert.deepEqual(Object.keys(first.catalog.models), ["a/model", "z/model"]);
  assert.deepEqual(first.diagnostics.unmatched, ["a/model", "z/model"]);
  assert.equal(first.catalog.models["a/model"].contextWindowTokens, null);
  assert.equal(first.catalog.models["a/model"].weightAccess, "unknown");
  assert.equal(serializeModelCatalog(first.catalog), serializeModelCatalog(second.catalog));
});

test("sync rejects duplicate upstream IDs before output generation", () => {
  assert.throws(
    () =>
      generateModelCatalog({
        currentModelGroupIds: ["provider/model"],
        upstream: { data: [{ id: "provider/model" }, { id: "provider/model" }] },
        overrides: overrides(),
        fetchedAt,
      }),
    /duplicate OpenRouter model ID/,
  );
});

test("CLI leaves the last valid catalog untouched when generation fails", () => {
  const directory = mkdtempSync(path.join(tmpdir(), "gitbench-model-catalog-"));
  const databasePath = path.join(directory, "models.db");
  const upstreamPath = path.join(directory, "upstream.json");
  const overridesPath = path.join(directory, "overrides.json");
  const outputPath = path.join(directory, "catalog.json");
  const original = '{"lastValid":true}\n';
  try {
    const database = new DatabaseSync(databasePath);
    database.exec("CREATE TABLE base_model_groups (provider TEXT, base_model TEXT)");
    database.exec("INSERT INTO base_model_groups VALUES ('provider', 'model')");
    database.close();
    writeFileSync(upstreamPath, JSON.stringify({
      data: [{ id: "provider/model", context_length: -1 }],
    }));
    writeFileSync(overridesPath, JSON.stringify(overrides()));
    writeFileSync(outputPath, original);

    const result = spawnSync(
      process.execPath,
      [
        "--experimental-strip-types",
        "--experimental-transform-types",
        "scripts/sync-model-catalog.mjs",
        "--upstream",
        upstreamPath,
        "--overrides",
        overridesPath,
        "--database",
        databasePath,
        "--output",
        outputPath,
        "--fetched-at",
        fetchedAt,
      ],
      { cwd: path.resolve("."), encoding: "utf8" },
    );

    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /invalid context_length/);
    assert.equal(readFileSync(outputPath, "utf8"), original);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
