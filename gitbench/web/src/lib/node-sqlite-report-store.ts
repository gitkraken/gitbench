import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import type {
  BenchmarkDetail,
  CampaignFilters,
  CampaignListItem,
  FixtureAttempts,
  FixtureAttemptGroup,
  FixtureDetail,
  ModelResultsFilters,
  RawAttempt,
  ReportQueryOptions,
  ReportStore,
} from "./report-store.ts";
import type {
  BaseModelGroup,
  CellData,
  FixtureInfo,
  FixtureResult,
  GitBenchData,
  ModelInfo,
} from "./types.ts";

let cachedDb: DatabaseSync | null = null;
let cachedStore: NodeSqliteReportStore | null = null;

export function clearReportStoreCache(): void {
  cachedDb = null;
  cachedStore = null;
}

export function getReportStore(): ReportStore {
  if (!cachedStore) {
    const dbPath =
      process.env.GITBENCH_REPORT_DB ??
      path.resolve(process.cwd(), "data", "gitbench.db");
    cachedDb = cachedDb ?? new DatabaseSync(dbPath, { readOnly: true });
    cachedStore = new NodeSqliteReportStore(cachedDb);
  }
  return cachedStore;
}

/** Build a key that combines model name and output mode for lookups. */
function modelModeKey(modelName: string, outputMode: string): string {
  return outputMode === "text" ? modelName : `${modelName}__${outputMode}`;
}

export class NodeSqliteReportStore implements ReportStore {
  private readonly db: DatabaseSync;

  constructor(db: DatabaseSync) {
    this.db = db;
  }

  getSummary(options: ReportQueryOptions = {}): GitBenchData {
    if (options.campaign_id) {
      const campaignSummary = this.getCampaignSummary(options.campaign_id);
      if (campaignSummary) return campaignSummary;
    }

    const models = this.getModels();
    const benchmarks = this.db
      .prepare("SELECT name FROM benchmarks ORDER BY name")
      .all()
      .map((row) => String((row as { name: string }).name));

    const model_summaries = Object.fromEntries(
      this.db
        .prepare(
          `
          SELECT model_name, output_mode, total_runs, total_fixtures, total_passed, pass_at_k,
                 total_cost_usd, avg_cost_usd
          FROM model_summaries
          `
        )
        .all()
        .map((row) => {
          const r = row as Record<string, number | string | null>;
          const key = modelModeKey(String(r.model_name), String(r.output_mode));
          return [
            key,
            {
              total_runs: Number(r.total_runs),
              total_fixtures: Number(r.total_fixtures),
              total_passed: Number(r.total_passed),
              pass_at_k: Number(r.pass_at_k),
              total_cost_usd: nullableNumber(r.total_cost_usd),
              avg_cost_usd: nullableNumber(r.avg_cost_usd),
            },
          ];
        })
    );

    const model_runtimes = Object.fromEntries(
      this.db
        .prepare(
          `
          SELECT model_name, output_mode, total_ms, avg_ms, min_ms, max_ms, fixture_count
          FROM model_runtimes
          `
        )
        .all()
        .map((row) => {
          const r = row as Record<string, number | string>;
          const key = modelModeKey(String(r.model_name), String(r.output_mode));
          return [
            key,
            {
              total_ms: Number(r.total_ms),
              avg_ms: Number(r.avg_ms),
              min_ms: Number(r.min_ms),
              max_ms: Number(r.max_ms),
              fixture_count: Number(r.fixture_count),
            },
          ];
        })
    );

    const matrix: GitBenchData["matrix"] = {};
    for (const row of this.db
      .prepare(
        `
        SELECT model_name, output_mode, benchmark_name, pass_at_k, total, passed, avg_similarity
        FROM benchmark_summaries
        `
      )
      .all() as Record<string, number | string>[]) {
      const key = modelModeKey(String(row.model_name), String(row.output_mode));
      const benchmark = String(row.benchmark_name);
      matrix[key] = matrix[key] ?? {};
      matrix[key][benchmark] = cellFromRow(row);
    }

    const model_token_summaries = Object.fromEntries(
      this.db
        .prepare(
          `
          SELECT model_name, output_mode,
                 COALESCE(SUM(input_tokens), 0) AS input_tokens,
                 COALESCE(SUM(output_tokens), 0) AS output_tokens,
                 COALESCE(SUM(total_tokens), 0) AS total_tokens,
                 CASE
                   WHEN COUNT(reasoning_tokens) = 0 THEN NULL
                   ELSE SUM(reasoning_tokens)
                 END AS reasoning_tokens
          FROM fixture_results
          GROUP BY model_name, output_mode
          `
        )
        .all()
        .map((row) => {
          const r = row as Record<string, number | string>;
          const key = modelModeKey(String(r.model_name), String(r.output_mode));
          return [
            key,
            {
              input_tokens: Number(r.input_tokens),
              output_tokens: Number(r.output_tokens),
              total_tokens: Number(r.total_tokens),
              reasoning_tokens:
                r.reasoning_tokens == null ? null : Number(r.reasoning_tokens),
            },
          ];
        })
    );

    return {
      models,
      benchmarks,
      model_summaries,
      model_runtimes,
      model_token_summaries,
      matrix,
      fixtures: {},
      fixture_index: {},
      runs_meta: this.getHistory(),
      base_model_groups: this.getBaseModelGroups(),
    };
  }

  getModels(): ModelInfo[] {
    return this.db
      .prepare(
        `
          SELECT name, provider, base_model AS baseModel, reasoning_level AS reasoningLevel, output_mode
          FROM models
          ORDER BY name, output_mode
          `
      )
      .all()
      .map((row) => {
        const r = row as Record<string, unknown>;
        return {
          name: String(r.name),
          provider: String(r.provider),
          baseModel: String(r.baseModel),
          reasoningLevel:
            r.reasoningLevel === null || r.reasoningLevel === undefined
              ? null
              : String(r.reasoningLevel),
          output_mode: String(r.output_mode),
        };
      });
  }

