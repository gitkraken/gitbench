import {
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";

import {
  generateModelCatalog,
  serializeModelCatalog,
} from "../src/lib/model-catalog-sync.ts";
import { validateModelMetadataCatalog } from "../src/lib/model-catalog.ts";

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models";

function parseArgs(args) {
  const options = {};
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--check") options.check = true;
    else if (arg === "--upstream") options.upstream = args[++index];
    else if (arg === "--overrides") options.overrides = args[++index];
    else if (arg === "--output") options.output = args[++index];
    else if (arg === "--database") options.database = args[++index];
    else if (arg === "--fetched-at") options.fetchedAt = args[++index];
    else if (arg === "--help") options.help = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return options;
}

function currentModelGroupIds(databasePath) {
  const database = new DatabaseSync(databasePath, { readOnly: true });
  try {
    return database
      .prepare("SELECT provider, base_model FROM base_model_groups ORDER BY provider, base_model")
      .all()
      .map((row) => `${row.provider}/${row.base_model}`);
  } finally {
    database.close();
  }
}

function validateCoverage(catalog, canonicalIds) {
  const catalogIds = Object.keys(catalog.models);
  const missing = canonicalIds.filter((id) => !catalog.models[id]);
  const stale = catalogIds.filter((id) => !canonicalIds.includes(id));
  if (missing.length || stale.length) {
    throw new Error(
      `Catalog coverage mismatch; missing: ${missing.join(", ") || "none"}; stale: ${stale.join(", ") || "none"}`,
    );
  }
}

function printDiagnostics(diagnostics) {
  for (const [label, ids] of Object.entries(diagnostics)) {
    if (ids.length) console.warn(`${label}: ${ids.join(", ")}`);
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    console.log("Usage: pnpm sync:model-catalog [--check] [--upstream file] [--overrides file] [--output file] [--database file] [--fetched-at ISO]");
    return;
  }

  const outputPath = path.resolve(webRoot, options.output ?? "data/model-catalog.json");
  const overridesPath = path.resolve(
    webRoot,
    options.overrides ?? "data/model-catalog-overrides.json",
  );
  const databasePath = path.resolve(webRoot, options.database ?? "data/gitbench.db");
  const canonicalIds = currentModelGroupIds(databasePath);

  if (options.check) {
    const catalog = validateModelMetadataCatalog(
      JSON.parse(readFileSync(outputPath, "utf8")),
    );
    validateCoverage(catalog, canonicalIds);
    const unknownContext = canonicalIds.filter(
      (id) => catalog.models[id].contextWindowTokens === null,
    );
    const unknownWeightAccess = canonicalIds.filter(
      (id) => catalog.models[id].weightAccess === "unknown",
    );
    printDiagnostics({ unknownContext, unknownWeightAccess });
    console.log(`Model catalog valid: ${canonicalIds.length} canonical groups`);
    return;
  }

  const upstream = options.upstream
    ? JSON.parse(readFileSync(path.resolve(webRoot, options.upstream), "utf8"))
    : await fetch(OPENROUTER_MODELS_URL).then((response) => {
        if (!response.ok) throw new Error(`OpenRouter request failed: ${response.status}`);
        return response.json();
      });
  const overrides = JSON.parse(readFileSync(overridesPath, "utf8"));
  const generated = generateModelCatalog({
    currentModelGroupIds: canonicalIds,
    upstream,
    overrides,
    fetchedAt: options.fetchedAt ?? new Date().toISOString(),
  });
  validateCoverage(generated.catalog, canonicalIds);
  printDiagnostics(generated.diagnostics);

  const tempPath = `${outputPath}.tmp-${process.pid}`;
  try {
    writeFileSync(tempPath, serializeModelCatalog(generated.catalog), {
      encoding: "utf8",
      flag: "wx",
    });
    renameSync(tempPath, outputPath);
  } catch (error) {
    rmSync(tempPath, { force: true });
    throw error;
  }
  console.log(`Wrote ${canonicalIds.length} model records to ${path.relative(webRoot, outputPath)}`);
}

await main();
