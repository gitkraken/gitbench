#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { DatabaseSync } from "node:sqlite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(__dirname, "..");

const REQUIRED_TOP_LEVEL_SECTIONS = {
  models: "array",
  benchmarks: "array",
  fixtures: "object",
  fixture_index: "object",
  model_summaries: "object",
  model_runtimes: "object",
  matrix: "object",
  runs_meta: "array",
  base_model_groups: "array",
  campaigns: "array",
};

const OPTIONAL_TOP_LEVEL_SECTIONS = {
  model_token_summaries: "object",
  safety_review: "object",
};

const options = parseArgs(process.argv.slice(2));
const jsonPath = path.resolve(webRoot, options.json ?? "public/results.json");
const schemaPath = path.resolve(webRoot, options.schema ?? "data/schema.sql");
const dbPath = path.resolve(webRoot, options.db ?? "data/gitbench.db");

const data = JSON.parse(readFileSync(jsonPath, "utf8"));
validateReportJsonContract(data);

const tempDir = mkdtempSync(path.join(tmpdir(), "gitbench-artifact-validation-"));
const rebuiltDbPath = path.join(tempDir, "gitbench.db");

try {
  const build = spawnSync(
    process.execPath,
    [
      "scripts/build-db.mjs",
      "--input",
      jsonPath,
      "--output",
      rebuiltDbPath,
      "--schema",
      schemaPath,
    ],
    {
      cwd: webRoot,
      encoding: "utf8",
    },
  );
  if (build.status !== 0) {
    throw new Error(build.stderr || build.stdout || "SQLite rebuild failed.");
  }

  const checkedIn = fingerprintDatabase(dbPath);
  const rebuilt = fingerprintDatabase(rebuiltDbPath);
  if (checkedIn !== rebuilt) {
    throw new Error(
      "web/data/gitbench.db is stale. Run `pnpm build:db` from web/ and commit the regenerated database.",
    );
  }

  console.error(
    `Report artifacts validated: ${path.relative(webRoot, jsonPath)}, ${path.relative(
      webRoot,
      schemaPath,
    )}, ${path.relative(webRoot, dbPath)}`,
  );
} finally {
  rmSync(tempDir, { recursive: true, force: true });
}

export function validateReportJsonContract(data) {
  if (!isPlainObject(data)) {
    throw new Error("Report artifact must be a JSON object.");
  }

  for (const [section, expectedType] of Object.entries(REQUIRED_TOP_LEVEL_SECTIONS)) {
    if (!(section in data)) {
      throw new Error(`Report artifact is missing required top-level section: ${section}`);
    }
    assertJsonSectionType(section, data[section], expectedType);
  }

  for (const [section, expectedType] of Object.entries(OPTIONAL_TOP_LEVEL_SECTIONS)) {
    if (section in data) assertJsonSectionType(section, data[section], expectedType);
  }

  JSON.stringify(data);
}

function parseArgs(args) {
  const parsed = {};
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--json") parsed.json = args[++index];
    else if (arg === "--schema") parsed.schema = args[++index];
    else if (arg === "--db") parsed.db = args[++index];
    else if (arg === "--help" || arg === "-h") {
      console.log(
        "Usage: pnpm validate:artifacts [--json public/results.json] [--schema data/schema.sql] [--db data/gitbench.db]",
      );
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return parsed;
}

function assertJsonSectionType(section, value, expectedType) {
  if (expectedType === "array" && !Array.isArray(value)) {
    throw new Error(`Report artifact section ${section} must be an array.`);
  }
  if (expectedType === "object" && !isPlainObject(value)) {
    throw new Error(`Report artifact section ${section} must be an object.`);
  }
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function fingerprintDatabase(dbPath) {
  const db = new DatabaseSync(dbPath, { readOnly: true });
  try {
    const foreignKeyViolations = db.prepare("PRAGMA foreign_key_check").all();
    if (foreignKeyViolations.length > 0) {
      throw new Error(`Foreign key violations in ${dbPath}: ${JSON.stringify(foreignKeyViolations)}`);
    }

    const hash = createHash("sha256");
    hash.update(JSON.stringify(schemaRows(db)));
    for (const table of userTables(db)) {
      hash.update(table);
      hash.update(JSON.stringify(tableRows(db, table)));
    }
    return hash.digest("hex");
  } finally {
    db.close();
  }
}

function schemaRows(db) {
  return db
    .prepare(
      `SELECT type, name, tbl_name, sql
       FROM sqlite_schema
       WHERE name NOT LIKE 'sqlite_%'
       ORDER BY type, name, tbl_name`,
    )
    .all()
    .map((row) => ({ ...row }));
}

function userTables(db) {
  return db
    .prepare(
      `SELECT name
       FROM sqlite_schema
       WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
       ORDER BY name`,
    )
    .all()
    .map((row) => row.name);
}

function tableRows(db, table) {
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(table)) {
    throw new Error(`Unexpected SQLite table name: ${table}`);
  }
  return db
    .prepare(`SELECT * FROM "${table}" ORDER BY rowid`)
    .all()
    .map((row) => ({ ...row }));
}