  getModelResults(
    model: string,
    filters: ModelResultsFilters = {}
  ): { model: string; results: Record<string, FixtureResult[]> } | null {
    // Find the actual model_name + output_mode for the given composite key
    const [modelName, outputMode] = this.resolveModelKey(model);
    const requestedOutputMode = filters.output_mode ?? outputMode ?? "text";
    if (filters.campaign_id) {
      if (!modelName) return null;
      const campaignRows = this.db
        .prepare(
          `
          SELECT ra.*, NULL AS duration_ms, NULL AS purpose, NULL AS difficulty,
                 '[]' AS tags_json, NULL AS parsed_payload,
                 NULL AS raw_structured_output, NULL AS structured_error
          FROM raw_attempts ra
          WHERE ra.campaign_id = ? AND ra.model_name = ?
            AND ra.output_mode = ?
            ${filters.benchmark ? "AND ra.benchmark_name = ?" : ""}
          ORDER BY ra.benchmark_name, ra.fixture_id, ra.trial_index
          `
        )
        .all(
          ...[
            filters.campaign_id,
            modelName,
            requestedOutputMode,
            ...(filters.benchmark ? [filters.benchmark] : []),
          ]
        ) as Record<string, unknown>[];
      if (campaignRows.length === 0) return null;
      return {
        model: modelModeKey(modelName, requestedOutputMode),
        results: groupResultsByBenchmark(campaignRows, false),
      };
    }
    if (!modelName) return null;
    if (!this.modelExists(modelName, requestedOutputMode)) return null;

    const clauses = ["fr.model_name = ?", "fr.output_mode = ?"];
    const params: (string | number)[] = [modelName, requestedOutputMode];
    if (filters.benchmark) {
      clauses.push("fr.benchmark_name = ?");
      params.push(filters.benchmark);
    }
    if (filters.difficulty) {
      clauses.push("fr.difficulty = ?");
      params.push(filters.difficulty);
    }
    if (filters.tag) {
      clauses.push(
        "EXISTS (SELECT 1 FROM fixture_tags ft WHERE ft.benchmark_name = fr.benchmark_name AND ft.fixture_id = fr.fixture_id AND ft.tag = ?)"
      );
      params.push(filters.tag);
    }

    const rows = this.db
      .prepare(
        `
        SELECT fr.*
        FROM fixture_results fr
        WHERE ${clauses.join(" AND ")}
        ORDER BY fr.benchmark_name, fr.fixture_id
        `
      )
      .all(...params) as Record<string, unknown>[];

    return {
      model: modelModeKey(modelName, requestedOutputMode),
      results: groupResultsByBenchmark(rows, false),
    };
  }

  getBenchmark(
    benchmark: string,
    options: ReportQueryOptions = {}
  ): BenchmarkDetail | null {
    if (options.campaign_id) {
      const campaignBenchmark = this.getCampaignBenchmark(
        benchmark,
        options.campaign_id
      );
      if (campaignBenchmark) return campaignBenchmark;
    }

    if (!this.benchmarkExists(benchmark)) return null;
    const leaderboard = (
      this.db
        .prepare(
          `
          SELECT model_name, output_mode, pass_at_k, total, passed, avg_similarity
          FROM benchmark_summaries
          WHERE benchmark_name = ?
          ORDER BY pass_at_k DESC, avg_similarity DESC, model_name, output_mode
          `
        )
        .all(benchmark) as Record<string, number | string>[]
    ).map((row) => ({
      model: modelModeKey(String(row.model_name), String(row.output_mode)),
      ...cellFromRow(row),
    }));

    const tag_counts = Object.fromEntries(
      (
        this.db
          .prepare(
            `
            SELECT tag, COUNT(*) AS count
            FROM fixture_tags
            WHERE benchmark_name = ?
            GROUP BY tag
            ORDER BY tag
            `
          )
          .all(benchmark) as Record<string, number | string>[]
      ).map((row) => [String(row.tag), Number(row.count)])
    );

    return {
      benchmark,
      tag_counts,
      leaderboard,
      fixtures: this.getFixtureIndex(benchmark),
      results: this.getCompactFixtureResults(benchmark),
    };
  }

  getFixture(
    benchmark: string,
    fixtureId: string,
    options: ReportQueryOptions = {}
  ): FixtureDetail | null {
    if (options.campaign_id) {
      const campaignFixture = this.getCampaignFixture(
        benchmark,
        fixtureId,
        options.campaign_id
      );
      if (campaignFixture) return campaignFixture;
    }

    const fixture = this.getFixtureInfo(benchmark, fixtureId);
    if (!fixture) return null;
    const outputs = (
      this.db
        .prepare(
          `
          SELECT fr.*
          FROM fixture_results fr
          WHERE fr.benchmark_name = ? AND fr.fixture_id = ?
          ORDER BY fr.model_name, fr.output_mode
          `
        )
        .all(benchmark, fixtureId) as Record<string, unknown>[]
    ).map((row) => ({
      model: modelModeKey(String(row.model_name), String(row.output_mode)),
      ...fixtureResultFromRow(row, true, { allowMissingSafetyState: true }),
    }));
    return { fixture, outputs };
  }

  private getCampaignSummary(campaignId: string): GitBenchData | null {
    if (!this.getCampaign(campaignId)) return null;

    const models = this.getCampaignModels(campaignId);
    const modelKeys = new Set(
      models.map((model) =>
        modelModeKey(model.name, model.output_mode ?? "text")
      )
    );

    return {
      models,
      benchmarks: this.getCampaignBenchmarks(campaignId),
      model_summaries: this.getCampaignModelSummaries(campaignId),
      model_runtimes: this.getCampaignModelRuntimes(campaignId),
      model_token_summaries: this.getCampaignModelTokenSummaries(campaignId),
      matrix: this.getCampaignMatrix(campaignId, modelKeys),
      fixtures: {},
      fixture_index: {},
      runs_meta: this.getHistory(),
      base_model_groups: this.getBaseModelGroupsForModelKeys(modelKeys),
    };
  }

  private getCampaignModels(campaignId: string): ModelInfo[] {
    const rows = this.db
      .prepare(
        `
        SELECT DISTINCT m.name, m.provider, m.base_model AS baseModel,
               m.reasoning_level AS reasoningLevel, m.output_mode
        FROM campaign_model_summaries cms
        JOIN models m
          ON m.name = cms.model_name
         AND m.output_mode = cms.output_mode
        WHERE cms.campaign_id = ?
        ORDER BY m.name, m.output_mode
        `
      )
      .all(campaignId) as Record<string, unknown>[];

    if (rows.length > 0) return rows.map(modelInfoFromRow);

    const campaignRow = this.getCampaignRow(campaignId);
    if (!campaignRow) return [];
    const modelIds = new Set(parseJsonArray(campaignRow.model_ids_json));
    const outputModes = new Set(parseJsonArray(campaignRow.output_modes_json));
    return this.getModels().filter(
      (model) =>
        modelIds.has(model.name) &&
        (outputModes.size === 0 || outputModes.has(model.output_mode ?? "text"))
    );
  }

