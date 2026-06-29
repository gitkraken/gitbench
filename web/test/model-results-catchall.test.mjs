import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

import { clearReportStoreCache } from "../src/lib/node-sqlite-report-store.ts";
import modelResultsHandler from "../api/models/[...model]/results.ts";

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
  const dir = mkdtempSync(path.join(tmpdir(), "gitbench-model-results-"));
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
    INSERT INTO fixture_tags (benchmark_name, fixture_id, tag)
    VALUES ('commit_messages', 'f001', 'basic');
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

test("catch-all model-results route resolves two-segment provider/model URL", () => {
  withStore(() => {
    const response = callHandler(modelResultsHandler, {
      model: ["openai", "gpt-test:high"],
    });
    assert.equal(response.statusCode, 200);
    assert.ok(response.body.results);
    assert.ok(response.body.results.commit_messages);
  });
});

test("catch-all model-results route resolves single-segment model URL", () => {
  withStore(() => {
    const response = callHandler(modelResultsHandler, {
      model: "openai/gpt-test:high",
    });
    assert.equal(response.statusCode, 200);
    assert.ok(response.body.results);
  });
});

test("catch-all model-results route rejects missing model parameter", () => {
  withStore(() => {
    const response = callHandler(modelResultsHandler, {});
    assert.equal(response.statusCode, 400);
    assert.match(response.body.error, /Missing model/);
  });
});

test("catch-all model-results route preserves benchmark filter", () => {
  withStore(() => {
    const response = callHandler(modelResultsHandler, {
      model: ["openai", "gpt-test:high"],
      benchmark: "commit_messages",
    });
    assert.equal(response.statusCode, 200);
    assert.ok(response.body.results.commit_messages);
  });
});

test("catch-all model-results route preserves difficulty filter", () => {
  withStore(() => {
    const response = callHandler(modelResultsHandler, {
      model: ["openai", "gpt-test:high"],
      difficulty: "easy",
    });
    assert.equal(response.statusCode, 200);
    assert.ok(response.body.results);
  });
});

test("catch-all model-results route preserves tag filter", () => {
  withStore(() => {
    const response = callHandler(modelResultsHandler, {
      model: ["openai", "gpt-test:high"],
      tag: "basic",
    });
    assert.equal(response.statusCode, 200);
    assert.ok(response.body.results);
  });
});

test("catch-all model-results route preserves output_mode filter", () => {
  withStore(() => {
    const response = callHandler(modelResultsHandler, {
      model: ["openai", "gpt-test:high"],
      output_mode: "text",
    });
    assert.equal(response.statusCode, 200);
    assert.ok(response.body.results);
  });
});

test("catch-all model-results route rejects invalid output_mode", () => {
  withStore(() => {
    const response = callHandler(modelResultsHandler, {
      model: ["openai", "gpt-test:high"],
      output_mode: "xml",
    });
    assert.equal(response.statusCode, 400);
    assert.match(response.body.error, /Invalid output_mode/);
  });
});

test("catch-all model-results route returns 404 for unknown model", () => {
  withStore(() => {
    const response = callHandler(modelResultsHandler, {
      model: ["unknown", "nonexistent"],
    });
    assert.equal(response.statusCode, 404);
    assert.match(response.body.error, /Model not found/);
  });
});