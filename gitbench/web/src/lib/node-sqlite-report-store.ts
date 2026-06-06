import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import type {
  BenchmarkDetail,
  FixtureDetail,
  ModelResultsFilters,
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
  constructor(private readonly db: DatabaseSync) {}

  getSummary(): GitBenchData {
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
          `,
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
        }),
    );

    const model_runtimes = Object.fromEntries(
      this.db
        .prepare(
          `
          SELECT model_name, output_mode, total_ms, avg_ms, min_ms, max_ms, fixture_count
          FROM model_runtimes
          `,
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
        }),
    );

    const matrix: GitBenchData["matrix"] = {};
    for (const row of this.db
      .prepare(
        `
        SELECT model_name, output_mode, benchmark_name, pass_at_k, total, passed, avg_similarity
        FROM benchmark_summaries
        `,
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
                 COALESCE(SUM(total_tokens), 0) AS total_tokens
          FROM fixture_results
          GROUP BY model_name, output_mode
          `,
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
            },
          ];
        }),
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
    return (
      this.db
        .prepare(
          `
          SELECT name, provider, base_model AS baseModel, reasoning_level AS reasoningLevel, output_mode
          FROM models
          ORDER BY name, output_mode
          `,
        )
        .all() as ModelInfo[]
    );
  }

  getModelResults(
    model: string,
    filters: ModelResultsFilters = {},
  ): { model: string; results: Record<string, FixtureResult[]> } | null {
    // Find the actual model_name + output_mode for the given composite key
    const [modelName, outputMode] = this.resolveModelKey(model);
    if (!modelName) return null;
    const requestedOutputMode = filters.output_mode ?? outputMode;
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
        "EXISTS (SELECT 1 FROM fixture_tags ft WHERE ft.benchmark_name = fr.benchmark_name AND ft.fixture_id = fr.fixture_id AND ft.tag = ?)",
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
        `,
      )
      .all(...params) as Record<string, unknown>[];

    return {
      model: modelModeKey(modelName, requestedOutputMode),
      results: groupResultsByBenchmark(rows, false),
    };
  }

  getBenchmark(benchmark: string): BenchmarkDetail | null {
    if (!this.benchmarkExists(benchmark)) return null;
    const leaderboard = (
      this.db
        .prepare(
          `
          SELECT model_name, output_mode, pass_at_k, total, passed, avg_similarity
          FROM benchmark_summaries
          WHERE benchmark_name = ?
          ORDER BY pass_at_k DESC, avg_similarity DESC, model_name, output_mode
          `,
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
            `,
          )
          .all(benchmark) as Record<string, number | string>[]
      ).map((row) => [String(row.tag), Number(row.count)]),
    );

    return {
      benchmark,
      tag_counts,
      leaderboard,
      fixtures: this.getFixtureIndex(benchmark),
      results: this.getCompactFixtureResults(benchmark),
    };
  }

  getFixture(benchmark: string, fixtureId: string): FixtureDetail | null {
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
          `,
        )
        .all(benchmark, fixtureId) as Record<string, unknown>[]
    ).map((row) => ({
      model: modelModeKey(String(row.model_name), String(row.output_mode)),
      ...fixtureResultFromRow(row, true),
    }));
    return { fixture, outputs };
  }

  getHistory(): GitBenchData["runs_meta"] {
    return (
      this.db
        .prepare(
          `
          SELECT timestamp, model_name AS model, output_mode, profile, git_sha,
                 benchmark_suite_version, reasoning_level
          FROM runs
          ORDER BY benchmark_suite_version, timestamp
          `,
        )
        .all() as GitBenchData["runs_meta"]
    );
  }

  private getBaseModelGroups(): BaseModelGroup[] {
    const groups = this.db
      .prepare(
        `
        SELECT id, provider, base_model AS baseModel
        FROM base_model_groups
        ORDER BY provider, base_model
        `,
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
            `,
          )
          .all(group.id) as (BaseModelGroup["levels"][number] & { output_mode: string })[]
      ).map((level) => ({
        level: level.level,
        modelName: modelModeKey(level.modelName, level.output_mode),
        pass_at_k: level.pass_at_k,
        total_cost_usd: level.total_cost_usd,
      })),
    }));
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
      }),
    );
  }

  private getFixtureInfo(
    benchmark: string,
    fixtureId: string,
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
        `,
      )
      .get(benchmark, fixtureId) as Record<string, unknown> | undefined;
    return row ? fixtureInfoFromRow(row) : null;
  }

  private getCompactFixtureResults(
    benchmark?: string,
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
      const model = modelModeKey(String(row.model_name), String(row.output_mode));
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
        .get(model, outputMode),
    );
  }

  private benchmarkExists(benchmark: string): boolean {
    return Boolean(
      this.db.prepare("SELECT 1 FROM benchmarks WHERE name = ?").get(benchmark),
    );
  }
}

function nullableNumber(value: unknown): number | null {
  return value === null || value === undefined ? null : Number(value);
}

function parseJsonArray(value: unknown): string[] {
  if (typeof value !== "string" || !value) return [];
  const parsed = JSON.parse(value);
  return Array.isArray(parsed) ? parsed : [];
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

function fixtureResultFromRow(
  row: Record<string, unknown>,
  includeModelOutput: boolean,
): FixtureResult {
  return {
    fixture_id: String(row.fixture_id),
    passed: Boolean(row.passed),
    similarity: Number(row.similarity),
    error: row.error === null || row.error === undefined ? null : String(row.error),
    model_output: includeModelOutput ? String(row.model_output ?? "") : "",
    reasoning_level:
      row.reasoning_level === null || row.reasoning_level === undefined
        ? null
        : String(row.reasoning_level),
    input_tokens: nullableNumber(row.input_tokens),
    output_tokens: nullableNumber(row.output_tokens),
    total_tokens: nullableNumber(row.total_tokens),
    cost_usd: nullableNumber(row.cost_usd),
    duration_ms: nullableNumber(row.duration_ms),
    api_duration_ms: nullableNumber(row.api_duration_ms),
    purpose: row.purpose === null || row.purpose === undefined ? null : String(row.purpose),
    difficulty:
      row.difficulty === null || row.difficulty === undefined
        ? null
        : String(row.difficulty),
    tags: parseJsonArray(row.tags_json),
    output_mode: String(row.output_mode ?? "text"),
    parsed_payload: typeof row.parsed_payload === "string" ? row.parsed_payload : null,
    raw_structured_output:
      typeof row.raw_structured_output === "string" ? row.raw_structured_output : null,
    structured_error:
      typeof row.structured_error === "string" ? row.structured_error : null,
  };
}

function groupResultsByBenchmark(
  rows: Record<string, unknown>[],
  includeModelOutput: boolean,
): Record<string, FixtureResult[]> {
  const grouped: Record<string, FixtureResult[]> = {};
  for (const row of rows) {
    const benchmark = String(row.benchmark_name);
    grouped[benchmark] = grouped[benchmark] ?? [];
    grouped[benchmark].push(fixtureResultFromRow(row, includeModelOutput));
  }
  return grouped;
}