  private getCampaignBenchmarks(campaignId: string): string[] {
    const rows = this.db
      .prepare(
        `
        SELECT DISTINCT benchmark_name
        FROM campaign_benchmark_summaries
        WHERE campaign_id = ?
        ORDER BY benchmark_name
        `
      )
      .all(campaignId) as Record<string, unknown>[];

    if (rows.length > 0) return rows.map((row) => String(row.benchmark_name));

    const campaignRow = this.getCampaignRow(campaignId);
    return campaignRow
      ? parseJsonArray(campaignRow.benchmark_ids_json).sort()
      : [];
  }

  private getCampaignModelSummaries(
    campaignId: string
  ): GitBenchData["model_summaries"] {
    const rows = this.db
      .prepare(
        `
        SELECT model_name, output_mode, completed_trials, valid_attempts,
               passing_attempts, mean_success_rate, resource_summary_json
        FROM campaign_model_summaries
        WHERE campaign_id = ?
        `
      )
      .all(campaignId) as Record<string, unknown>[];

    if (rows.length === 0) {
      const attemptRows = this.db
        .prepare(
          `
          SELECT model_name, output_mode,
                 COUNT(DISTINCT trial_index) AS total_runs,
                 COUNT(DISTINCT benchmark_name || char(31) || fixture_id) AS total_fixtures,
                 COUNT(DISTINCT CASE
                   WHEN passed = 1 THEN benchmark_name || char(31) || fixture_id
                 END) AS total_passed,
                 SUM(CASE WHEN status IN ('valid_pass', 'valid_fail') THEN 1 ELSE 0 END) AS valid_attempts,
                 SUM(CASE WHEN status = 'valid_pass' THEN 1 ELSE 0 END) AS passing_attempts,
                 SUM(cost_usd) AS total_cost_usd,
                 AVG(cost_usd) AS avg_cost_usd
          FROM raw_attempts
          WHERE campaign_id = ?
          GROUP BY model_name, output_mode
          `
        )
        .all(campaignId) as Record<string, unknown>[];

      return Object.fromEntries(
        attemptRows.map((row) => {
          const validAttempts = Number(row.valid_attempts ?? 0);
          const passingAttempts = Number(row.passing_attempts ?? 0);
          return [
            modelModeKey(String(row.model_name), String(row.output_mode)),
            {
              total_runs: Number(row.total_runs ?? 0),
              total_fixtures: Number(row.total_fixtures ?? 0),
              total_passed: Number(row.total_passed ?? 0),
              pass_at_k:
                validAttempts > 0 ? passingAttempts / validAttempts : 0,
              total_cost_usd: nullableNumber(row.total_cost_usd),
              avg_cost_usd: nullableNumber(row.avg_cost_usd),
              total_valid_attempts: validAttempts,
              total_passing_attempts: passingAttempts,
            },
          ];
        })
      ) as GitBenchData["model_summaries"];
    }

    const aggregateRows = this.db
      .prepare(
        `
        SELECT model_name, output_mode,
               COUNT(DISTINCT benchmark_name || char(31) || fixture_id) AS total_fixtures,
               SUM(CASE WHEN reliability_classification = 'stable_pass' THEN 1 ELSE 0 END) AS stable_pass_fixtures
        FROM fixture_aggregates
        WHERE campaign_id = ? AND model_name <> ''
        GROUP BY model_name, output_mode
        `
      )
      .all(campaignId) as Record<string, unknown>[];
    const fixtureStats = new Map(
      aggregateRows.map((row) => [
        modelModeKey(String(row.model_name), String(row.output_mode)),
        {
          total_fixtures: Number(row.total_fixtures ?? 0),
          stable_pass_fixtures: Number(row.stable_pass_fixtures ?? 0),
        },
      ])
    );
    const rawFixtureRows = this.db
      .prepare(
        `
        SELECT model_name, output_mode,
               COUNT(DISTINCT benchmark_name || char(31) || fixture_id) AS total_fixtures,
               COUNT(DISTINCT CASE
                 WHEN passed = 1 THEN benchmark_name || char(31) || fixture_id
               END) AS stable_pass_fixtures
        FROM raw_attempts
        WHERE campaign_id = ?
        GROUP BY model_name, output_mode
        `
      )
      .all(campaignId) as Record<string, unknown>[];
    const rawFixtureStats = new Map(
      rawFixtureRows.map((row) => [
        modelModeKey(String(row.model_name), String(row.output_mode)),
        {
          total_fixtures: Number(row.total_fixtures ?? 0),
          stable_pass_fixtures: Number(row.stable_pass_fixtures ?? 0),
        },
      ])
    );

    return Object.fromEntries(
      rows.map((row) => {
        const key = modelModeKey(
          String(row.model_name),
          String(row.output_mode)
        );
        const resource = parseJsonObject(row.resource_summary_json);
        const stats = fixtureStats.get(key) ?? rawFixtureStats.get(key);
        return [
          key,
          {
            total_runs: Number(row.completed_trials ?? 0),
            total_fixtures: stats?.total_fixtures ?? 0,
            total_passed: stats?.stable_pass_fixtures ?? 0,
            pass_at_k: Number(row.mean_success_rate ?? 0),
            total_cost_usd: nullableNumber(resource.total_cost_usd),
            avg_cost_usd: nullableNumber(
              resource.mean_cost_per_complete_trial_usd
            ),
            total_valid_attempts: Number(row.valid_attempts ?? 0),
            total_passing_attempts: Number(row.passing_attempts ?? 0),
          },
        ];
      })
    ) as GitBenchData["model_summaries"];
  }

  private getCampaignModelRuntimes(
    campaignId: string
  ): GitBenchData["model_runtimes"] {
    const rows = this.db
      .prepare(
        `
        SELECT model_name, output_mode,
               COALESCE(SUM(api_duration_ms), 0) AS total_ms,
               COALESCE(AVG(api_duration_ms), 0) AS avg_ms,
               COALESCE(MIN(api_duration_ms), 0) AS min_ms,
               COALESCE(MAX(api_duration_ms), 0) AS max_ms,
               COUNT(api_duration_ms) AS fixture_count
        FROM raw_attempts
        WHERE campaign_id = ?
        GROUP BY model_name, output_mode
        `
      )
      .all(campaignId) as Record<string, unknown>[];

    return Object.fromEntries(
      rows.map((row) => [
        modelModeKey(String(row.model_name), String(row.output_mode)),
        {
          total_ms: Number(row.total_ms),
          avg_ms: Number(row.avg_ms),
          min_ms: Number(row.min_ms),
          max_ms: Number(row.max_ms),
          fixture_count: Number(row.fixture_count),
        },
      ])
    ) as GitBenchData["model_runtimes"];
  }

