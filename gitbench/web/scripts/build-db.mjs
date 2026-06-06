#!/usr/bin/env node

import { readFileSync, renameSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { DatabaseSync } from "node:sqlite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(__dirname, "..");

const options = parseArgs(process.argv.slice(2));
const inputPath = path.resolve(webRoot, options.input ?? "public/results.json");
const outputPath = path.resolve(webRoot, options.output ?? "data/gitbench.db");
const schemaPath = path.resolve(webRoot, options.schema ?? "data/schema.sql");

const data = normalizeData(JSON.parse(readFileSync(inputPath, "utf8")));
const tempPath = `${outputPath}.tmp-${process.pid}`;

rmSync(tempPath, { force: true });

const db = new DatabaseSync(tempPath);
try {
  db.exec(`
    PRAGMA foreign_keys = ON;
    PRAGMA journal_mode = OFF;
    PRAGMA synchronous = OFF;
    PRAGMA temp_store = MEMORY;
  `);
  db.exec(readFileSync(schemaPath, "utf8"));
  insertReportData(db, data);
  db.exec("ANALYZE");
  db.close();
  renameSync(tempPath, outputPath);
  console.error(`SQLite report database written to: ${outputPath}`);
} catch (error) {
  db.close();
  rmSync(tempPath, { force: true });
  throw error;
}

function parseArgs(args) {
  const parsed = {};
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--input" || arg === "-i") parsed.input = args[++index];
    else if (arg === "--output" || arg === "-o") parsed.output = args[++index];
    else if (arg === "--schema" || arg === "-s") parsed.schema = args[++index];
    else if (arg === "--help" || arg === "-h") {
      console.log(`Usage: pnpm build:db [--input public/results.json] [--output data/gitbench.db] [--schema data/schema.sql]`);
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return parsed;
}

function normalizeData(data) {
  data.models ??= [];
  data.benchmarks ??= [];
  data.model_summaries ??= {};
  data.model_runtimes ??= {};
  data.matrix ??= {};
  data.fixtures ??= {};
  data.fixture_index ??= {};
  data.runs_meta ??= [];
  data.base_model_groups ??= [];

  const benchmarks = new Set(data.benchmarks);
  for (const byBenchmark of Object.values(data.fixtures)) {
    for (const benchmark of Object.keys(byBenchmark ?? {})) benchmarks.add(benchmark);
  }
  data.benchmarks = [...benchmarks].sort();

  for (const byBenchmark of Object.values(data.fixtures)) {
    for (const [benchmark, results] of Object.entries(byBenchmark ?? {})) {
      for (const result of results ?? []) {
        const fixtureId = result.fixture_id ?? "";
        const key = `${benchmark}/${fixtureId}`;
        if (!fixtureId || data.fixture_index[key]) continue;
        data.fixture_index[key] = {
          id: fixtureId,
          benchmark,
          prompt: "",
          expected: "",
          description: "",
          setup: [],
          purpose: result.purpose ?? "",
          difficulty: result.difficulty ?? "",
          tags: result.tags ?? [],
        };
      }
    }
  }

  // Normalize models: strip __json_schema suffix and set output_mode
  for (const model of data.models) {
    if (model.name && model.name.endsWith("__json_schema")) {
      model.output_mode = "json_schema";
      model.name = model.name.slice(0, -"__json_schema".length);
    } else if (!model.output_mode) {
      model.output_mode = "text";
    }
  }

  return data;
}

/** Derive (model_name, output_mode) from a composite key. */
function deriveModelMode(compositeKey) {
  if (compositeKey.endsWith("__json_schema")) {
    return {
      model_name: compositeKey.slice(0, -"__json_schema".length),
      output_mode: "json_schema",
    };
  }
  return { model_name: compositeKey, output_mode: "text" };
}

function insertReportData(db, data) {
  db.exec("BEGIN");
  try {
    insertMany(
      db,
      `INSERT INTO models (name, provider, base_model, reasoning_level, output_mode)
       VALUES (:name, :provider, :baseModel, :reasoningLevel, :output_mode)`,
      data.models.map((m) => ({ ...m, output_mode: m.output_mode ?? "text" })),
    );

    insertMany(
      db,
      "INSERT INTO benchmarks (name) VALUES (?)",
      data.benchmarks.map((name) => [name]),
    );

    insertMany(
      db,
      `INSERT INTO model_summaries (
         model_name, output_mode, total_runs, total_fixtures, total_passed, pass_at_k,
         total_cost_usd, avg_cost_usd
       )
       VALUES (
         :model_name, :output_mode, :total_runs, :total_fixtures, :total_passed, :pass_at_k,
         :total_cost_usd, :avg_cost_usd
       )`,
      Object.entries(data.model_summaries).map(([modelName, summary]) => ({
        ...deriveModelMode(modelName),
        ...summary,
      })),
    );

    insertMany(
      db,
      `INSERT INTO model_runtimes (
         model_name, output_mode, total_ms, avg_ms, min_ms, max_ms, fixture_count
       )
       VALUES (:model_name, :output_mode, :total_ms, :avg_ms, :min_ms, :max_ms, :fixture_count)`,
      Object.entries(data.model_runtimes).map(([modelName, runtime]) => ({
        ...deriveModelMode(modelName),
        ...runtime,
      })),
    );

    insertMany(
      db,
      `INSERT INTO benchmark_summaries (
         model_name, output_mode, benchmark_name, pass_at_k, total, passed, avg_similarity
       )
       VALUES (
         :model_name, :output_mode, :benchmark_name, :pass_at_k, :total, :passed, :avg_similarity
       )`,
      Object.entries(data.matrix).flatMap(([modelName, byBenchmark]) =>
        Object.entries(byBenchmark ?? {}).map(([benchmarkName, cell]) => ({
          ...deriveModelMode(modelName),
          benchmark_name: benchmarkName,
          ...cell,
        })),
      ),
    );

    const fixtures = Object.values(data.fixture_index);
    insertMany(
      db,
      `INSERT INTO fixtures (
         benchmark_name, fixture_id, prompt, expected, description, setup_json,
         purpose, difficulty
       )
       VALUES (
         :benchmark_name, :fixture_id, :prompt, :expected, :description,
         :setup_json, :purpose, :difficulty
       )`,
      fixtures.map((fixture) => ({
        benchmark_name: fixture.benchmark ?? "",
        fixture_id: fixture.id ?? "",
        prompt: fixture.prompt ?? "",
        expected: fixture.expected ?? "",
        description: fixture.description ?? "",
        setup_json: jsonArray(fixture.setup),
        purpose: fixture.purpose ?? "",
        difficulty: fixture.difficulty ?? "",
      })),
    );

    insertMany(
      db,
      "INSERT INTO fixture_tags (benchmark_name, fixture_id, tag) VALUES (?, ?, ?)",
      fixtures.flatMap((fixture) =>
        (fixture.tags ?? []).map((tag) => [fixture.benchmark ?? "", fixture.id ?? "", tag]),
      ),
    );

    insertMany(
      db,
      `INSERT INTO fixture_results (
         model_name, output_mode, benchmark_name, fixture_id, passed, similarity, error,
         model_output, reasoning_level, input_tokens, output_tokens, total_tokens,
         cost_usd, duration_ms, api_duration_ms, purpose, difficulty, tags_json,
         parsed_payload, raw_structured_output, structured_error
       )
       VALUES (
         :model_name, :output_mode, :benchmark_name, :fixture_id, :passed, :similarity, :error,
         :model_output, :reasoning_level, :input_tokens, :output_tokens,
         :total_tokens, :cost_usd, :duration_ms, :api_duration_ms, :purpose,
         :difficulty, :tags_json, :parsed_payload, :raw_structured_output, :structured_error
       )`,
      Object.entries(data.fixtures).flatMap(([modelName, byBenchmark]) =>
        Object.entries(byBenchmark ?? {}).flatMap(([benchmarkName, results]) =>
          (results ?? []).map((result) => ({
            ...deriveModelMode(modelName),
            output_mode: result.output_mode ?? deriveModelMode(modelName).output_mode,
            benchmark_name: benchmarkName,
            fixture_id: result.fixture_id ?? "",
            passed: result.passed ? 1 : 0,
            similarity: result.similarity ?? 0,
            error: result.error ?? null,
            model_output: result.model_output ?? "",
            reasoning_level: result.reasoning_level ?? null,
            input_tokens: result.input_tokens ?? null,
            output_tokens: result.output_tokens ?? null,
            total_tokens: result.total_tokens ?? null,
            cost_usd: result.cost_usd ?? null,
            duration_ms: result.duration_ms ?? null,
            api_duration_ms: result.api_duration_ms ?? null,
            purpose: result.purpose ?? null,
            difficulty: result.difficulty ?? null,
            tags_json: jsonArray(result.tags),
            parsed_payload: result.parsed_payload != null
              ? (typeof result.parsed_payload === "string"
                ? result.parsed_payload
                : JSON.stringify(result.parsed_payload))
              : null,
            raw_structured_output: result.raw_structured_output ?? null,
            structured_error: result.structured_error ?? null,
          })),
        ),
      ),
    );

    insertMany(
      db,
      `INSERT INTO runs (
         timestamp, model_name, output_mode, profile, git_sha, benchmark_suite_version,
         reasoning_level
       )
       VALUES (
         :timestamp, :model, :output_mode, :profile, :git_sha, :benchmark_suite_version,
         :reasoning_level
       )`,
      data.runs_meta.map((r) => {
        const { model_name, output_mode } = deriveModelMode(r.model ?? "");
        return {
          ...r,
          model: model_name,
          output_mode: r.output_mode ?? output_mode,
        };
      }),
    );

    const insertGroup = db.prepare(
      "INSERT INTO base_model_groups (provider, base_model) VALUES (?, ?)",
    );
    const insertLevel = db.prepare(
      `INSERT INTO base_model_group_levels (
         group_id, level, model_name, output_mode, pass_at_k, total_cost_usd
       )
       VALUES (?, ?, ?, ?, ?, ?)`,
    );
    for (const group of data.base_model_groups) {
      const { lastInsertRowid } = insertGroup.run(group.provider ?? "", group.baseModel ?? "");
      for (const level of group.levels ?? []) {
        insertLevel.run(
          lastInsertRowid,
          (level.level ?? "").replace(/__json_schema$/, "") || null,
          deriveModelMode(level.modelName ?? "").model_name,
          level.output_mode ?? deriveModelMode(level.modelName ?? "").output_mode,
          level.pass_at_k ?? 0,
          level.total_cost_usd ?? null,
        );
      }
    }

    db.exec("COMMIT");
  } catch (error) {
    db.exec("ROLLBACK");
    throw error;
  }
}

function insertMany(db, sql, rows) {
  const statement = db.prepare(sql);
  for (const row of rows) {
    Array.isArray(row) ? statement.run(...row) : statement.run(row);
  }
}

function jsonArray(value) {
  return JSON.stringify(Array.isArray(value) ? value : [], null, 0);
}
