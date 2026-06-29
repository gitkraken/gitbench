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
  data.campaigns ??= [];

  for (const model of data.models) {
    if (model.name && model.name.endsWith("__json_schema")) {
      model.output_mode = "json_schema";
      model.name = model.name.slice(0, -"__json_schema".length);
    } else if (!model.output_mode) {
      model.output_mode = "text";
    }
  }

  const modelKeys = new Set(
    data.models.map((model) => `${model.name}\u001f${model.output_mode ?? "text"}`),
  );
  const addModel = (modelName, outputMode) => {
    const derived = deriveModelMode(modelName ?? "");
    const name = derived.model_name;
    const mode = outputMode ?? derived.output_mode;
    if (!name) return;
    const key = `${name}\u001f${mode}`;
    if (modelKeys.has(key)) return;
    data.models.push(inferModelInfo(name, mode));
    modelKeys.add(key);
  };

  const benchmarks = new Set(data.benchmarks);
  const ensureFixture = (benchmark, fixtureId) => {
    if (!benchmark || !fixtureId) return;
    benchmarks.add(benchmark);
    const key = fixtureId.includes("/") ? fixtureId : `${benchmark}/${fixtureId}`;
    if (data.fixture_index[key]) return;
    data.fixture_index[key] = {
      id: fixtureId,
      benchmark,
      prompt: "",
      expected: "",
      description: "",
      setup: [],
      purpose: "",
      difficulty: "",
      tags: [],
    };
  };

  for (const byBenchmark of Object.values(data.fixtures)) {
    for (const benchmark of Object.keys(byBenchmark ?? {})) benchmarks.add(benchmark);
  }

  for (const byBenchmark of Object.values(data.fixtures)) {
    for (const [benchmark, results] of Object.entries(byBenchmark ?? {})) {
      for (const result of results ?? []) {
        const fixtureId = result.fixture_id ?? "";
        ensureFixture(benchmark, fixtureId);
        const key = fixtureId.includes("/") ? fixtureId : `${benchmark}/${fixtureId}`;
        const fixture = data.fixture_index[key];
        if (fixture) {
          fixture.purpose ||= result.purpose ?? "";
          fixture.difficulty ||= result.difficulty ?? "";
          if (
            Array.isArray(result.tags) &&
            result.tags.length > 0 &&
            (!Array.isArray(fixture.tags) || fixture.tags.length === 0)
          ) {
            fixture.tags = result.tags;
          }
        }
      }
    }
  }

  for (const campaign of data.campaigns) {
    const outputModes =
      Array.isArray(campaign.output_modes) && campaign.output_modes.length > 0
        ? campaign.output_modes
        : ["text"];
    for (const benchmark of campaign.benchmark_ids ?? []) benchmarks.add(benchmark);
    for (const modelId of campaign.model_ids ?? []) {
      for (const outputMode of outputModes) addModel(modelId, outputMode);
    }
    for (const attempt of campaign.raw_attempts ?? []) {
      const identity = attempt.identity ?? {};
      const fixtureId = identity.fixture_id ?? "";
      const benchmark = identity.benchmark ?? benchmarkFromFixtureId(fixtureId);
      ensureFixture(benchmark, fixtureId);
      addModel(identity.model_id, identity.output_mode ?? "text");
    }
    for (const aggregate of campaign.fixture_aggregates ?? []) {
      const fixtureId = aggregate.fixture_id ?? "";
      const benchmark = aggregate.benchmark ?? benchmarkFromFixtureId(fixtureId);
      ensureFixture(benchmark, fixtureId);
      addModel(aggregate.model_id, aggregate.output_mode ?? "text");
    }
    for (const summary of campaign.model_summaries ?? []) {
      addModel(summary.model_id, summary.output_mode ?? "text");
    }
    for (const summary of campaign.benchmark_summaries ?? []) {
      if (summary.benchmark) benchmarks.add(summary.benchmark);
    }
  }
  data.benchmarks = [...benchmarks].sort();

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
         reasoning_tokens,
         cost_usd, duration_ms, api_duration_ms, purpose, difficulty, tags_json,
         parsed_payload, raw_structured_output, structured_error
       )
       VALUES (
         :model_name, :output_mode, :benchmark_name, :fixture_id, :passed, :similarity, :error,
         :model_output, :reasoning_level, :input_tokens, :output_tokens,
         :total_tokens, :reasoning_tokens,
         :cost_usd, :duration_ms, :api_duration_ms, :purpose,
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
            reasoning_tokens: result.reasoning_tokens ?? null,
            cost_usd: result.cost_usd ?? null,
            duration_ms: result.duration_ms ?? null,
            api_duration_ms: result.api_duration_ms ?? null,
            purpose: result.purpose ?? null,
            difficulty: result.difficulty ?? null,
            tags_json: jsonArray(result.tags),
            parsed_payload: result.structured_error == null && result.parsed_payload != null
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

    insertCampaignData(db, data);

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

function insertCampaignData(db, data) {
  for (const campaign of data.campaigns ?? []) {
    const campaignId = campaign.campaign_id ?? "";
    db.prepare(
      `INSERT INTO campaigns (
         campaign_id, created_at, config_hash, state,
         planned_attempts, completed_attempts, valid_attempts,
         passing_attempts, excluded_attempts, publication_state,
         legacy, benchmark_ids_json, model_ids_json, output_modes_json,
         planned_trial_count
       )
       VALUES (
         :campaign_id, :created_at, :config_hash, :state,
         :planned_attempts, :completed_attempts, :valid_attempts,
         :passing_attempts, :excluded_attempts, :publication_state,
         :legacy, :benchmark_ids_json, :model_ids_json, :output_modes_json,
         :planned_trial_count
       )`,
    ).run({
      campaign_id: campaignId,
      created_at: campaign.created_at ?? "",
      config_hash: campaign.config_hash ?? "",
      state: campaign.state ?? "incomplete",
      planned_attempts: campaign.planned_attempts ?? 0,
      completed_attempts: campaign.completed_attempts ?? 0,
      valid_attempts: campaign.valid_attempts ?? 0,
      passing_attempts: campaign.passing_attempts ?? 0,
      excluded_attempts: campaign.excluded_attempts ?? 0,
      publication_state: campaign.publication_state ?? "draft",
      legacy: campaign.legacy ? 1 : 0,
      benchmark_ids_json: jsonArray(campaign.benchmark_ids),
      model_ids_json: jsonArray(campaign.model_ids),
      output_modes_json: jsonArray(campaign.output_modes),
      planned_trial_count: campaign.planned_trial_count ?? 1,
    });

    insertMany(
      db,
      `INSERT INTO trials (
         campaign_id, trial_index, planned_attempts, completed_attempts,
         valid_attempts, passing_attempts, excluded_attempts, complete
       )
       VALUES (
         :campaign_id, :trial_index, :planned_attempts, :completed_attempts,
         :valid_attempts, :passing_attempts, :excluded_attempts, :complete
       )`,
      (campaign.trials ?? []).map((trial) => ({
        campaign_id: campaignId,
        trial_index: trial.trial_index ?? 0,
        planned_attempts: trial.planned_attempts ?? 0,
        completed_attempts: trial.completed_attempts ?? 0,
        valid_attempts: trial.valid_attempts ?? 0,
        passing_attempts: trial.passing_attempts ?? 0,
        excluded_attempts: trial.excluded_attempts ?? 0,
        complete: trial.complete ? 1 : 0,
      })),
    );

    insertMany(
      db,
      `INSERT INTO raw_attempts (
         campaign_id, trial_index, model_name, reasoning_level,
         output_mode, benchmark_name, fixture_id, status, passed,
         similarity, error, model_output, input_tokens, output_tokens,
         total_tokens, reasoning_tokens, cost_usd, api_duration_ms,
         request_telemetry_json, provider_route_metadata_json,
         judge_evidence_json, safety_state, safety_cost_usd,
         provenance_json
       )
       VALUES (
         :campaign_id, :trial_index, :model_name, :reasoning_level,
         :output_mode, :benchmark_name, :fixture_id, :status, :passed,
         :similarity, :error, :model_output, :input_tokens, :output_tokens,
         :total_tokens, :reasoning_tokens, :cost_usd, :api_duration_ms,
         :request_telemetry_json, :provider_route_metadata_json,
         :judge_evidence_json, :safety_state, :safety_cost_usd,
         :provenance_json
       )`,
      (campaign.raw_attempts ?? []).map((attempt) => {
        const identity = attempt.identity ?? {};
        const fixtureId = identity.fixture_id ?? "";
        return {
          campaign_id: campaignId,
          trial_index: identity.trial_index ?? 0,
          model_name: identity.model_id ?? "",
          reasoning_level: identity.reasoning_effort ?? null,
          output_mode: identity.output_mode ?? "text",
          benchmark_name: identity.benchmark ?? benchmarkFromFixtureId(fixtureId),
          fixture_id: fixtureId,
          status: attempt.status ?? "pending",
          passed: attempt.passed == null ? null : attempt.passed ? 1 : 0,
          similarity: attempt.similarity ?? null,
          error: attempt.error ?? null,
          model_output: attempt.model_output ?? "",
          input_tokens: attempt.input_tokens ?? null,
          output_tokens: attempt.output_tokens ?? null,
          total_tokens: attempt.total_tokens ?? null,
          reasoning_tokens: attempt.reasoning_tokens ?? null,
          cost_usd: attempt.cost_usd ?? null,
          api_duration_ms: attempt.api_duration_ms ?? null,
          request_telemetry_json: jsonValue(attempt.request_telemetry),
          provider_route_metadata_json: jsonValue(attempt.provider_route_metadata),
          judge_evidence_json: jsonValue(attempt.judge_evidence),
          safety_state: attempt.safety_state ?? null,
          safety_cost_usd: attempt.safety_cost_usd ?? null,
          provenance_json: jsonValue(attempt.provenance),
        };
      }),
    );

    insertMany(
      db,
      `INSERT INTO fixture_aggregates (
         campaign_id, benchmark_name, fixture_id, model_name,
         reasoning_level, output_mode, planned_trials,
         completed_trials, valid_attempts, passing_attempts,
         failing_attempts, excluded_attempts, mean_success_rate,
         pass_any_at_n_json, reliability_classification, incomplete
       )
       VALUES (
         :campaign_id, :benchmark_name, :fixture_id, :model_name,
         :reasoning_level, :output_mode, :planned_trials,
         :completed_trials, :valid_attempts, :passing_attempts,
         :failing_attempts, :excluded_attempts, :mean_success_rate,
         :pass_any_at_n_json, :reliability_classification, :incomplete
       )`,
      (campaign.fixture_aggregates ?? []).map((aggregate) => {
        const fixtureId = aggregate.fixture_id ?? "";
        return {
          campaign_id: campaignId,
          benchmark_name: aggregate.benchmark ?? benchmarkFromFixtureId(fixtureId),
          fixture_id: fixtureId,
          model_name: aggregate.model_id ?? "",
          reasoning_level: aggregate.reasoning_effort ?? "",
          output_mode: aggregate.output_mode ?? "text",
          planned_trials: aggregate.planned_trials ?? 0,
          completed_trials: aggregate.completed_trials ?? 0,
          valid_attempts: aggregate.valid_attempts ?? 0,
          passing_attempts: aggregate.passing_attempts ?? 0,
          failing_attempts: aggregate.failing_attempts ?? 0,
          excluded_attempts: aggregate.excluded_attempts ?? 0,
          mean_success_rate: aggregate.mean_success_rate ?? null,
          pass_any_at_n_json: jsonValue(aggregate.pass_any_at_n ?? {}),
          reliability_classification: aggregate.reliability_classification ?? null,
          incomplete: aggregate.incomplete ? 1 : 0,
        };
      }),
    );

    insertMany(
      db,
      `INSERT INTO campaign_model_summaries (
         campaign_id, model_name, reasoning_level, output_mode, planned_trials,
         completed_trials, valid_attempts, passing_attempts,
         excluded_attempts, mean_success_rate, pass_any_at_n_json,
         incomplete, resource_summary_json
       )
       VALUES (
         :campaign_id, :model_name, :reasoning_level, :output_mode, :planned_trials,
         :completed_trials, :valid_attempts, :passing_attempts,
         :excluded_attempts, :mean_success_rate, :pass_any_at_n_json,
         :incomplete, :resource_summary_json
       )`,
      (campaign.model_summaries ?? []).map((summary) => ({
        campaign_id: campaignId,
        model_name: summary.model_id ?? "",
        reasoning_level: summary.reasoning_effort ?? "",
        output_mode: summary.output_mode ?? "text",
        planned_trials: summary.planned_trials ?? 0,
        completed_trials: summary.completed_trials ?? 0,
        valid_attempts: summary.valid_attempts ?? 0,
        passing_attempts: summary.passing_attempts ?? 0,
        excluded_attempts: summary.excluded_attempts ?? 0,
        mean_success_rate: summary.mean_success_rate ?? null,
        pass_any_at_n_json: jsonValue(summary.pass_any_at_n ?? {}),
        incomplete: summary.incomplete ? 1 : 0,
        resource_summary_json: jsonValue(summary.resource_summary),
      })),
    );

    insertMany(
      db,
      `INSERT INTO campaign_benchmark_summaries (
         campaign_id, benchmark_name, planned_trials,
         completed_trials, valid_attempts, passing_attempts,
         excluded_attempts, mean_success_rate, pass_any_at_n_json,
         incomplete, resource_summary_json
       )
       VALUES (
         :campaign_id, :benchmark_name, :planned_trials,
         :completed_trials, :valid_attempts, :passing_attempts,
         :excluded_attempts, :mean_success_rate, :pass_any_at_n_json,
         :incomplete, :resource_summary_json
       )`,
      (campaign.benchmark_summaries ?? []).map((summary) => ({
        campaign_id: campaignId,
        benchmark_name: summary.benchmark ?? "",
        planned_trials: summary.planned_trials ?? 0,
        completed_trials: summary.completed_trials ?? 0,
        valid_attempts: summary.valid_attempts ?? 0,
        passing_attempts: summary.passing_attempts ?? 0,
        excluded_attempts: summary.excluded_attempts ?? 0,
        mean_success_rate: summary.mean_success_rate ?? null,
        pass_any_at_n_json: jsonValue(summary.pass_any_at_n ?? {}),
        incomplete: summary.incomplete ? 1 : 0,
        resource_summary_json: jsonValue(summary.resource_summary),
      })),
    );

    insertMany(
      db,
      `INSERT INTO resource_summaries (
         campaign_id, scope, total_cost_usd, total_input_tokens,
         total_output_tokens, total_tokens, total_reasoning_tokens,
         total_api_duration_ms, total_wall_duration_ms,
         mean_cost_per_complete_trial_usd, mean_tokens_per_complete_trial,
         mean_api_duration_per_complete_trial_ms, partial_pricing
       )
       VALUES (
         :campaign_id, :scope, :total_cost_usd, :total_input_tokens,
         :total_output_tokens, :total_tokens, :total_reasoning_tokens,
         :total_api_duration_ms, :total_wall_duration_ms,
         :mean_cost_per_complete_trial_usd, :mean_tokens_per_complete_trial,
         :mean_api_duration_per_complete_trial_ms, :partial_pricing
       )`,
      (campaign.resource_summaries ?? []).map((summary) => ({
        campaign_id: campaignId,
        scope: summary.scope ?? "campaign",
        total_cost_usd: summary.total_cost_usd ?? null,
        total_input_tokens: summary.total_input_tokens ?? null,
        total_output_tokens: summary.total_output_tokens ?? null,
        total_tokens: summary.total_tokens ?? null,
        total_reasoning_tokens: summary.total_reasoning_tokens ?? null,
        total_api_duration_ms: summary.total_api_duration_ms ?? null,
        total_wall_duration_ms: summary.total_wall_duration_ms ?? null,
        mean_cost_per_complete_trial_usd:
          summary.mean_cost_per_complete_trial_usd ?? null,
        mean_tokens_per_complete_trial: summary.mean_tokens_per_complete_trial ?? null,
        mean_api_duration_per_complete_trial_ms:
          summary.mean_api_duration_per_complete_trial_ms ?? null,
        partial_pricing: summary.partial_pricing ? 1 : 0,
      })),
    );

    const safetySummary = campaign.safety_summary ?? {};
    db.prepare(
      `INSERT INTO publication_states (
         campaign_id, reviewed_count, sanitized_count, blocked_count, pending_count
       )
       VALUES (
         :campaign_id, :reviewed_count, :sanitized_count, :blocked_count, :pending_count
       )`,
    ).run({
      campaign_id: campaignId,
      reviewed_count: safetySummary.reviewed ?? 0,
      sanitized_count: safetySummary.sanitized ?? 0,
      blocked_count: safetySummary.blocked ?? 0,
      pending_count: safetySummary.pending ?? 0,
    });
  }
}

function jsonArray(value) {
  return JSON.stringify(Array.isArray(value) ? value : [], null, 0);
}

function jsonValue(value) {
  return JSON.stringify(value ?? null, null, 0);
}

function benchmarkFromFixtureId(fixtureId) {
  return typeof fixtureId === "string" && fixtureId.includes("/")
    ? fixtureId.split("/")[0]
    : "";
}

function inferModelInfo(modelName, outputMode) {
  const slashIndex = modelName.indexOf("/");
  const provider = slashIndex > 0 ? modelName.slice(0, slashIndex) : "";
  const modelPart = slashIndex > 0 ? modelName.slice(slashIndex + 1) : modelName;
  const levelIndex = modelPart.lastIndexOf(":");
  const baseModel =
    levelIndex > 0 ? modelPart.slice(0, levelIndex) : modelPart || modelName;
  const reasoningLevel = levelIndex > 0 ? modelPart.slice(levelIndex + 1) : null;
  return {
    name: modelName,
    provider,
    baseModel,
    reasoningLevel,
    output_mode: outputMode,
  };
}