  private getCampaignModelTokenSummaries(
    campaignId: string
  ): GitBenchData["model_token_summaries"] {
    const rows = this.db
      .prepare(
        `
        SELECT model_name, output_mode,
               COALESCE(SUM(input_tokens), 0) AS input_tokens,
               COALESCE(SUM(output_tokens), 0) AS output_tokens,
               COALESCE(SUM(total_tokens), 0) AS total_tokens,
               CASE
                 WHEN COUNT(reasoning_tokens) = 0 THEN NULL
                 ELSE SUM(reasoning_tokens)
               END AS reasoning_tokens
        FROM raw_attempts
        WHERE campaign_id = ?
        GROUP BY model_name, output_mode
        `
      )
      .all(campaignId) as Record<string, unknown>[];

    return Object.fromEntries(
      rows.map((row) => [
        modelModeKey(String(row.model_name), String(row.output_mode)),
        {
          input_tokens: Number(row.input_tokens),
          output_tokens: Number(row.output_tokens),
          total_tokens: Number(row.total_tokens),
          reasoning_tokens: nullableNumber(row.reasoning_tokens),
        },
      ])
    ) as GitBenchData["model_token_summaries"];
  }

  private getCampaignMatrix(
    campaignId: string,
    modelKeys: Set<string>
  ): GitBenchData["matrix"] {
    const rows = this.db
      .prepare(
        `
        SELECT model_name, output_mode, benchmark_name,
               SUM(valid_attempts) AS total,
               SUM(passing_attempts) AS passed,
               CASE
                 WHEN SUM(valid_attempts) > 0
                   THEN CAST(SUM(passing_attempts) AS REAL) / SUM(valid_attempts)
                 ELSE 0
               END AS pass_at_k
        FROM fixture_aggregates
        WHERE campaign_id = ? AND model_name <> ''
        GROUP BY model_name, output_mode, benchmark_name
        `
      )
      .all(campaignId) as Record<string, unknown>[];

    const matrix: GitBenchData["matrix"] = {};
    for (const row of rows) {
      const key = modelModeKey(String(row.model_name), String(row.output_mode));
      if (modelKeys.size > 0 && !modelKeys.has(key)) continue;
      const benchmark = String(row.benchmark_name);
      matrix[key] = matrix[key] ?? {};
      matrix[key][benchmark] = {
        pass_at_k: Number(row.pass_at_k),
        total: Number(row.total),
        passed: Number(row.passed),
        avg_similarity: 0,
      };
    }

    if (Object.keys(matrix).length === 0) {
      for (const row of this.db
        .prepare(
          `
          SELECT model_name, output_mode, benchmark_name,
                 SUM(CASE WHEN status IN ('valid_pass', 'valid_fail') THEN 1 ELSE 0 END) AS total,
                 SUM(CASE WHEN status = 'valid_pass' THEN 1 ELSE 0 END) AS passed
          FROM raw_attempts
          WHERE campaign_id = ?
          GROUP BY model_name, output_mode, benchmark_name
          `
        )
        .all(campaignId) as Record<string, unknown>[]) {
        const key = modelModeKey(
          String(row.model_name),
          String(row.output_mode)
        );
        if (modelKeys.size > 0 && !modelKeys.has(key)) continue;
        const total = Number(row.total ?? 0);
        const passed = Number(row.passed ?? 0);
        const benchmark = String(row.benchmark_name);
        matrix[key] = matrix[key] ?? {};
        matrix[key][benchmark] = {
          pass_at_k: total > 0 ? passed / total : 0,
          total,
          passed,
          avg_similarity: 0,
        };
      }
    }

    if (Object.keys(matrix).length === 0 && modelKeys.size === 1) {
      const onlyModel = Array.from(modelKeys)[0];
      matrix[onlyModel] = {};
      for (const row of this.db
        .prepare(
          `
          SELECT benchmark_name, valid_attempts AS total,
                 passing_attempts AS passed, mean_success_rate AS pass_at_k
          FROM campaign_benchmark_summaries
          WHERE campaign_id = ?
          `
        )
        .all(campaignId) as Record<string, unknown>[]) {
        matrix[onlyModel][String(row.benchmark_name)] = {
          pass_at_k: Number(row.pass_at_k ?? 0),
          total: Number(row.total ?? 0),
          passed: Number(row.passed ?? 0),
          avg_similarity: 0,
        };
      }
    }

    return matrix;
  }

  private getCampaignBenchmark(
    benchmark: string,
    campaignId: string
  ): BenchmarkDetail | null {
    if (!this.benchmarkExists(benchmark)) return null;

    let leaderboard = (
      this.db
        .prepare(
          `
          SELECT model_name, output_mode,
                 SUM(valid_attempts) AS total,
                 SUM(passing_attempts) AS passed,
                 CASE
                   WHEN SUM(valid_attempts) > 0
                     THEN CAST(SUM(passing_attempts) AS REAL) / SUM(valid_attempts)
                   ELSE 0
                 END AS pass_at_k
          FROM fixture_aggregates
          WHERE campaign_id = ? AND benchmark_name = ? AND model_name <> ''
          GROUP BY model_name, output_mode
          ORDER BY pass_at_k DESC, model_name, output_mode
          `
        )
        .all(campaignId, benchmark) as Record<string, unknown>[]
    ).map((row) => ({
      model: modelModeKey(String(row.model_name), String(row.output_mode)),
      pass_at_k: Number(row.pass_at_k),
      total: Number(row.total),
      passed: Number(row.passed),
      avg_similarity: 0,
    }));

    if (leaderboard.length === 0) {
      leaderboard = (
        this.db
          .prepare(
            `
            SELECT model_name, output_mode,
                   SUM(CASE WHEN status IN ('valid_pass', 'valid_fail') THEN 1 ELSE 0 END) AS total,
                   SUM(CASE WHEN status = 'valid_pass' THEN 1 ELSE 0 END) AS passed
            FROM raw_attempts
            WHERE campaign_id = ? AND benchmark_name = ?
            GROUP BY model_name, output_mode
            `
          )
          .all(campaignId, benchmark) as Record<string, unknown>[]
      )
        .map((row) => {
          const total = Number(row.total ?? 0);
          const passed = Number(row.passed ?? 0);
          return {
            model: modelModeKey(
              String(row.model_name),
              String(row.output_mode)
            ),
            pass_at_k: total > 0 ? passed / total : 0,
            total,
            passed,
            avg_similarity: 0,
          };
        })
        .sort(
          (a, b) => b.pass_at_k - a.pass_at_k || a.model.localeCompare(b.model)
        );
    }

    return {
      benchmark,
      tag_counts: this.getTagCounts(benchmark),
      leaderboard,
      fixtures: this.getFixtureIndex(benchmark),
      results: this.getCampaignFixtureResults(campaignId, benchmark),
    };
  }

