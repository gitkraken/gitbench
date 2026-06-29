import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

test("build-db creates a queryable SQLite database from results JSON", () => {
  const dir = mkdtempSync(path.join(tmpdir(), "gitbench-build-db-"));
  const inputPath = path.join(dir, "results.json");
  const outputPath = path.join(dir, "gitbench.db");

  try {
    writeFileSync(inputPath, JSON.stringify(makeResults()));

    const result = spawnSync(
      process.execPath,
      [
        "scripts/build-db.mjs",
        "--input",
        inputPath,
        "--output",
        outputPath,
        "--schema",
        path.resolve("data/schema.sql"),
      ],
      {
        cwd: process.cwd(),
        encoding: "utf8",
      },
    );

    assert.equal(result.status, 0, result.stderr);

    const db = new DatabaseSync(outputPath, { readOnly: true });
    try {
      assert.equal(
        db.prepare("SELECT COUNT(*) AS count FROM models").get().count,
        2,
      );
      assert.equal(
        db.prepare("SELECT COUNT(*) AS count FROM fixture_results").get().count,
        4,
      );
      assert.equal(db.prepare("PRAGMA integrity_check").get().integrity_check, "ok");
      assert.deepEqual(db.prepare("PRAGMA foreign_key_check").all(), []);
      assert.deepEqual(
        db
          .prepare(
            `SELECT fixture_id, output_mode, duration_ms, api_duration_ms
             FROM fixture_results
             ORDER BY output_mode, fixture_id`,
          )
          .all()
          .map((row) => ({ ...row })),
        [
          { fixture_id: "f001", output_mode: "json_schema", duration_ms: 30, api_duration_ms: 15.0 },
          { fixture_id: "f002", output_mode: "json_schema", duration_ms: 50, api_duration_ms: 25.0 },
          { fixture_id: "f001", output_mode: "text", duration_ms: 25, api_duration_ms: 12.5 },
          { fixture_id: "f002", output_mode: "text", duration_ms: 40, api_duration_ms: null },
        ],
      );

      // Verify output_mode is stored in all relevant tables
      const modelOutputModes = db
        .prepare("SELECT name, output_mode FROM models ORDER BY output_mode")
        .all()
        .map((row) => ({ ...row }));
      assert.deepEqual(modelOutputModes, [
        { name: "openai/gpt-test:high", output_mode: "json_schema" },
        { name: "openai/gpt-test:high", output_mode: "text" },
      ]);

      // Verify structured-output payload fields are stored
      const jsonPayload = db
        .prepare(
          `SELECT parsed_payload, raw_structured_output, structured_error
           FROM fixture_results
           WHERE output_mode = 'json_schema' AND fixture_id = 'f001'`,
        )
        .get();
      assert.equal(jsonPayload.parsed_payload, '{"commit":"fix fixture"}');
      assert.equal(jsonPayload.raw_structured_output, '{"commit":"fix fixture"}');
      assert.equal(jsonPayload.structured_error, null);

      // Text mode has null structured fields
      const textPayload = db
        .prepare(
          `SELECT parsed_payload, raw_structured_output, structured_error
           FROM fixture_results
           WHERE output_mode = 'text' AND fixture_id = 'f001'`,
        )
        .get();
      assert.equal(textPayload.parsed_payload, null);
      assert.equal(textPayload.raw_structured_output, null);

      const schema = readFileSync(path.resolve("data/schema.sql"), "utf8");
      assert.match(schema, /idx_benchmark_summaries_leaderboard/);

      assert.equal(
        db.prepare("SELECT COUNT(*) AS count FROM campaigns").get().count,
        1,
      );
      assert.equal(
        db.prepare("SELECT COUNT(*) AS count FROM raw_attempts").get().count,
        1,
      );
      assert.deepEqual(
        {
          ...db
            .prepare(
              `SELECT campaign_id, trial_index, model_name, reasoning_level,
                      output_mode, benchmark_name, fixture_id, status
               FROM raw_attempts`,
            )
            .get(),
        },
        {
          campaign_id: "cmp-build",
          trial_index: 1,
          model_name: "openai/gpt-test:high",
          reasoning_level: "high",
          output_mode: "text",
          benchmark_name: "commit_messages",
          fixture_id: "f001",
          status: "valid_pass",
        },
      );
    } finally {
      db.close();
    }
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("build-db derives campaign benchmarks, fixtures, and models without legacy aggregates", () => {
  const dir = mkdtempSync(path.join(tmpdir(), "gitbench-build-db-campaign-"));
  const inputPath = path.join(dir, "results.json");
  const outputPath = path.join(dir, "gitbench.db");
  const data = makeResults();
  data.models = [];
  data.benchmarks = [];
  data.model_summaries = {};
  data.model_runtimes = {};
  data.matrix = {};
  data.fixtures = {};
  data.fixture_index = {};
  data.runs_meta = [];
  data.base_model_groups = [];

  try {
    writeFileSync(inputPath, JSON.stringify(data));

    const result = spawnSync(
      process.execPath,
      [
        "scripts/build-db.mjs",
        "--input",
        inputPath,
        "--output",
        outputPath,
        "--schema",
        path.resolve("data/schema.sql"),
      ],
      {
        cwd: process.cwd(),
        encoding: "utf8",
      },
    );

    assert.equal(result.status, 0, result.stderr);

    const db = new DatabaseSync(outputPath, { readOnly: true });
    try {
      assert.equal(db.prepare("PRAGMA integrity_check").get().integrity_check, "ok");
      assert.deepEqual(db.prepare("PRAGMA foreign_key_check").all(), []);
      assert.equal(
        db.prepare("SELECT COUNT(*) AS count FROM models").get().count,
        1,
      );
      assert.equal(
        db.prepare("SELECT COUNT(*) AS count FROM benchmarks").get().count,
        1,
      );
      assert.equal(
        db.prepare("SELECT COUNT(*) AS count FROM fixtures").get().count,
        1,
      );
      assert.deepEqual(
        {
          ...db
            .prepare(
              `SELECT benchmark_name, fixture_id
               FROM fixtures`,
            )
            .get(),
        },
        { benchmark_name: "commit_messages", fixture_id: "f001" },
      );
    } finally {
      db.close();
    }
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("validate-artifacts accepts fresh SQLite and rejects stale SQLite", () => {
  const dir = mkdtempSync(path.join(tmpdir(), "gitbench-artifact-contract-"));
  const inputPath = path.join(dir, "results.json");
  const outputPath = path.join(dir, "gitbench.db");
  const staleInputPath = path.join(dir, "stale-results.json");
  const staleDbPath = path.join(dir, "stale-gitbench.db");
  const schemaPath = path.resolve("data/schema.sql");

  try {
    const data = makeResults();
    writeFileSync(inputPath, JSON.stringify(data));
    assert.equal(
      spawnSync(
        process.execPath,
        [
          "scripts/build-db.mjs",
          "--input",
          inputPath,
          "--output",
          outputPath,
          "--schema",
          schemaPath,
        ],
        { cwd: process.cwd(), encoding: "utf8" },
      ).status,
      0,
    );

    const fresh = spawnSync(
      process.execPath,
      [
        "scripts/validate-artifacts.mjs",
        "--json",
        inputPath,
        "--schema",
        schemaPath,
        "--db",
        outputPath,
      ],
      { cwd: process.cwd(), encoding: "utf8" },
    );
    assert.equal(fresh.status, 0, fresh.stderr);

    const staleData = makeResults();
    staleData.fixtures["openai/gpt-test:high"].commit_messages.pop();
    writeFileSync(staleInputPath, JSON.stringify(staleData));
    assert.equal(
      spawnSync(
        process.execPath,
        [
          "scripts/build-db.mjs",
          "--input",
          staleInputPath,
          "--output",
          staleDbPath,
          "--schema",
          schemaPath,
        ],
        { cwd: process.cwd(), encoding: "utf8" },
      ).status,
      0,
    );

    const stale = spawnSync(
      process.execPath,
      [
        "scripts/validate-artifacts.mjs",
        "--json",
        inputPath,
        "--schema",
        schemaPath,
        "--db",
        staleDbPath,
      ],
      { cwd: process.cwd(), encoding: "utf8" },
    );
    assert.notEqual(stale.status, 0);
    assert.match(stale.stderr, /gitbench\.db is stale/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

function makeResults() {
  return {
    models: [
      {
        name: "openai/gpt-test:high",
        provider: "openai",
        baseModel: "gpt-test",
        reasoningLevel: "high",
        output_mode: "text",
      },
      {
        name: "openai/gpt-test:high__json_schema",
        provider: "openai",
        baseModel: "gpt-test",
        reasoningLevel: "high",
        output_mode: "json_schema",
      },
    ],
    benchmarks: ["commit_messages"],
    model_summaries: {
      "openai/gpt-test:high": {
        total_runs: 1,
        total_fixtures: 2,
        total_passed: 2,
        pass_at_k: 1,
        total_cost_usd: 0.01,
        avg_cost_usd: 0.01,
      },
      "openai/gpt-test:high__json_schema": {
        total_runs: 1,
        total_fixtures: 2,
        total_passed: 2,
        pass_at_k: 1,
        total_cost_usd: 0.01,
        avg_cost_usd: 0.01,
      },
    },
    model_runtimes: {
      "openai/gpt-test:high": {
        total_ms: 12.5,
        avg_ms: 12.5,
        min_ms: 12.5,
        max_ms: 12.5,
        fixture_count: 1,
      },
      "openai/gpt-test:high__json_schema": {
        total_ms: 15.0,
        avg_ms: 15.0,
        min_ms: 15.0,
        max_ms: 15.0,
        fixture_count: 1,
      },
    },
    matrix: {
      "openai/gpt-test:high": {
        commit_messages: {
          pass_at_k: 1,
          total: 2,
          passed: 2,
          avg_similarity: 0.95,
        },
      },
      "openai/gpt-test:high__json_schema": {
        commit_messages: {
          pass_at_k: 1,
          total: 2,
          passed: 2,
          avg_similarity: 0.90,
        },
      },
    },
    fixtures: {
      "openai/gpt-test:high": {
        commit_messages: [
          {
            fixture_id: "f001",
            passed: true,
            similarity: 0.95,
            error: null,
            model_output: "full output",
            reasoning_level: "high",
            input_tokens: 10,
            output_tokens: 5,
            total_tokens: 15,
            cost_usd: 0.01,
            duration_ms: 25,
            api_duration_ms: 12.5,
            purpose: "purpose",
            difficulty: "easy",
            tags: ["basic"],
            output_mode: "text",
            parsed_payload: null,
            raw_structured_output: null,
            structured_error: null,
          },
          {
            fixture_id: "f002",
            passed: true,
            similarity: 0.95,
            error: null,
            model_output: "full output",
            reasoning_level: "high",
            input_tokens: 10,
            output_tokens: 5,
            total_tokens: 15,
            cost_usd: 0.01,
            duration_ms: 40,
            purpose: "purpose",
            difficulty: "easy",
            tags: ["basic"],
            output_mode: "text",
            parsed_payload: null,
            raw_structured_output: null,
            structured_error: null,
          },
        ],
      },
      "openai/gpt-test:high__json_schema": {
        commit_messages: [
          {
            fixture_id: "f001",
            passed: true,
            similarity: 0.90,
            error: null,
            model_output: "canonical text",
            reasoning_level: "high",
            input_tokens: 10,
            output_tokens: 5,
            total_tokens: 15,
            cost_usd: 0.01,
            duration_ms: 30,
            api_duration_ms: 15.0,
            purpose: "purpose",
            difficulty: "easy",
            tags: ["basic"],
            output_mode: "json_schema",
            parsed_payload: { commit: "fix fixture" },
            raw_structured_output: '{"commit":"fix fixture"}',
            structured_error: null,
          },
          {
            fixture_id: "f002",
            passed: true,
            similarity: 0.90,
            error: null,
            model_output: "canonical text",
            reasoning_level: "high",
            input_tokens: 10,
            output_tokens: 5,
            total_tokens: 15,
            cost_usd: 0.01,
            duration_ms: 50,
            api_duration_ms: 25.0,
            purpose: "purpose",
            difficulty: "easy",
            tags: ["basic"],
            output_mode: "json_schema",
            parsed_payload: { commit: "fix thing" },
            raw_structured_output: '{"commit":"fix thing"}',
            structured_error: null,
          },
        ],
      },
    },
    fixture_index: {
      "commit_messages/f001": {
        id: "f001",
        benchmark: "commit_messages",
        prompt: "prompt",
        expected: "expected",
        description: "description",
        setup: ["git init"],
        purpose: "purpose",
        difficulty: "easy",
        tags: ["basic"],
      },
      "commit_messages/f002": {
        id: "f002",
        benchmark: "commit_messages",
        prompt: "prompt",
        expected: "expected",
        description: "description",
        setup: ["git init"],
        purpose: "purpose",
        difficulty: "easy",
        tags: ["basic"],
      },
    },
    runs_meta: [
      {
        timestamp: "2026-01-01T00:00:00Z",
        model: "openai/gpt-test:high",
        output_mode: "text",
        profile: "default",
        git_sha: "abc123",
        benchmark_suite_version: "0.1.0",
        reasoning_level: "high",
      },
      {
        timestamp: "2026-01-01T01:00:00Z",
        model: "openai/gpt-test:high",
        output_mode: "json_schema",
        profile: "default",
        git_sha: "abc123",
        benchmark_suite_version: "0.1.0",
        reasoning_level: "high",
      },
    ],
    base_model_groups: [
      {
        provider: "openai",
        baseModel: "gpt-test",
        levels: [
          {
            level: "high",
            modelName: "openai/gpt-test:high",
            pass_at_k: 1,
            total_cost_usd: 0.01,
          },
          {
            level: "high",
            modelName: "openai/gpt-test:high__json_schema",
            pass_at_k: 1,
            total_cost_usd: 0.01,
          },
        ],
      },
    ],
    campaigns: [
      {
        campaign_id: "cmp-build",
        created_at: "2026-06-01T00:00:00Z",
        config_hash: "abc",
        state: "complete",
        planned_attempts: 1,
        completed_attempts: 1,
        valid_attempts: 1,
        passing_attempts: 1,
        excluded_attempts: 0,
        publication_state: "published",
        legacy: false,
        benchmark_ids: ["commit_messages"],
        model_ids: ["openai/gpt-test:high"],
        output_modes: ["text"],
        planned_trial_count: 1,
        trials: [
          {
            trial_index: 1,
            planned_attempts: 1,
            completed_attempts: 1,
            valid_attempts: 1,
            passing_attempts: 1,
            excluded_attempts: 0,
            complete: true,
          },
        ],
        raw_attempts: [
          {
            identity: {
              campaign_id: "cmp-build",
              trial_index: 1,
              model_id: "openai/gpt-test:high",
              reasoning_effort: "high",
              output_mode: "text",
              benchmark: "commit_messages",
              fixture_id: "f001",
            },
            status: "valid_pass",
            passed: true,
            similarity: 0.95,
            error: null,
            model_output: "git commit -m test",
            input_tokens: 10,
            output_tokens: 5,
            total_tokens: 15,
            cost_usd: 0.01,
            api_duration_ms: 12.5,
            safety_state: "reviewed",
          },
        ],
        fixture_aggregates: [
          {
            benchmark: "commit_messages",
            fixture_id: "f001",
            model_id: "openai/gpt-test:high",
            reasoning_effort: "high",
            output_mode: "text",
            planned_trials: 1,
            completed_trials: 1,
            valid_attempts: 1,
            passing_attempts: 1,
            failing_attempts: 0,
            excluded_attempts: 0,
            mean_success_rate: 1,
            pass_any_at_n: { 1: true },
            reliability_classification: "stable_pass",
            incomplete: false,
          },
        ],
        model_summaries: [
          {
            model_id: "openai/gpt-test:high",
            reasoning_effort: "high",
            output_mode: "text",
            planned_trials: 1,
            completed_trials: 1,
            valid_attempts: 1,
            passing_attempts: 1,
            excluded_attempts: 0,
            mean_success_rate: 1,
            pass_any_at_n: { 1: true },
            incomplete: false,
            resource_summary: {
              total_cost_usd: 0.01,
              mean_cost_per_complete_trial_usd: 0.01,
            },
          },
        ],
        benchmark_summaries: [
          {
            benchmark: "commit_messages",
            planned_trials: 1,
            completed_trials: 1,
            valid_attempts: 1,
            passing_attempts: 1,
            excluded_attempts: 0,
            mean_success_rate: 1,
            pass_any_at_n: { 1: true },
            incomplete: false,
          },
        ],
        resource_summaries: [
          {
            scope: "campaign",
            total_cost_usd: 0.01,
            total_input_tokens: 10,
            total_output_tokens: 5,
            total_tokens: 15,
            partial_pricing: false,
          },
        ],
        safety_summary: {
          reviewed: 1,
          sanitized: 0,
          blocked: 0,
          pending: 0,
        },
      },
    ],
  };
}
