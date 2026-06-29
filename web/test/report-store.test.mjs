import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";

import { NodeSqliteReportStore } from "../src/lib/node-sqlite-report-store.ts";
import { computeModeComparison } from "../src/lib/model-comparison.ts";
import { deriveModelGroups } from "../src/components/charts/model-groups.ts";
import modelResultsHandler from "../api/models/[...model]/results.ts";
import fixtureHandler from "../api/fixtures/[benchmark]/[...fixture].ts";
import campaignsHandler from "../api/campaigns/index.ts";
import summaryHandler from "../api/summary.ts";
import chartRouteHandler from "../api/charts/[chart].ts";

import { clearReportStoreCache } from "../src/lib/node-sqlite-report-store.ts";

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

function withStore(fn, { seedFn = seedWithBothModes } = {}) {
  const dir = mkdtempSync(path.join(tmpdir(), "gitbench-store-"));
  const dbPath = path.join(dir, "gitbench.db");
  const db = new DatabaseSync(dbPath);
  const previousDbEnv = process.env.GITBENCH_REPORT_DB;
  try {
    db.exec(readFileSync(path.resolve("data/schema.sql"), "utf8"));
    seedFn(db);
    process.env.GITBENCH_REPORT_DB = dbPath;
    clearReportStoreCache();
    fn(new NodeSqliteReportStore(db));
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

function seedTextOnly(db) {
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

function seedWithBothModes(db) {
  db.exec(`
    INSERT INTO models (name, provider, base_model, reasoning_level, output_mode)
    VALUES
      ('openai/gpt-test:high', 'openai', 'gpt-test', 'high', 'text'),
      ('openai/gpt-test:high', 'openai', 'gpt-test', 'high', 'json_schema');
    INSERT INTO benchmarks (name) VALUES ('commit_messages');
    INSERT INTO runs (
      timestamp, model_name, output_mode, profile, git_sha, benchmark_suite_version,
      reasoning_level
    )
    VALUES
      ('2026-01-01T00:00:00Z', 'openai/gpt-test:high', 'text', 'default', 'abc123', '0.1.0', 'high'),
      ('2026-01-01T01:00:00Z', 'openai/gpt-test:high', 'json_schema', 'default', 'abc123', '0.1.0', 'high');
    INSERT INTO model_summaries (
      model_name, output_mode, total_runs, total_fixtures, total_passed, pass_at_k,
      total_cost_usd, avg_cost_usd
    )
    VALUES
      ('openai/gpt-test:high', 'text', 1, 1, 1, 1.0, 0.01, 0.01),
      ('openai/gpt-test:high', 'json_schema', 1, 1, 0, 0.0, 0.01, 0.01);
    INSERT INTO model_runtimes (
      model_name, output_mode, total_ms, avg_ms, min_ms, max_ms, fixture_count
    )
    VALUES
      ('openai/gpt-test:high', 'text', 12.5, 12.5, 12.5, 12.5, 1),
      ('openai/gpt-test:high', 'json_schema', 15.0, 15.0, 15.0, 15.0, 1);
    INSERT INTO benchmark_summaries (
      model_name, output_mode, benchmark_name, pass_at_k, total, passed, avg_similarity
    )
    VALUES
      ('openai/gpt-test:high', 'text', 'commit_messages', 1.0, 1, 1, 0.95),
      ('openai/gpt-test:high', 'json_schema', 'commit_messages', 0.0, 1, 0, 0.30);
    INSERT INTO fixtures (
      benchmark_name, fixture_id, prompt, expected, description, setup_json,
      purpose, difficulty
    )
    VALUES
      ('commit_messages', 'f001', 'prompt', 'expected', 'description', '["git init"]', 'purpose', 'easy');
    INSERT INTO fixture_tags (benchmark_name, fixture_id, tag)
    VALUES ('commit_messages', 'f001', 'basic');
    INSERT INTO fixture_results (
      model_name, output_mode, benchmark_name, fixture_id, passed, similarity, error,
      model_output, reasoning_level, input_tokens, output_tokens, total_tokens,
      cost_usd, duration_ms, api_duration_ms, purpose, difficulty, tags_json,
      parsed_payload, raw_structured_output, structured_error
    )
    VALUES
      ('openai/gpt-test:high', 'text', 'commit_messages', 'f001', 1, 0.95, NULL,
       'full output', 'high', 10, 5, 15, 0.01, 25, 12.5, 'purpose', 'easy',
       '["basic"]', NULL, NULL, NULL),
      ('openai/gpt-test:high', 'json_schema', 'commit_messages', 'f001', 0, 0.30, NULL,
       'canonical text', 'high', 10, 5, 15, 0.01, 30, 15.0, 'purpose', 'easy',
       '["basic"]', '{"commit":"fix thing"}', '{"commit":"fix thing"}', NULL);
    INSERT INTO base_model_groups (id, provider, base_model)
    VALUES (1, 'openai', 'gpt-test');
    INSERT INTO base_model_group_levels (
      group_id, level, model_name, output_mode, pass_at_k, total_cost_usd
    )
    VALUES
      (1, 'high', 'openai/gpt-test:high', 'text', 1.0, 0.01),
      (1, 'high', 'openai/gpt-test:high', 'json_schema', 0.0, 0.01);
  `);
}

function seedInvalidStructuredOutput(db) {
  seedWithBothModes(db);
  db.exec(`
    INSERT INTO fixtures (
      benchmark_name, fixture_id, prompt, expected, description, setup_json,
      purpose, difficulty
    )
    VALUES (
      'commit_messages', 'f002', 'prompt', 'expected', 'description',
      '["git init"]', 'purpose', 'easy'
    );
    INSERT INTO fixture_results (
      model_name, output_mode, benchmark_name, fixture_id, passed, similarity, error,
      model_output, reasoning_level, input_tokens, output_tokens, total_tokens,
      cost_usd, duration_ms, api_duration_ms, purpose, difficulty, tags_json,
      parsed_payload, raw_structured_output, structured_error
    )
    VALUES (
      'openai/gpt-test:high', 'json_schema', 'commit_messages', 'f002', 0, 0.0,
      'Structured output schema validation failed', '{"commit":42}', 'high',
      10, 5, 15, 0.01, 30, 15.0, 'purpose', 'easy', '["basic"]', NULL,
      '{"commit":42}', 'Structured output schema validation failed'
    );
  `);
}

test("summary returns compact report data without full model output", () => {
  withStore((store) => {
    const summary = store.getSummary();
    assert.equal(summary.models.length, 2);
    assert.equal(summary.benchmarks[0], "commit_messages");
    assert.deepEqual(summary.fixtures, {});
    assert.deepEqual(summary.fixture_index, {});
    // Both output modes are keyed by composite modelModeKey
    assert.equal(
      summary.model_token_summaries["openai/gpt-test:high"].total_tokens,
      15,
    );
    assert.equal(
      summary.model_token_summaries["openai/gpt-test:high__json_schema"].total_tokens,
      15,
    );
    assert.equal(
      summary.model_token_summaries["openai/gpt-test:high"].reasoning_tokens,
      null,
    );
    assert.equal(summary.model_runtimes["openai/gpt-test:high"].total_ms, 12.5);
    assert.equal(
      summary.model_runtimes["openai/gpt-test:high__json_schema"].total_ms,
      15.0,
    );
  });
});

test("benchmark and model result queries return scoped rows", () => {
  withStore((store) => {
    const benchmark = store.getBenchmark("commit_messages");
    assert.equal(benchmark.benchmark, "commit_messages");
    assert.equal(benchmark.tag_counts.basic, 1);

    const model = store.getModelResults("openai/gpt-test:high", {
      benchmark: "commit_messages",
      difficulty: "easy",
      tag: "basic",
    });
    assert.equal(model.results.commit_messages[0].model_output, "");
    assert.equal(model.results.commit_messages[0].api_duration_ms, 12.5);
    assert.equal(model.results.commit_messages[0].output_mode, "text");
  });
});

test("fixture detail returns full outputs and missing resources return null", () => {
  withStore((store) => {
    const fixture = store.getFixture("commit_messages", "f001");
    assert.equal(fixture.outputs.length, 2);
    const textOutput = fixture.outputs.find((o) => o.output_mode === "text");
    const jsonOutput = fixture.outputs.find((o) => o.output_mode === "json_schema");
    assert.equal(textOutput.model_output, "full output");
    assert.equal(textOutput.api_duration_ms, 12.5);
    assert.equal(jsonOutput.model_output, "canonical text");
    assert.equal(jsonOutput.output_mode, "json_schema");

    assert.equal(store.getBenchmark("missing"), null);
    assert.equal(store.getModelResults("missing"), null);
    assert.equal(store.getFixture("commit_messages", "missing"), null);
  });
});

test("text mode defaults: model without json_schema returns text results", () => {
  withStore((store) => {
    const model = store.getModelResults("openai/gpt-test:high");
    assert.ok(model);
    assert.equal(model.results.commit_messages[0].output_mode, "text");
  }, { seedFn: seedTextOnly });
});

test("JSON-schema rows: model with json_schema returns structured output", () => {
  withStore((store) => {
    // JSON-schema mode model is accessed with the composite key
    const textResult = store.getModelResults("openai/gpt-test:high");
    assert.ok(textResult);
    assert.equal(textResult.results.commit_messages[0].output_mode, "text");
  });
});

test("compact omissions: summary does not include bulk structured output", () => {
  withStore((store) => {
    const summary = store.getSummary();
    // Summary returns empty fixtures — bulky fields omitted
    assert.deepEqual(summary.fixtures, {});
  });
});

test("fixture-detail structured payloads: json_schema result includes parsed_payload", () => {
  withStore((store) => {
    const fixture = store.getFixture("commit_messages", "f001");
    const jsonOutput = fixture.outputs.find((o) => o.output_mode === "json_schema");
    assert.ok(jsonOutput);
    assert.equal(jsonOutput.parsed_payload, '{"commit":"fix thing"}');
    assert.equal(jsonOutput.raw_structured_output, '{"commit":"fix thing"}');
    assert.equal(jsonOutput.structured_error, null);
  });
});

test("fixture detail text result has null structured fields", () => {
  withStore((store) => {
    const fixture = store.getFixture("commit_messages", "f001");
    const textOutput = fixture.outputs.find((o) => o.output_mode === "text");
    assert.ok(textOutput);
    assert.equal(textOutput.parsed_payload, null);
    assert.equal(textOutput.raw_structured_output, null);
    assert.equal(textOutput.structured_error, null);
  });
});

test("fixture detail preserves invalid structured-output display fields", () => {
  withStore((store) => {
    const fixture = store.getFixture("commit_messages", "f002");
    assert.ok(fixture);
    assert.equal(fixture.outputs.length, 1);
    assert.equal(fixture.outputs[0].model_output, '{"commit":42}');
    assert.equal(fixture.outputs[0].parsed_payload, null);
    assert.equal(fixture.outputs[0].raw_structured_output, '{"commit":42}');
    assert.equal(
      fixture.outputs[0].structured_error,
      "Structured output schema validation failed",
    );
  }, { seedFn: seedInvalidStructuredOutput });
});

test("history includes output_mode", () => {
  withStore((store) => {
    const summary = store.getSummary();
    assert.equal(summary.runs_meta.length, 2);
    const modes = new Set(summary.runs_meta.map((r) => r.output_mode));
    assert.deepEqual(modes, new Set(["text", "json_schema"]));
  });
});

test("getModels includes output_mode field", () => {
  withStore((store) => {
    const models = store.getModels();
    assert.equal(models.length, 2);
    for (const m of models) {
      assert.ok(typeof m.output_mode === "string");
    }
    const modes = new Set(models.map((m) => m.output_mode));
    assert.deepEqual(modes, new Set(["text", "json_schema"]));
  });
});

test("base_model_groups include both output mode variants", () => {
  withStore((store) => {
    const summary = store.getSummary();
    assert.equal(summary.base_model_groups.length, 1);
    const levels = summary.base_model_groups[0].levels;
    assert.equal(levels.length, 2);
    const modelNames = new Set(levels.map((l) => l.modelName));
    assert.deepEqual(
      modelNames,
      new Set(["openai/gpt-test:high", "openai/gpt-test:high__json_schema"]),
    );
  });
});

test("frontend model groups preserve JSON-schema effort identity", () => {
  withStore((store) => {
    const groups = deriveModelGroups(store.getSummary());
    assert.equal(groups.length, 1);
    assert.deepEqual(
      Object.fromEntries(
        groups[0].efforts.map((effort) => [
          effort.modelName,
          effort.outputMode,
        ]),
      ),
      {
        "openai/gpt-test:high": "text",
        "openai/gpt-test:high__json_schema": "json_schema",
      },
    );
  });
});

test("model detail comparison: both modes return per-fixture results", () => {
  withStore((store) => {
    const textResults = store.getModelResults("openai/gpt-test:high");
    const jsonResults = store.getModelResults("openai/gpt-test:high__json_schema");

    assert.ok(textResults);
    assert.ok(jsonResults);

    // Text mode: fixture f001 passed
    const textFixture = textResults.results.commit_messages[0];
    assert.equal(textFixture.fixture_id, "f001");
    assert.equal(textFixture.output_mode, "text");
    assert.equal(textFixture.passed, true);
    assert.equal(textFixture.similarity, 0.95);

    // JSON schema mode: fixture f001 failed
    const jsonFixture = jsonResults.results.commit_messages[0];
    assert.equal(jsonFixture.fixture_id, "f001");
    assert.equal(jsonFixture.output_mode, "json_schema");
    assert.equal(jsonFixture.passed, false);
    assert.equal(jsonFixture.similarity, 0.30);

    // Verify pass rates differ
    const summary = store.getSummary();
    const textSummary = summary.model_summaries["openai/gpt-test:high"];
    const jsonSummary = summary.model_summaries["openai/gpt-test:high__json_schema"];
    assert.equal(textSummary.pass_at_k, 1.0);
    assert.equal(jsonSummary.pass_at_k, 0.0);
  });
});

test("model results output_mode filter selects requested mode", () => {
  withStore((store) => {
    const result = store.getModelResults("openai/gpt-test:high", {
      output_mode: "json_schema",
    });

    assert.ok(result);
    assert.equal(result.model, "openai/gpt-test:high__json_schema");
    const fixture = result.results.commit_messages[0];
    assert.equal(fixture.output_mode, "json_schema");
    assert.equal(fixture.passed, false);
  });
});

test("model results route accepts output_mode query parameter", () => {
  const response = callHandler(modelResultsHandler, {
    model: ["openai", "gpt-test:high"],
    output_mode: "xml",
  });

  assert.equal(response.statusCode, 400);
  assert.match(response.body.error, /Invalid output_mode/);
});

test("model detail comparison: computeModeComparison returns correct deltas", () => {
  withStore((store) => {
    const comparison = computeModeComparison(
      store,
      "openai/gpt-test:high",
      "openai/gpt-test:high__json_schema",
    );

    assert.ok(comparison);
    assert.equal(comparison.textPassRate, 1.0);
    assert.equal(comparison.jsonPassRate, 0.0);
    assert.equal(comparison.passRateDelta, -1.0);

    // Text mode passed, JSON mode failed -> lost
    assert.equal(comparison.gained, 0);
    assert.equal(comparison.lost, 1);
    assert.equal(comparison.unchangedPass, 0);
    assert.equal(comparison.unchangedFail, 0);
    assert.equal(comparison.totalFixtures, 1);

    // Benchmark deltas
    assert.equal(comparison.benchmarkDeltas.length, 1);
    const bd = comparison.benchmarkDeltas[0];
    assert.equal(bd.benchmark, "commit_messages");
    assert.equal(bd.textPassRate, 1.0);
    assert.equal(bd.jsonPassRate, 0.0);
    assert.equal(bd.delta, -1.0);

    // Changed fixtures
    assert.equal(comparison.changedFixtures.length, 1);
    const cf = comparison.changedFixtures[0];
    assert.equal(cf.fixtureId, "f001");
    assert.equal(cf.benchmark, "commit_messages");
    assert.equal(cf.textPassed, true);
    assert.equal(cf.jsonPassed, false);
  });
});

test("model detail comparison: computeModeComparison returns null for missing mode", () => {
  withStore((store) => {
    const comparison = computeModeComparison(
      store,
      "openai/gpt-test:high",
      "nonexistent__json_schema",
    );
    assert.equal(comparison, null);
  });
});

test("output-mode selection: summary distinguishes text and json_schema keys", () => {
  withStore((store) => {
    const summary = store.getSummary();

    // Both modes have separate entries in maps
    assert.ok(summary.model_summaries["openai/gpt-test:high"]);
    assert.ok(summary.model_summaries["openai/gpt-test:high__json_schema"]);

    // Matrix distinguishes modes
    assert.ok(summary.matrix["openai/gpt-test:high"]);
    assert.ok(summary.matrix["openai/gpt-test:high__json_schema"]);
    assert.equal(
      summary.matrix["openai/gpt-test:high"].commit_messages.pass_at_k,
      1.0,
    );
    assert.equal(
      summary.matrix["openai/gpt-test:high__json_schema"].commit_messages.pass_at_k,
      0.0,
    );

    // Token summaries distinguish modes
    assert.ok(summary.model_token_summaries["openai/gpt-test:high"]);
    assert.ok(summary.model_token_summaries["openai/gpt-test:high__json_schema"]);

    // Runtime summaries distinguish modes
    assert.equal(
      summary.model_runtimes["openai/gpt-test:high"].total_ms,
      12.5,
    );
    assert.equal(
      summary.model_runtimes["openai/gpt-test:high__json_schema"].total_ms,
      15.0,
    );
  });
});

test("output-mode selection: text-only models do not have json_schema entries", () => {
  withStore((store) => {
    const summary = store.getSummary();
    assert.equal(summary.models.length, 1);
    assert.equal(summary.models[0].output_mode, "text");

    // No json_schema entry exists
    assert.equal(
      summary.model_summaries["openai/gpt-test:high__json_schema"],
      undefined,
    );
  }, { seedFn: seedTextOnly });
});


function seedCampaign(db) {
  db.exec(`
    INSERT INTO models (name, provider, base_model, reasoning_level, output_mode)
    VALUES ('openai/gpt-test:high', 'openai', 'gpt-test', 'high', 'text');
    INSERT INTO benchmarks (name) VALUES ('commit_messages');
    INSERT INTO fixtures (
      benchmark_name, fixture_id, prompt, expected, description, setup_json,
      purpose, difficulty
    )
    VALUES (
      'commit_messages', 'commit_messages/f001', 'Generate commit message',
      'feat: add login', 'description', '[]', 'purpose', 'easy'
    );
    INSERT INTO campaigns (
      campaign_id, created_at, config_hash, state, planned_attempts,
      completed_attempts, valid_attempts, passing_attempts, excluded_attempts,
      publication_state, legacy, benchmark_ids_json, model_ids_json,
      output_modes_json, planned_trial_count
    )
    VALUES (
      'cmp-test', '2026-06-01T00:00:00Z', 'abc', 'complete', 2, 2, 2, 1, 0,
      'published', 0, '["commit_messages"]', '["openai/gpt-test:high"]',
      '["text"]', 2
    );
    INSERT INTO trials (
      campaign_id, trial_index, planned_attempts, completed_attempts,
      valid_attempts, passing_attempts, excluded_attempts, complete
    )
    VALUES ('cmp-test', 1, 1, 1, 1, 1, 0, 1);
    INSERT INTO trials (
      campaign_id, trial_index, planned_attempts, completed_attempts,
      valid_attempts, passing_attempts, excluded_attempts, complete
    )
    VALUES ('cmp-test', 2, 1, 1, 1, 0, 0, 1);
    INSERT INTO raw_attempts (
      campaign_id, trial_index, model_name, reasoning_level, output_mode,
      benchmark_name, fixture_id, status, passed, similarity, error,
      input_tokens, output_tokens, total_tokens, cost_usd, api_duration_ms,
      model_output, safety_state
    )
    VALUES (
      'cmp-test', 1, 'openai/gpt-test:high', 'high', 'text',
      'commit_messages', 'commit_messages/f001', 'valid_pass', 1, 0.95, NULL,
      10, 5, 15, 0.01, 100.0, 'secret output', 'reviewed'
    );
    INSERT INTO raw_attempts (
      campaign_id, trial_index, model_name, reasoning_level, output_mode,
      benchmark_name, fixture_id, status, passed, similarity, error,
      input_tokens, output_tokens, total_tokens, cost_usd, api_duration_ms,
      model_output
    )
    VALUES (
      'cmp-test', 2, 'openai/gpt-test:high', 'high', 'text',
      'commit_messages', 'commit_messages/f001', 'valid_fail', 0, 0.3, 'bad',
      10, 5, 15, 0.01, 100.0, 'unreviewed output'
    );
    INSERT INTO fixture_aggregates (
      campaign_id, benchmark_name, fixture_id, planned_trials,
      completed_trials, valid_attempts, passing_attempts, failing_attempts,
      excluded_attempts, mean_success_rate, pass_any_at_n_json,
      reliability_classification, incomplete
    )
    VALUES (
      'cmp-test', 'commit_messages', 'commit_messages/f001', 2, 2, 2, 1, 1, 0,
      0.5, '{"1": true}', 'flaky', 0
    );
    INSERT INTO campaign_benchmark_summaries (
      campaign_id, benchmark_name, planned_trials, completed_trials,
      valid_attempts, passing_attempts, excluded_attempts, mean_success_rate,
      pass_any_at_n_json, incomplete, resource_summary_json
    )
    VALUES (
      'cmp-test', 'commit_messages', 2, 2, 2, 1, 0, 0.5, '{"1": true}', 0, NULL
    );
    INSERT INTO campaign_model_summaries (
      campaign_id, model_name, reasoning_level, output_mode, planned_trials,
      completed_trials, valid_attempts, passing_attempts, excluded_attempts,
      mean_success_rate, pass_any_at_n_json, incomplete, resource_summary_json
    )
    VALUES (
      'cmp-test', 'openai/gpt-test:high', 'high', 'text', 2, 2, 2, 1, 0,
      0.5, '{"1": true}', 0,
      '{"total_cost_usd":0.02,"mean_cost_per_complete_trial_usd":0.01}'
    );
    INSERT INTO resource_summaries (
      id, campaign_id, scope, total_cost_usd, total_input_tokens,
      total_output_tokens, total_tokens, partial_pricing
    ) VALUES (1, 'cmp-test', 'campaign', 0.02, 20, 10, 30, 0);
    INSERT INTO publication_states (
      campaign_id, reviewed_count, sanitized_count, blocked_count, pending_count
    ) VALUES ('cmp-test', 1, 0, 0, 0);
  `);
}

function seedCampaignDefaults(db) {
  seedTextOnly(db);
  db.exec(`
    INSERT INTO campaigns (
      campaign_id, created_at, config_hash, state, planned_attempts,
      completed_attempts, valid_attempts, passing_attempts, excluded_attempts,
      publication_state, legacy, benchmark_ids_json, model_ids_json,
      output_modes_json, planned_trial_count
    )
    VALUES
      (
        'cmp-older', '2026-06-01T00:00:00Z', 'abc', 'complete', 1, 1, 1, 1, 0,
        'published', 0, '["commit_messages"]', '["openai/gpt-test:high"]',
        '["text"]', 1
      ),
      (
        'cmp-latest', '2026-06-02T00:00:00Z', 'abc', 'complete', 1, 1, 1, 1, 0,
        'published', 0, '["commit_messages"]', '["openai/gpt-test:high"]',
        '["text"]', 1
      ),
      (
        'cmp-incomplete', '2026-06-03T00:00:00Z', 'abc', 'running', 1, 0, 0, 0, 0,
        'published', 0, '["commit_messages"]', '["openai/gpt-test:high"]',
        '["text"]', 1
      ),
      (
        'cmp-legacy', '2026-06-04T00:00:00Z', 'abc', 'complete', 1, 1, 1, 1, 0,
        'published', 1, '["commit_messages"]', '["openai/gpt-test:high"]',
        '["text"]', 1
      ),
      (
        'cmp-blocked', '2026-06-05T00:00:00Z', 'abc', 'complete', 1, 1, 1, 1, 0,
        'published', 0, '["commit_messages"]', '["openai/gpt-test:high"]',
        '["text"]', 1
      );
    INSERT INTO publication_states (
      campaign_id, reviewed_count, sanitized_count, blocked_count, pending_count
    )
    VALUES
      ('cmp-older', 1, 0, 0, 0),
      ('cmp-latest', 1, 0, 0, 0),
      ('cmp-incomplete', 0, 0, 0, 0),
      ('cmp-legacy', 1, 0, 0, 0),
      ('cmp-blocked', 1, 0, 1, 0);
  `);
}

test("campaign store: getCampaign returns a single campaign", () => {
  withStore((store) => {
    const campaign = store.getCampaign("cmp-test");
    assert.ok(campaign);
    assert.equal(campaign.campaign_id, "cmp-test");
    assert.equal(campaign.incomplete, false);
    assert.equal(campaign.publishable, true);
  }, { seedFn: seedCampaign });
});

test("campaign store: default campaign prefers latest publishable non-legacy complete run", () => {
  withStore((store) => {
    const campaign = store.getDefaultCampaign();
    assert.ok(campaign);
    assert.equal(campaign.campaign_id, "cmp-latest");
  }, { seedFn: seedCampaignDefaults });
});

test("campaign store: campaign summary exposes default evaluation metrics", () => {
  withStore((store) => {
    const summary = store.getSummary({ campaign_id: "cmp-test" });
    const modelSummary = summary.model_summaries["openai/gpt-test:high"];
    assert.ok(modelSummary);
    assert.equal(modelSummary.pass_at_k, 0.5);
    assert.equal(modelSummary.total_fixtures, 1);
    assert.equal(modelSummary.total_valid_attempts, 2);
    assert.equal(modelSummary.total_passing_attempts, 1);
    assert.equal(modelSummary.total_cost_usd, 0.02);
    assert.equal(
      summary.matrix["openai/gpt-test:high"].commit_messages.pass_at_k,
      0.5,
    );
  }, { seedFn: seedCampaign });
});

test("summary endpoint defaults to latest campaign when campaign rows exist", () => {
  withStore(() => {
    const response = callHandler(summaryHandler, {});
    assert.equal(response.statusCode, 200);
    assert.equal(response.body.campaign_id, "cmp-test");
    assert.equal(
      response.body.model_summaries["openai/gpt-test:high"].pass_at_k,
      0.5,
    );
  }, { seedFn: seedCampaign });
});

test("summary endpoint keeps aggregate fallback when no campaign rows exist", () => {
  withStore(() => {
    const response = callHandler(summaryHandler, {});
    assert.equal(response.statusCode, 200);
    assert.equal(response.body.campaign_id, null);
    assert.equal(
      response.body.model_summaries["openai/gpt-test:high"].pass_at_k,
      1.0,
    );
  }, { seedFn: seedTextOnly });
});

test("chart endpoint uses explicit compatible campaign data", () => {
  withStore(() => {
    const response = callHandler(chartRouteHandler, {
      chart: "pass-rate",
      campaign: "cmp-test",
    });
    assert.equal(response.statusCode, 200);
    assert.equal(response.body.campaign_id, "cmp-test");
    assert.equal(
      response.body.model_summaries["openai/gpt-test:high"].pass_at_k,
      0.5,
    );
  }, { seedFn: seedCampaign });
});

test("incompatible explicit campaign query falls back without scoped metadata", () => {
  withStore(() => {
    const response = callHandler(summaryHandler, {
      campaign: "cmp-test",
      output_mode: "json_schema",
    });
    assert.equal(response.statusCode, 200);
    assert.equal(response.body.campaign_id, null);
    assert.equal(response.body.campaign_metadata, null);
  }, { seedFn: seedCampaign });
});

test("campaign store: publication gating allows published campaigns", () => {
  withStore((store) => {
    assert.equal(store.isCampaignPublicationAllowed("cmp-test"), true);
  }, { seedFn: seedCampaign });
});

test("campaign store: raw attempts omit output by default", () => {
  withStore((store) => {
    const attempts = store.getRawAttempts("cmp-test");
    assert.equal(attempts.length, 2);
    assert.equal(attempts[0].model_output, undefined);
    assert.equal(attempts[0].safety_state, "reviewed");
  }, { seedFn: seedCampaign });
});

test("campaign store: raw attempts include output when requested", () => {
  withStore((store) => {
    const attempts = store.getRawAttempts("cmp-test", { includeOutput: true });
    assert.equal(attempts[0].model_output, "secret output");
    assert.equal(attempts[1].model_output, undefined);
  }, { seedFn: seedCampaign });
});

test("campaign store: campaign fixture omits unreviewed model output", () => {
  withStore((store) => {
    const fixture = store.getFixture("commit_messages", "commit_messages/f001", {
      campaign_id: "cmp-test",
    });
    assert.ok(fixture);
    assert.deepEqual(
      fixture.outputs.map((output) => output.model_output),
      ["secret output", ""],
    );
  }, { seedFn: seedCampaign });
});

test("campaign store: raw attempt lookup by identity", () => {
  withStore((store) => {
    const attempt = store.getRawAttemptByIdentity("cmp-test", {
      trial_index: 1,
      model_name: "openai/gpt-test:high",
      output_mode: "text",
      fixture_id: "commit_messages/f001",
    });
    assert.ok(attempt);
    assert.equal(attempt.status, "valid_pass");
  }, { seedFn: seedCampaign });
});

test("campaign store: raw attempt lookup returns null for missing identity", () => {
  withStore((store) => {
    const attempt = store.getRawAttemptByIdentity("cmp-test", {
      trial_index: 99,
      model_name: "openai/gpt-test:high",
      output_mode: "text",
      fixture_id: "commit_messages/f001",
    });
    assert.equal(attempt, null);
  }, { seedFn: seedCampaign });
});

test("fixture attempts endpoint returns campaign-aware groups and raw attempts", () => {
  withStore(() => {
    const response = callHandler(fixtureHandler, {
      benchmark: "commit_messages",
      fixture: ["commit_messages/f001", "attempts"],
      campaign: "cmp-test",
    });
    assert.equal(response.statusCode, 200);
    assert.equal(response.body.campaign_id, "cmp-test");
    assert.ok(Array.isArray(response.body.groups));
    assert.ok(Array.isArray(response.body.attempts));
    assert.equal(response.body.attempts.length, 2);
  }, { seedFn: seedCampaign });
});

test("campaigns endpoint lists campaigns with config hash and status", () => {
  withStore(() => {
    const response = callHandler(campaignsHandler, {});
    assert.equal(response.statusCode, 200);
    assert.ok(Array.isArray(response.body.campaigns));
    const campaign = response.body.campaigns.find((c) => c.campaign_id === "cmp-test");
    assert.ok(campaign);
    assert.equal(campaign.config_hash, "abc");
    assert.equal(campaign.incomplete, false);
  }, { seedFn: seedCampaign });
});

test("model results endpoint resolves campaign and returns metadata", () => {
  withStore(() => {
    const response = callHandler(modelResultsHandler, {
      model: ["openai", "gpt-test:high"],
      campaign: "cmp-test",
    });
    assert.equal(response.statusCode, 200);
    assert.equal(response.body.campaign_id, "cmp-test");
    assert.ok(response.body.campaign_metadata);
  }, { seedFn: seedCampaign });
});