  private getCampaignFixture(
    benchmark: string,
    fixtureId: string,
    campaignId: string
  ): FixtureDetail | null {
    const fixture = this.getFixtureInfo(benchmark, fixtureId);
    if (!fixture) return null;

    const includeOutput = this.isCampaignPublicationAllowed(campaignId);
    const outputs = (
      this.db
        .prepare(
          `
          SELECT ra.*, NULL AS duration_ms, NULL AS purpose, NULL AS difficulty,
                 '[]' AS tags_json, NULL AS parsed_payload,
                 NULL AS raw_structured_output, NULL AS structured_error
          FROM raw_attempts ra
          WHERE ra.campaign_id = ? AND ra.benchmark_name = ? AND ra.fixture_id = ?
          ORDER BY ra.model_name, ra.output_mode, ra.trial_index
          `
        )
        .all(campaignId, benchmark, fixtureId) as Record<string, unknown>[]
    ).map((row) => ({
      model: modelModeKey(String(row.model_name), String(row.output_mode)),
      ...fixtureResultFromRow(row, includeOutput),
    }));

    return { fixture, outputs };
  }

  private getCampaignFixtureResults(
    campaignId: string,
    benchmark: string
  ): Record<string, Record<string, FixtureResult[]>> {
    const rows = this.db
      .prepare(
        `
        SELECT ra.*, NULL AS duration_ms, NULL AS purpose, NULL AS difficulty,
               '[]' AS tags_json, NULL AS parsed_payload,
               NULL AS raw_structured_output, NULL AS structured_error
        FROM raw_attempts ra
        WHERE ra.campaign_id = ? AND ra.benchmark_name = ?
        ORDER BY ra.model_name, ra.output_mode, ra.fixture_id, ra.trial_index
        `
      )
      .all(campaignId, benchmark) as Record<string, unknown>[];

    const grouped: Record<string, Record<string, FixtureResult[]>> = {};
    for (const row of rows) {
      const model = modelModeKey(
        String(row.model_name),
        String(row.output_mode)
      );
      const bench = String(row.benchmark_name);
      grouped[model] = grouped[model] ?? {};
      grouped[model][bench] = grouped[model][bench] ?? [];
      grouped[model][bench].push(fixtureResultFromRow(row, false));
    }
    return grouped;
  }

  getHistory(): GitBenchData["runs_meta"] {
    return this.db
      .prepare(
        `
          SELECT timestamp, model_name AS model, output_mode, profile, git_sha,
                 benchmark_suite_version, reasoning_level
          FROM runs
          ORDER BY benchmark_suite_version, timestamp
          `
      )
      .all()
      .map((row) => {
        const r = row as Record<string, unknown>;
        return {
          timestamp: String(r.timestamp),
          model: String(r.model),
          profile: String(r.profile),
          git_sha: String(r.git_sha),
          benchmark_suite_version: String(r.benchmark_suite_version),
          reasoning_level: String(r.reasoning_level ?? ""),
          output_mode: String(r.output_mode),
        };
      });
  }

  getCampaigns(filters: CampaignFilters = {}): CampaignListItem[] {
    const clauses: string[] = [];
    const params: (string | number)[] = [];
    if (filters.benchmark) {
      clauses.push(
        "EXISTS (SELECT 1 FROM json_each(c.benchmark_ids_json) WHERE value = ?)"
      );
      params.push(filters.benchmark);
    }
    if (filters.model) {
      clauses.push(
        "EXISTS (SELECT 1 FROM json_each(c.model_ids_json) WHERE value = ?)"
      );
      params.push(filters.model);
    }
    if (filters.output_mode) {
      clauses.push(
        "EXISTS (SELECT 1 FROM json_each(c.output_modes_json) WHERE value = ?)"
      );
      params.push(filters.output_mode);
    }
    const where = clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
    const rows = this.db
      .prepare(
        `
        SELECT c.campaign_id, c.created_at, c.config_hash, c.state, c.publication_state,
               c.legacy, c.planned_trial_count,
               COALESCE(SUM(t.completed_trials), 0) AS completed_trials,
               c.valid_attempts, c.passing_attempts, c.excluded_attempts,
               COALESCE(
                 CASE
                   WHEN c.valid_attempts > 0 THEN CAST(c.passing_attempts AS REAL) / c.valid_attempts
                   ELSE NULL
                 END,
                 NULL
               ) AS mean_success_rate,
               ps.pending_count, ps.blocked_count
        FROM campaigns c
        LEFT JOIN (
          SELECT campaign_id, COUNT(*) AS completed_trials
          FROM trials
          WHERE complete = 1
          GROUP BY campaign_id
        ) t ON t.campaign_id = c.campaign_id
        LEFT JOIN publication_states ps ON ps.campaign_id = c.campaign_id
        ${where}
        GROUP BY c.campaign_id
        ORDER BY c.created_at DESC
        `
      )
      .all(...params) as Record<string, unknown>[];

    return rows.map((row) => {
      const publicationState = String(row.publication_state);
      const state = String(row.state);
      const legacy = Boolean(row.legacy);
      const meanSuccessRate = nullableNumber(row.mean_success_rate);
      const pendingCount = Number(row.pending_count ?? 0);
      const blockedCount = Number(row.blocked_count ?? 0);
      return {
        campaign_id: String(row.campaign_id),
        created_at: String(row.created_at),
        config_hash: String(row.config_hash ?? ""),
        state,
        publication_state: publicationState,
        legacy,
        planned_trials: Number(row.planned_trial_count),
        completed_trials: Number(row.completed_trials),
        valid_attempts: Number(row.valid_attempts),
        passing_attempts: Number(row.passing_attempts),
        excluded_attempts: Number(row.excluded_attempts),
        mean_success_rate: meanSuccessRate,
        compatible: this.checkCampaignCompatibility(
          String(row.campaign_id),
          filters
        ),
        incomplete: state !== "complete",
        publishable:
          state === "complete" &&
          publicationState === "published" &&
          pendingCount === 0 &&
          blockedCount === 0 &&
          !legacy,
      };
    });
  }

  getDefaultCampaign(filters: CampaignFilters = {}): CampaignListItem | null {
    const candidates = this.getCampaigns(filters);
    // Prefer the latest reportable campaign, then fall back by completion state.
    const ranked = candidates.sort((a, b) => {
      const score = (c: CampaignListItem) =>
        (c.publishable ? 8 : 0) +
        (c.state === "complete" ? 4 : 0) +
        (c.publication_state === "published" ? 2 : 0) +
        (c.legacy ? 0 : 1);
      return (
        score(b) - score(a) ||
        Date.parse(b.created_at) - Date.parse(a.created_at)
      );
    });
    return ranked[0] ?? null;
  }

