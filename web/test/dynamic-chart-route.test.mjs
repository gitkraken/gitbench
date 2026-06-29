import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

import { clearReportStoreCache } from "../src/lib/node-sqlite-report-store.ts";
import chartRouteHandler from "../api/charts/[chart].ts";

function callHandler(handler, query) {
  clearReportStoreCache();
  const res = {
    statusCode: null,
    headers: {},
    body: "",
    status(code) {
      this.statusCode = code;
      return this;
    },
    setHeader(key, value) {
      this.headers[key] = value;
      return this;
    },
    end(payload) {
      this.body = payload;
    },
  };
  handler({ query }, res);
  return {
    statusCode: res.statusCode,
    body: JSON.parse(res.body),
  };
}

function withStore(fn) {
  const dir = mkdtempSync(path.join(tmpdir(), "gitbench-chart-"));
  const dbPath = path.join(dir, "gitbench.db");
  const db = new DatabaseSync(dbPath);
  const previousDbEnv = process.env.GITBENCH_REPORT_DB;
  try {
    db.exec(readFileSync(path.resolve("data/schema.sql"), "utf8"));
    seedStore(db);
    process.env.GITBENCH_REPORT_DB = dbPath;
    clearReportStoreCache();
    fn();
  } finally {
    db.close();
    rmSync(dir, { recursive: true, force: true });
    if (previousDbEnv === undefined) {
      delete process.env.GITBENCH_REPORT_DB;
    } else {
      process.env.GITBENCH_REPORT_DB = previousDbEnv;
    }
    clearReportStoreCache();
  }
}

function seedStore(db) {
  db.exec(`
    INSERT INTO models (name, provider, base_model, reasoning_level, output_mode)
    VALUES ('openai/gpt-test:high', 'openai', 'gpt-test', 'high', 'text');
    INSERT INTO benchmarks (name) VALUES ('commit_messages');
    INSERT INTO runs (
      timestamp, model_name, output_mode, profile, git_sha, benchmark_suite_version,
      reasoning_level
    )
    VALUES (
      '2026-01-01T00:00:00Z', 'openai/gpt-test:high', 'text', 'default', 'abc123',
      '0.1.0', 'high'
    );
    INSERT INTO model_summaries (
      model_name, output_mode, total_runs, total_fixtures, total_passed, pass_at_k,
      total_cost_usd, avg_cost_usd
    )
    VALUES ('openai/gpt-test:high', 'text', 1, 1, 1, 1.0, 0.01, 0.01);
    INSERT INTO model_runtimes (
      model_name, output_mode, total_ms, avg_ms, min_ms, max_ms, fixture_count
    )
    VALUES ('openai/gpt-test:high', 'text', 12.5, 12.5, 12.5, 12.5, 1);
    INSERT INTO benchmark_summaries (
      model_name, output_mode, benchmark_name, pass_at_k, total, passed, avg_similarity
    )
    VALUES ('openai/gpt-test:high', 'text', 'commit_messages', 1.0, 1, 1, 0.95);
    INSERT INTO fixtures (
      benchmark_name, fixture_id, prompt, expected, description, setup_json,
      purpose, difficulty
    )
    VALUES (
      'commit_messages', 'f001', 'prompt', 'expected', 'description',
      '["git init"]', 'purpose', 'easy'
    );
    INSERT INTO fixture_results (
      model_name, output_mode, benchmark_name, fixture_id, passed, similarity, error,
      model_output, reasoning_level, input_tokens, output_tokens, total_tokens,
      cost_usd, duration_ms, api_duration_ms, purpose, difficulty, tags_json
    )
    VALUES (
      'openai/gpt-test:high', 'text', 'commit_messages', 'f001', 1, 0.95, NULL,
      'full output', 'high', 10, 5, 15, 0.01, 25, 12.5, 'purpose', 'easy',
      '["basic"]'
    );
    INSERT INTO base_model_groups (id, provider, base_model)
    VALUES (1, 'openai', 'gpt-test');
    INSERT INTO base_model_group_levels (
      group_id, level, model_name, output_mode, pass_at_k, total_cost_usd
    )
    VALUES (1, 'high', 'openai/gpt-test:high', 'text', 1.0, 0.01);
  `);
}

test("dynamic chart route dispatches pass-rate chart successfully", () => {
  withStore(() => {
    const response = callHandler(chartRouteHandler, { chart: "pass-rate" });
    assert.equal(response.statusCode, 200);
    assert.equal(response.body.models.length, 1);
    assert.ok(response.body.model_summaries);
    assert.ok(response.body.campaign_id !== undefined);
  });
});

test("dynamic chart route dispatches cost chart successfully", () => {
  withStore(() => {
    const response = callHandler(chartRouteHandler, { chart: "cost" });
    assert.equal(response.statusCode, 200);
    assert.ok(response.body.model_summaries);
  });
});

test("dynamic chart route dispatches heatmap chart successfully", () => {
  withStore(() => {
    const response = callHandler(chartRouteHandler, { chart: "heatmap" });
    assert.equal(response.statusCode, 200);
    assert.ok(response.body.matrix);
  });
});

test("dynamic chart route dispatches runtime chart successfully", () => {
  withStore(() => {
    const response = callHandler(chartRouteHandler, { chart: "runtime" });
    assert.equal(response.statusCode, 200);
    assert.ok(response.body.model_runtimes);
  });
});

test("dynamic chart route dispatches tokens chart successfully", () => {
  withStore(() => {
    const response = callHandler(chartRouteHandler, { chart: "tokens" });
    assert.equal(response.statusCode, 200);
    assert.ok(response.body.model_token_summaries);
  });
});

test("dynamic chart route dispatches quadrant chart successfully", () => {
  withStore(() => {
    const response = callHandler(chartRouteHandler, { chart: "quadrant" });
    assert.equal(response.statusCode, 200);
    assert.ok(response.body.model_runtimes);
    assert.ok(response.body.model_token_summaries);
  });
});

test("dynamic chart route preserves benchmark filter for pass-rate chart", () => {
  withStore(() => {
    const response = callHandler(chartRouteHandler, {
      chart: "pass-rate",
      benchmark: "commit_messages",
    });
    assert.equal(response.statusCode, 200);
    assert.deepEqual(response.body.benchmarks, ["commit_messages"]);
    assert.ok(response.body.matrix);
  });
});

test("dynamic chart route rejects unsupported chart name with 404", () => {
  withStore(() => {
    const response = callHandler(chartRouteHandler, { chart: "not-a-chart" });
    assert.equal(response.statusCode, 404);
    assert.match(response.body.error, /Unknown chart/);
  });
});

test("dynamic chart route rejects missing chart parameter", () => {
  withStore(() => {
    const response = callHandler(chartRouteHandler, {});
    assert.equal(response.statusCode, 404);
    assert.match(response.body.error, /Unknown chart/);
  });
});