  checkCampaignCompatibility(
    campaignId: string,
    filters: CampaignFilters = {}
  ): boolean {
    const row = this.db
      .prepare("SELECT * FROM campaigns WHERE campaign_id = ?")
      .get(campaignId) as Record<string, unknown> | undefined;
    if (!row) return false;
    const benchmarkIds = parseJsonArray(String(row.benchmark_ids_json ?? "[]"));
    const modelIds = parseJsonArray(String(row.model_ids_json ?? "[]"));
    const outputModes = parseJsonArray(String(row.output_modes_json ?? "[]"));
    if (filters.benchmark && !benchmarkIds.includes(filters.benchmark)) {
      return false;
    }
    if (filters.model && !modelIds.includes(filters.model)) {
      return false;
    }
    if (filters.output_mode && !outputModes.includes(filters.output_mode)) {
      return false;
    }
    return true;
  }

  getCampaignAggregate(campaignId: string, benchmark: string): CellData | null {
    const row = this.db
      .prepare(
        `
        SELECT mean_success_rate AS pass_at_k, valid_attempts AS total,
               passing_attempts AS passed
        FROM campaign_benchmark_summaries
        WHERE campaign_id = ? AND benchmark_name = ?
        `
      )
      .get(campaignId, benchmark) as Record<string, unknown> | undefined;
    if (!row) return null;
    return {
      pass_at_k: Number(row.pass_at_k ?? 0),
      total: Number(row.total ?? 0),
      passed: Number(row.passed ?? 0),
      avg_similarity: 0,
    };
  }

  getCampaign(campaignId: string): CampaignListItem | null {
    return (
      this.getCampaigns().find((c) => c.campaign_id === campaignId) ?? null
    );
  }

  isCampaignPublicationAllowed(campaignId: string): boolean {
    const row = this.db
      .prepare(
        `
        SELECT c.state, c.publication_state, c.legacy,
               COALESCE(ps.pending_count, 0) AS pending_count,
               COALESCE(ps.blocked_count, 0) AS blocked_count
        FROM campaigns c
        LEFT JOIN publication_states ps ON ps.campaign_id = c.campaign_id
        WHERE c.campaign_id = ?
        `
      )
      .get(campaignId) as Record<string, unknown> | undefined;
    if (!row) return false;
    return (
      String(row.state) === "complete" &&
      String(row.publication_state) === "published" &&
      Number(row.pending_count) === 0 &&
      Number(row.blocked_count) === 0 &&
      !Boolean(row.legacy)
    );
  }

  getRawAttempts(
    campaignId: string,
    options: {
      limit?: number;
      offset?: number;
      fixture_id?: string;
      includeOutput?: boolean;
    } = {}
  ): RawAttempt[] {
    const clauses = ["campaign_id = ?"];
    const params: (string | number)[] = [campaignId];
    if (options.fixture_id) {
      clauses.push("fixture_id = ?");
      params.push(options.fixture_id);
    }
    const limit = options.limit ?? 100;
    const offset = options.offset ?? 0;
    const includeOutput = options.includeOutput ?? false;
    const rows = this.db
      .prepare(
        `
        SELECT trial_index, model_name, reasoning_level, output_mode,
               benchmark_name, fixture_id, status, passed, similarity, error,
               input_tokens, output_tokens, total_tokens, reasoning_tokens,
               cost_usd, api_duration_ms, safety_state,
               ${includeOutput ? "model_output" : "NULL AS model_output"}
        FROM raw_attempts
        WHERE ${clauses.join(" AND ")}
        ORDER BY trial_index, model_name, fixture_id
        LIMIT ? OFFSET ?
        `
      )
      .all(...params, limit, offset) as Record<string, unknown>[];

    return rows.map((row) => rawAttemptFromRow(row, includeOutput));
  }

  getRawAttemptByIdentity(
    campaignId: string,
    identity: {
      trial_index: number;
      model_name: string;
      reasoning_level?: string | null;
      output_mode: string;
      benchmark_name?: string;
      fixture_id: string;
    },
    options: { includeOutput?: boolean } = {}
  ): RawAttempt | null {
    const includeOutput = options.includeOutput ?? false;
    const clauses = [
      "campaign_id = ?",
      "trial_index = ?",
      "model_name = ?",
      "output_mode = ?",
      "fixture_id = ?",
    ];
    const params: (string | number | null)[] = [
      campaignId,
      identity.trial_index,
      identity.model_name,
      identity.output_mode,
      identity.fixture_id,
    ];
    if (identity.reasoning_level !== undefined) {
      clauses.push("COALESCE(reasoning_level, '') = ?");
      params.push(identity.reasoning_level ?? "");
    }
    if (identity.benchmark_name) {
      clauses.push("benchmark_name = ?");
      params.push(identity.benchmark_name);
    }
    const row = this.db
      .prepare(
        `
        SELECT trial_index, model_name, reasoning_level, output_mode,
               benchmark_name, fixture_id, status, passed, similarity, error,
               input_tokens, output_tokens, total_tokens, reasoning_tokens,
               cost_usd, api_duration_ms, safety_state,
               ${includeOutput ? "model_output" : "NULL AS model_output"}
        FROM raw_attempts
        WHERE ${clauses.join(" AND ")}
        `
      )
      .get(...params) as Record<string, unknown> | undefined;
    return row ? rawAttemptFromRow(row, includeOutput) : null;
  }

  getFixtureAttempts(
    benchmark: string,
    fixtureId: string,
    options: { campaign_id?: string } = {}
  ): FixtureAttempts | null {
    const fixture = this.getFixtureInfo(benchmark, fixtureId);
    if (!fixture) return null;

    let campaignId = options.campaign_id;
    let campaignMetadata: CampaignListItem | null = null;
    if (!campaignId) {
      const defaultCampaign = this.getDefaultCampaign({ benchmark });
      if (defaultCampaign) {
        campaignId = defaultCampaign.campaign_id;
        campaignMetadata = defaultCampaign;
      }
    } else {
      campaignMetadata = this.getCampaign(campaignId) ?? null;
    }

    const attempts: RawAttempt[] = [];
    const groups: FixtureAttemptGroup[] = [];

    if (campaignId) {
      const rows = this.db
        .prepare(
          `
          SELECT trial_index, model_name, reasoning_level, output_mode,
                 benchmark_name, fixture_id, status, passed, similarity, error,
                 input_tokens, output_tokens, total_tokens, reasoning_tokens,
                 cost_usd, api_duration_ms, safety_state, NULL AS model_output
          FROM raw_attempts
          WHERE campaign_id = ? AND benchmark_name = ? AND fixture_id = ?
          ORDER BY model_name, reasoning_level, output_mode, trial_index
          `
        )
        .all(campaignId, benchmark, fixtureId) as Record<string, unknown>[];
      attempts.push(...rows.map((row) => rawAttemptFromRow(row, false)));

      const byModelMode: Record<
        string,
        {
          model_name: string;
          reasoning_level: string | null;
          output_mode: string;
          attempts: RawAttempt[];
        }
      > = {};
      for (const attempt of attempts) {
        const key = `${attempt.model_name}::${attempt.reasoning_level ?? ""}::${
          attempt.output_mode
        }`;
        byModelMode[key] = byModelMode[key] ?? {
          model_name: attempt.model_name,
          reasoning_level: attempt.reasoning_level,
          output_mode: attempt.output_mode,
          attempts: [],
        };
        byModelMode[key].attempts.push(attempt);
      }

      for (const group of Object.values(byModelMode)) {
        const valid = group.attempts.filter(
          (a) => a.status === "valid_pass" || a.status === "valid_fail"
        );
        const passing = valid.filter((a) => a.passed).length;
        const failing = valid.length - passing;
        const excluded = group.attempts.length - valid.length;
        let classification: FixtureAttemptGroup["classification"] = "unknown";
        if (valid.length > 0) {
          if (passing === valid.length) classification = "stable_pass";
          else if (passing === 0) classification = "stable_fail";
          else classification = "flaky";
        }
        const trialIndices = new Set(group.attempts.map((a) => a.trial_index));
        groups.push({
          model_name: group.model_name,
          output_mode: group.output_mode,
          planned_trials: campaignMetadata?.planned_trials ?? 0,
          completed_trials: trialIndices.size,
          valid_attempts: valid.length,
          passing_attempts: passing,
          failing_attempts: failing,
          excluded_attempts: excluded,
          mean_success_rate: valid.length > 0 ? passing / valid.length : null,
          classification,
        });
      }
    }

    return {
      fixture,
      campaign_id: campaignId ?? null,
      campaign_metadata: campaignMetadata,
      groups,
      attempts,
    };
  }

  private getTagCounts(benchmark: string): Record<string, number> {
    return Object.fromEntries(
      (
        this.db
          .prepare(
            `
            SELECT tag, COUNT(*) AS count
            FROM fixture_tags
            WHERE benchmark_name = ?
            GROUP BY tag
            ORDER BY tag
            `
          )
          .all(benchmark) as Record<string, number | string>[]
      ).map((row) => [String(row.tag), Number(row.count)])
    );
  }

  private getCampaignRow(campaignId: string): Record<string, unknown> | null {
    return (
      (this.db
        .prepare("SELECT * FROM campaigns WHERE campaign_id = ?")
        .get(campaignId) as Record<string, unknown> | undefined) ?? null
    );
  }

  private getBaseModelGroups(): BaseModelGroup[] {
    const groups = this.db
      .prepare(
        `
        SELECT id, provider, base_model AS baseModel
        FROM base_model_groups
        ORDER BY provider, base_model
        `
      )
      .all() as ({ id: number } & Omit<BaseModelGroup, "levels">)[];

    return groups.map((group) => ({
      provider: group.provider,
      baseModel: group.baseModel,
      levels: (
        this.db
          .prepare(
            `
            SELECT level, model_name AS modelName, output_mode, pass_at_k, total_cost_usd
            FROM base_model_group_levels
            WHERE group_id = ?
            ORDER BY COALESCE(level, ''), output_mode
            `
          )
          .all(group.id) as Record<string, unknown>[]
      ).map((level) => ({
        level: level.level === null ? null : String(level.level),
        modelName: modelModeKey(
          String(level.modelName),
          String(level.output_mode)
        ),
        pass_at_k: Number(level.pass_at_k),
        total_cost_usd: nullableNumber(level.total_cost_usd),
      })),
    }));
  }

  private getBaseModelGroupsForModelKeys(
    modelKeys: Set<string>
  ): BaseModelGroup[] {
    if (modelKeys.size === 0) return [];
    return this.getBaseModelGroups()
      .map((group) => ({
        ...group,
        levels: group.levels.filter((level) => modelKeys.has(level.modelName)),
      }))
      .filter((group) => group.levels.length > 0);
  }

  /** Resolve a composite model key back to (model_name, output_mode). */
  private resolveModelKey(key: string): [string, string] | [null, null] {
    // Check if the key ends with a known output_mode suffix
    for (const suffix of ["__json_schema"]) {
      if (key.endsWith(suffix)) {
        const modelName = key.slice(0, -suffix.length);
        const outputMode = suffix.slice(2); // remove "__"
        if (this.modelExists(modelName, outputMode)) {
          return [modelName, outputMode];
        }
      }
    }
    // Default: try as text mode
    if (this.modelExists(key, "text")) {
      return [key, "text"];
    }
    return [null, null];
  }

  private getFixtureIndex(benchmark?: string): Record<string, FixtureInfo> {
    const sql = `
      SELECT f.*, GROUP_CONCAT(ft.tag, char(31)) AS tags
      FROM fixtures f
      LEFT JOIN fixture_tags ft
        ON ft.benchmark_name = f.benchmark_name
       AND ft.fixture_id = f.fixture_id
      ${benchmark ? "WHERE f.benchmark_name = ?" : ""}
      GROUP BY f.benchmark_name, f.fixture_id
      ORDER BY f.benchmark_name, f.fixture_id
    `;
    const rows = benchmark
      ? this.db.prepare(sql).all(benchmark)
      : this.db.prepare(sql).all();

    return Object.fromEntries(
      (rows as Record<string, unknown>[]).map((row) => {
        const fixture = fixtureInfoFromRow(row);
        return [`${fixture.benchmark}/${fixture.id}`, fixture];
      })
    );
  }

  private getFixtureInfo(
    benchmark: string,
    fixtureId: string
  ): FixtureInfo | null {
    const row = this.db
      .prepare(
        `
        SELECT f.*, GROUP_CONCAT(ft.tag, char(31)) AS tags
        FROM fixtures f
        LEFT JOIN fixture_tags ft
          ON ft.benchmark_name = f.benchmark_name
         AND ft.fixture_id = f.fixture_id
        WHERE f.benchmark_name = ? AND f.fixture_id = ?
        GROUP BY f.benchmark_name, f.fixture_id
        `
      )
      .get(benchmark, fixtureId) as Record<string, unknown> | undefined;
    return row ? fixtureInfoFromRow(row) : null;
  }

  private getCompactFixtureResults(
    benchmark?: string
  ): Record<string, Record<string, FixtureResult[]>> {
    const sql = `
      SELECT *
      FROM fixture_results
      ${benchmark ? "WHERE benchmark_name = ?" : ""}
      ORDER BY model_name, output_mode, benchmark_name, fixture_id
    `;
    const rows = benchmark
      ? this.db.prepare(sql).all(benchmark)
      : this.db.prepare(sql).all();

    const grouped: Record<string, Record<string, FixtureResult[]>> = {};
    for (const row of rows as Record<string, unknown>[]) {
      const model = modelModeKey(
        String(row.model_name),
        String(row.output_mode)
      );
      const bench = String(row.benchmark_name);
      grouped[model] = grouped[model] ?? {};
      grouped[model][bench] = grouped[model][bench] ?? [];
      grouped[model][bench].push(fixtureResultFromRow(row, false));
    }
    return grouped;
  }

  private modelExists(model: string, outputMode: string = "text"): boolean {
    return Boolean(
      this.db
        .prepare("SELECT 1 FROM models WHERE name = ? AND output_mode = ?")
        .get(model, outputMode)
    );
  }

  private benchmarkExists(benchmark: string): boolean {
    return Boolean(
      this.db.prepare("SELECT 1 FROM benchmarks WHERE name = ?").get(benchmark)
    );
  }
}

function nullableNumber(value: unknown): number | null {
  return value === null || value === undefined ? null : Number(value);
}

function modelInfoFromRow(row: Record<string, unknown>): ModelInfo {
  return {
    name: String(row.name),
    provider: String(row.provider),
    baseModel: String(row.baseModel),
    reasoningLevel:
      row.reasoningLevel === null || row.reasoningLevel === undefined
        ? null
        : String(row.reasoningLevel),
    output_mode: String(row.output_mode),
  };
}

function parseJsonArray(value: unknown): string[] {
  if (typeof value !== "string" || !value) return [];
  const parsed = JSON.parse(value);
  return Array.isArray(parsed) ? parsed : [];
}

function parseJsonObject(value: unknown): Record<string, unknown> {
  if (typeof value !== "string" || !value) return {};
  const parsed = JSON.parse(value);
  return parsed && typeof parsed === "object" && !Array.isArray(parsed)
    ? (parsed as Record<string, unknown>)
    : {};
}

function cellFromRow(row: Record<string, unknown>): CellData {
  return {
    pass_at_k: Number(row.pass_at_k),
    total: Number(row.total),
    passed: Number(row.passed),
    avg_similarity: Number(row.avg_similarity),
  };
}

function fixtureInfoFromRow(row: Record<string, unknown>): FixtureInfo {
  return {
    id: String(row.fixture_id),
    benchmark: String(row.benchmark_name),
    prompt: String(row.prompt ?? ""),
    expected: String(row.expected ?? ""),
    description: String(row.description ?? ""),
    setup: parseJsonArray(row.setup_json),
    purpose: String(row.purpose ?? ""),
    difficulty: String(row.difficulty ?? ""),
    tags: typeof row.tags === "string" ? row.tags.split("\u001f") : [],
  };
}

function rawAttemptFromRow(
  row: Record<string, unknown>,
  includeOutput: boolean
): RawAttempt {
  const safetyState =
    typeof row.safety_state === "string" ? row.safety_state : null;
  const canExposeOutput =
    safetyState === "reviewed" || safetyState === "published";
  return {
    trial_index: Number(row.trial_index),
    model_name: String(row.model_name),
    reasoning_level:
      row.reasoning_level === null || row.reasoning_level === undefined
        ? null
        : String(row.reasoning_level),
    output_mode: String(row.output_mode),
    benchmark_name: String(row.benchmark_name),
    fixture_id: String(row.fixture_id),
    status: String(row.status),
    passed: row.passed === null ? null : Boolean(row.passed),
    similarity: nullableNumber(row.similarity),
    error: row.error === null ? null : String(row.error),
    input_tokens: nullableNumber(row.input_tokens),
    output_tokens: nullableNumber(row.output_tokens),
    total_tokens: nullableNumber(row.total_tokens),
    reasoning_tokens: nullableNumber(row.reasoning_tokens),
    cost_usd: nullableNumber(row.cost_usd),
    api_duration_ms: nullableNumber(row.api_duration_ms),
    model_output:
      includeOutput && canExposeOutput
        ? String(row.model_output ?? "")
        : undefined,
    safety_state: safetyState,
  };
}

function fixtureResultFromRow(
  row: Record<string, unknown>,
  includeModelOutput: boolean,
  options: { allowMissingSafetyState?: boolean } = {}
): FixtureResult {
  const safetyState =
    typeof row.safety_state === "string" ? row.safety_state : null;
  const canExposeOutput =
    safetyState === "reviewed" ||
    safetyState === "published" ||
    (options.allowMissingSafetyState === true && safetyState === null);
  return {
    fixture_id: String(row.fixture_id),
    passed: Boolean(row.passed),
    similarity: Number(row.similarity),
    error:
      row.error === null || row.error === undefined ? null : String(row.error),
    model_output:
      includeModelOutput && canExposeOutput
        ? String(row.model_output ?? "")
        : "",
    reasoning_level:
      row.reasoning_level === null || row.reasoning_level === undefined
        ? null
        : String(row.reasoning_level),
    input_tokens: nullableNumber(row.input_tokens),
    output_tokens: nullableNumber(row.output_tokens),
    total_tokens: nullableNumber(row.total_tokens),
    reasoning_tokens: nullableNumber(row.reasoning_tokens),
    cost_usd: nullableNumber(row.cost_usd),
    duration_ms: nullableNumber(row.duration_ms),
    api_duration_ms: nullableNumber(row.api_duration_ms),
    purpose:
      row.purpose === null || row.purpose === undefined
        ? null
        : String(row.purpose),
    difficulty:
      row.difficulty === null || row.difficulty === undefined
        ? null
        : String(row.difficulty),
    tags: parseJsonArray(row.tags_json),
    output_mode: String(row.output_mode ?? "text"),
    parsed_payload:
      typeof row.parsed_payload === "string" ? row.parsed_payload : null,
    raw_structured_output:
      typeof row.raw_structured_output === "string"
        ? row.raw_structured_output
        : null,
    structured_error:
      typeof row.structured_error === "string" ? row.structured_error : null,
  };
}

function groupResultsByBenchmark(
  rows: Record<string, unknown>[],
  includeModelOutput: boolean
): Record<string, FixtureResult[]> {
  const grouped: Record<string, FixtureResult[]> = {};
  for (const row of rows) {
    const benchmark = String(row.benchmark_name);
    grouped[benchmark] = grouped[benchmark] ?? [];
    grouped[benchmark].push(fixtureResultFromRow(row, includeModelOutput));
  }
  return grouped;
}
