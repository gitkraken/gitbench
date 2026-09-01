import type { ModelResultsResponse } from "./report-client.ts";
import { ReportClientError } from "./report-client-error.ts";
import type { BenchmarkDetail, FixtureDetail } from "./report-store.ts";
import type {
  CampaignAwareGitBenchData,
  FixtureResult,
  ModelInfo,
  RunMeta,
} from "./types.ts";
export const AGENT_OPERATIONS = [
  "overview",
  "models",
  "model-results",
  "benchmark",
  "fixture",
  "rank",
] as const;

export type AgentOperation = (typeof AGENT_OPERATIONS)[number];
export type ToolErrorCategory =
  "not_found" | "unavailable" | "invalid_input" | "query_failure" | "cancelled";

export interface ToolFailure {
  ok: false;
  source_url: string;
  error: {
    category: ToolErrorCategory;
    message: string;
    input?: Record<string, unknown>;
  };
}

export interface ToolSuccess<T> {
  ok: true;
  source_url: string;
  data: T;
}

export type ToolResult<T> = ToolSuccess<T> | ToolFailure;

export interface GitBenchToolDependencies {
  loadSummary(signal?: AbortSignal): Promise<CampaignAwareGitBenchData>;
  loadModels(signal?: AbortSignal): Promise<{ models: ModelInfo[] }>;
  loadModelResults(
    model: string,
    filters?: Record<string, string>,
    signal?: AbortSignal,
  ): Promise<ModelResultsResponse>;
  loadBenchmark(
    benchmark: string,
    signal?: AbortSignal,
  ): Promise<BenchmarkDetail & { campaign_id?: string | null }>;
  loadFixture(
    benchmark: string,
    fixture: string,
    signal?: AbortSignal,
  ): Promise<FixtureDetail & { campaign_id?: string | null }>;
  loadQuadrantChart(
    scope?: { benchmark?: string; fixture?: string },
    signal?: AbortSignal,
  ): Promise<CampaignAwareGitBenchData>;
}

const LIMITS = {
  listDefault: 20,
  listMaximum: 50,
  evidenceCharactersDefault: 2_000,
  evidenceCharactersMaximum: 8_000,
} as const;

class InvalidAgentInput extends Error {}

interface ModelGroupEffort {
  modelName: string;
  reasoningLevel: string | null;
  outputMode: string;
  totalCostUsd: number | null;
}

interface ModelGroup {
  id: string;
  efforts: ModelGroupEffort[];
}

function splitModelVariantKey(modelName: string): {
  canonicalModelName: string;
  outputMode: "text" | "json_schema";
} {
  const suffix = "__json_schema";
  return modelName.endsWith(suffix)
    ? {
        canonicalModelName: modelName.slice(0, -suffix.length),
        outputMode: "json_schema",
      }
    : { canonicalModelName: modelName, outputMode: "text" };
}

function deriveModelGroups(data: CampaignAwareGitBenchData): ModelGroup[] {
  if (data.base_model_groups?.length) {
    return data.base_model_groups.map((group) => ({
      id: `${group.provider}/${group.baseModel}`,
      efforts: group.levels.map((level) => {
        const variant = splitModelVariantKey(level.modelName);
        const model = data.models.find(
          (candidate) =>
            candidate.name === variant.canonicalModelName &&
            (candidate.output_mode ?? "text") === variant.outputMode,
        );
        return {
          modelName: level.modelName,
          reasoningLevel: model?.reasoningLevel ?? level.level,
          outputMode: variant.outputMode,
          totalCostUsd:
            data.model_summaries[level.modelName]?.total_cost_usd ??
            level.total_cost_usd ??
            null,
        };
      }),
    }));
  }

  const groups = new Map<string, ModelGroup>();
  for (const model of data.models) {
    const outputMode = model.output_mode ?? "text";
    const modelName =
      outputMode === "text" ? model.name : `${model.name}__${outputMode}`;
    const id = `${model.provider}/${model.baseModel}`;
    const group = groups.get(id) ?? { id, efforts: [] };
    group.efforts.push({
      modelName,
      reasoningLevel: model.reasoningLevel,
      outputMode,
      totalCostUsd: data.model_summaries[modelName]?.total_cost_usd ?? null,
    });
    groups.set(id, group);
  }
  return Array.from(groups.values());
}

function normalizeMetric(
  value: number,
  min: number,
  max: number,
  better: "higher" | "lower",
) {
  if (max === min) return 0.5;
  const ratio = (value - min) / (max - min);
  return better === "higher" ? ratio : 1 - ratio;
}

export function isAgentOperation(value: string): value is AgentOperation {
  return (AGENT_OPERATIONS as readonly string[]).includes(value);
}

function origin(): string {
  return "https://gitbench.gitkraken.com";
}

export function gitBenchSourceUrl(path: string, base = origin()): string {
  return new URL(path, `${base.replace(/\/$/, "")}/`).toString();
}

export function overviewSourceUrl(base?: string): string {
  return gitBenchSourceUrl("/", base);
}

export function modelsSourceUrl(base?: string): string {
  return gitBenchSourceUrl("/models", base);
}

export function modelSourceUrl(model: string, base?: string): string {
  const canonical = splitModelVariantKey(model).canonicalModelName;
  const [provider, ...rest] = canonical.split("/");
  const modelAndLevel = rest.join("/");
  const colon = modelAndLevel.lastIndexOf(":");
  const modelName =
    colon === -1 ? modelAndLevel : modelAndLevel.slice(0, colon);
  const level = colon === -1 ? null : modelAndLevel.slice(colon + 1);
  const parts = ["models", provider, modelName, ...(level ? [level] : [])];
  return gitBenchSourceUrl(`/${parts.map(encodeURIComponent).join("/")}`, base);
}

export function benchmarkSourceUrl(benchmark: string, base?: string): string {
  return gitBenchSourceUrl(
    `/benchmarks/${encodeURIComponent(benchmark)}`,
    base,
  );
}

export function fixtureSourceUrl(
  benchmark: string,
  fixture: string,
  base?: string,
): string {
  return gitBenchSourceUrl(
    `/fixtures/${encodeURIComponent(benchmark)}/${encodeURIComponent(fixture)}`,
    base,
  );
}

function sourceUrl(
  operation: AgentOperation,
  input: Record<string, unknown>,
  base?: string,
): string {
  if (operation === "models") return modelsSourceUrl(base);
  if (operation === "model-results")
    return modelSourceUrl(String(input.model || "unknown"), base);
  if (operation === "benchmark" || operation === "rank")
    return benchmarkSourceUrl(String(input.benchmark || "unknown"), base);
  if (operation === "fixture")
    return fixtureSourceUrl(
      String(input.benchmark || "unknown"),
      String(input.fixture || "unknown"),
      base,
    );
  return overviewSourceUrl(base);
}

function text(
  input: Record<string, unknown>,
  key: string,
  required = false,
): string | undefined {
  const value = input[key];
  if (value == null || value === "") {
    if (required) throw new InvalidAgentInput(`${key} is required`);
    return undefined;
  }
  if (typeof value !== "string")
    throw new InvalidAgentInput(`${key} must be a string`);
  return value;
}

function bool(input: Record<string, unknown>, key: string): boolean {
  const value = input[key];
  if (value == null) return false;
  if (typeof value !== "boolean")
    throw new InvalidAgentInput(`${key} must be a boolean`);
  return value;
}

function boundedInteger(
  input: Record<string, unknown>,
  key: string,
  fallback: number,
  maximum: number,
): number {
  const value = input[key] ?? fallback;
  if (!Number.isInteger(value) || Number(value) < 0)
    throw new InvalidAgentInput(`${key} must be a non-negative integer`);
  return Math.min(Number(value), maximum);
}

function listWindow(input: Record<string, unknown>) {
  if (
    input.limit !== undefined &&
    (!Number.isInteger(input.limit) || Number(input.limit) < 1)
  )
    throw new InvalidAgentInput("limit must be a positive integer");
  return {
    offset: boundedInteger(input, "offset", 0, Number.MAX_SAFE_INTEGER),
    limit: boundedInteger(
      input,
      "limit",
      LIMITS.listDefault,
      LIMITS.listMaximum,
    ),
  };
}

function page<T>(items: T[], offset: number, limit: number) {
  const sliced = items.slice(offset, offset + limit);
  const next = offset + sliced.length;
  return {
    items: sliced,
    offset,
    limit,
    total: items.length,
    truncated: next < items.length,
    next_offset: next < items.length ? next : null,
  };
}

function evidenceLimit(input: Record<string, unknown>): number {
  const raw = input.evidence_characters ?? LIMITS.evidenceCharactersDefault;
  if (!Number.isInteger(raw) || Number(raw) < 1)
    throw new InvalidAgentInput(
      "evidence_characters must be a positive integer",
    );
  return Math.min(Number(raw), LIMITS.evidenceCharactersMaximum);
}

function truncateEvidence(value: string | null | undefined, limit: number) {
  if (value == null) return null;
  return value.length <= limit ? value : `${value.slice(0, limit - 1)}…`;
}

function evaluationIdentityKey(
  model: string,
  reasoningLevel: string | null | undefined,
  outputMode: string | null | undefined,
) {
  const variant = splitModelVariantKey(model);
  const mode = outputMode ?? variant.outputMode;
  return JSON.stringify([
    variant.canonicalModelName.trim(),
    reasoningLevel == null || reasoningLevel === ""
      ? null
      : reasoningLevel.trim(),
    mode === "json" ? "json_schema" : mode,
  ]);
}

function buildGenerationLookup(runs: RunMeta[]): Map<string, string | null> {
  const timestamps = new Map<string, Set<string>>();
  for (const run of runs) {
    const key = evaluationIdentityKey(
      run.model,
      run.reasoning_level,
      run.output_mode,
    );
    const values = timestamps.get(key) ?? new Set<string>();
    if (run.timestamp) values.add(run.timestamp);
    timestamps.set(key, values);
  }
  return new Map(
    Array.from(timestamps, ([key, values]) => [
      key,
      values.size === 1 ? Array.from(values)[0] : null,
    ]),
  );
}

function generatedAt(
  lookup: Map<string, string | null>,
  model: string,
  reasoningLevel: string | null | undefined,
  outputMode: string | null | undefined,
) {
  return (
    lookup.get(evaluationIdentityKey(model, reasoningLevel, outputMode)) ?? null
  );
}

function modelEvaluationIdentity(models: ModelInfo[], model: string) {
  const requested = splitModelVariantKey(model);
  const match = models.find((candidate) => {
    const candidateVariant = splitModelVariantKey(candidate.name);
    return (
      candidateVariant.canonicalModelName === requested.canonicalModelName &&
      (candidate.output_mode || candidateVariant.outputMode) ===
        requested.outputMode
    );
  });
  return match
    ? {
        reasoningLevel: match.reasoningLevel,
        outputMode: match.output_mode || requested.outputMode,
      }
    : undefined;
}

function projectResult(
  result: FixtureResult,
  model: string,
  lookup: Map<string, string | null>,
  includeOutput: boolean,
  characterLimit: number,
) {
  return {
    fixture_id: result.fixture_id,
    passed: result.passed,
    similarity: result.similarity,
    error: result.error,
    reasoning_level: result.reasoning_level,
    output_mode: result.output_mode,
    cost_usd: result.cost_usd,
    api_duration_ms: result.api_duration_ms,
    total_tokens: result.total_tokens,
    generated_at: generatedAt(
      lookup,
      model,
      result.reasoning_level,
      result.output_mode,
    ),
    ...(includeOutput
      ? { model_output: truncateEvidence(result.model_output, characterLimit) }
      : {}),
  };
}

type ResourceMetric = "cost" | "api_time" | "tokens";
type RankingStrategy = "efficiency_ratio" | "balanced";

function resourceFor(
  effort: ModelGroupEffort,
  data: CampaignAwareGitBenchData,
  metric: ResourceMetric,
) {
  if (metric === "cost")
    return effort.totalCostUsd == null
      ? null
      : { value: effort.totalCostUsd, unit: "USD" };
  if (metric === "api_time") {
    const runtime = data.model_runtimes[effort.modelName];
    return runtime
      ? { value: runtime.total_ms / 1000, unit: "api_call_seconds" }
      : null;
  }
  const tokens = data.model_token_summaries[effort.modelName];
  return tokens ? { value: tokens.total_tokens, unit: "tokens" } : null;
}

function rankModels(
  data: CampaignAwareGitBenchData,
  benchmark: string,
  metric: ResourceMetric,
  strategy: RankingStrategy,
  outputMode: string,
  minimumQuality: number,
) {
  const raw = deriveModelGroups(data).flatMap((group) =>
    group.efforts
      .filter(
        (effort) => outputMode === "both" || effort.outputMode === outputMode,
      )
      .map((effort) => ({ group, effort })),
  );
  let excluded_below_quality = 0;
  let excluded_unusable_resource = 0;
  const eligible: any[] = [];
  for (const { group, effort } of raw) {
    const quality = data.matrix[effort.modelName]?.[benchmark]?.pass_at_k;
    if (quality == null || quality < minimumQuality) {
      excluded_below_quality += 1;
      continue;
    }
    const resource = resourceFor(effort, data, metric);
    if (!resource || !Number.isFinite(resource.value) || resource.value <= 0) {
      excluded_unusable_resource += 1;
      continue;
    }
    eligible.push({
      pair_id: group.id,
      model: splitModelVariantKey(effort.modelName).canonicalModelName,
      reasoning_level: effort.reasoningLevel,
      output_mode: effort.outputMode,
      quality,
      resource: resource.value,
      resource_unit: resource.unit,
      ranking_score: quality / resource.value,
    });
  }
  if (strategy === "balanced" && eligible.length) {
    const qualities = eligible.map((entry) => entry.quality);
    const resources = eligible.map((entry) => entry.resource);
    for (const entry of eligible) {
      entry.quality_score = normalizeMetric(
        entry.quality,
        Math.min(...qualities),
        Math.max(...qualities),
        "higher",
      );
      entry.resource_score = normalizeMetric(
        entry.resource,
        Math.min(...resources),
        Math.max(...resources),
        "lower",
      );
      entry.ranking_score = (entry.quality_score + entry.resource_score) / 2;
    }
  }
  const best = new Map<string, any>();
  for (const entry of eligible) {
    const key = `${entry.pair_id}\u0000${entry.output_mode}`;
    const previous = best.get(key);
    if (
      !previous ||
      entry.ranking_score > previous.ranking_score ||
      (entry.ranking_score === previous.ranking_score &&
        entry.model.localeCompare(previous.model) < 0)
    )
      best.set(key, entry);
  }
  return {
    entries: Array.from(best.values()).sort(
      (a, b) =>
        b.ranking_score - a.ranking_score ||
        a.model.localeCompare(b.model) ||
        a.output_mode.localeCompare(b.output_mode),
    ),
    candidate_count: raw.length,
    excluded_below_quality,
    excluded_unusable_resource,
  };
}

function normalizeFailure(
  source_url: string,
  error: unknown,
  input: Record<string, unknown>,
): ToolFailure {
  if (error instanceof InvalidAgentInput)
    return {
      ok: false,
      source_url,
      error: { category: "invalid_input", message: error.message, input },
    };
  if (error instanceof DOMException && error.name === "AbortError")
    return {
      ok: false,
      source_url,
      error: {
        category: "cancelled",
        message: "The report query was cancelled.",
      },
    };
  if (error instanceof ReportClientError) {
    const category: ToolErrorCategory =
      error.status === 404
        ? "not_found"
        : error.status >= 500
          ? "unavailable"
          : "query_failure";
    return {
      ok: false,
      source_url,
      error: { category, message: error.message, input },
    };
  }
  if (error instanceof TypeError)
    return {
      ok: false,
      source_url,
      error: {
        category: "unavailable",
        message: "The report API is unavailable.",
      },
    };
  return {
    ok: false,
    source_url,
    error: {
      category: "query_failure",
      message:
        error instanceof Error ? error.message : "The report query failed.",
    },
  };
}

export function createAgentQueryService(
  dependencies: GitBenchToolDependencies,
  sourceBaseUrl?: string,
) {
  return {
    async execute(
      operation: AgentOperation,
      input: Record<string, unknown> = {},
      signal?: AbortSignal,
    ): Promise<ToolResult<unknown>> {
      const source_url = sourceUrl(operation, input, sourceBaseUrl);
      try {
        const data = await executeOperation(
          dependencies,
          operation,
          input,
          signal,
        );
        return { ok: true, source_url, data };
      } catch (error) {
        return normalizeFailure(source_url, error, input);
      }
    },
  };
}

async function executeOperation(
  dependencies: GitBenchToolDependencies,
  operation: AgentOperation,
  input: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<unknown> {
  const { offset, limit } = listWindow(input);
  if (operation === "overview") {
    const data = await dependencies.loadSummary(signal);
    const lookup = buildGenerationLookup(data.runs_meta);
    const leaders = Object.entries(data.model_summaries)
      .sort(
        (a, b) => b[1].pass_at_k - a[1].pass_at_k || a[0].localeCompare(b[0]),
      )
      .map(([model, summary]) => {
        const identity = modelEvaluationIdentity(data.models, model);
        return {
          model,
          pass_at_k: summary.pass_at_k,
          total_cost_usd: summary.total_cost_usd,
          generated_at: generatedAt(
            lookup,
            model,
            identity?.reasoningLevel,
            identity?.outputMode,
          ),
        };
      });
    return {
      campaign_id: data.campaign_id ?? null,
      model_count: data.models.length,
      benchmark_count: data.benchmarks.length,
      benchmarks: page(data.benchmarks, offset, limit),
      leading_models: page(leaders, offset, limit),
    };
  }
  if (operation === "models") {
    const { models } = await dependencies.loadModels(signal);
    return {
      campaign_id: null,
      ...page(
        [...models].sort((a, b) => a.name.localeCompare(b.name)),
        offset,
        limit,
      ),
    };
  }
  if (operation === "model-results") {
    const model = text(input, "model", true) as string;
    const filters = Object.fromEntries(
      ["benchmark", "difficulty", "tag", "output_mode"]
        .map((key) => [key, text(input, key)] as const)
        .filter(
          (entry): entry is readonly [string, string] => entry[1] !== undefined,
        ),
    );
    const characterLimit = evidenceLimit(input);
    const [results, summary] = await Promise.all([
      dependencies.loadModelResults(model, filters, signal),
      dependencies.loadSummary(signal),
    ]);
    const lookup = buildGenerationLookup(summary.runs_meta);
    const includeOutput = bool(input, "include_model_output");
    const flattened = Object.entries(results.results)
      .flatMap(([benchmark, rows]) =>
        rows.map((row) => ({
          benchmark,
          ...projectResult(
            row,
            results.model,
            lookup,
            includeOutput,
            characterLimit,
          ),
        })),
      )
      .sort(
        (a, b) =>
          a.benchmark.localeCompare(b.benchmark) ||
          a.fixture_id.localeCompare(b.fixture_id) ||
          String(a.output_mode).localeCompare(String(b.output_mode)),
      );
    return {
      campaign_id: results.campaign_id ?? null,
      model: results.model,
      filters,
      results: page(flattened, offset, limit),
      ...(includeOutput ? { untrusted_content: true } : {}),
    };
  }
  if (operation === "benchmark") {
    const benchmark = text(input, "benchmark", true) as string;
    const [detail, summary] = await Promise.all([
      dependencies.loadBenchmark(benchmark, signal),
      dependencies.loadSummary(signal),
    ]);
    const lookup = buildGenerationLookup(summary.runs_meta);
    const leaderboard = detail.leaderboard
      .map((entry) => {
        const identity = modelEvaluationIdentity(summary.models, entry.model);
        return {
          ...entry,
          generated_at: generatedAt(
            lookup,
            entry.model,
            identity?.reasoningLevel,
            identity?.outputMode,
          ),
        };
      })
      .sort(
        (a, b) => b.pass_at_k - a.pass_at_k || a.model.localeCompare(b.model),
      );
    const fixtures = Object.values(detail.fixtures)
      .map(({ prompt: _p, expected: _e, setup: _s, ...fixture }) => fixture)
      .sort((a, b) => a.id.localeCompare(b.id));
    return {
      campaign_id: detail.campaign_id ?? summary.campaign_id ?? null,
      benchmark: detail.benchmark,
      tag_counts: detail.tag_counts,
      leaderboard: page(leaderboard, offset, limit),
      fixtures: page(fixtures, offset, limit),
    };
  }
  if (operation === "fixture") {
    const benchmark = text(input, "benchmark", true) as string;
    const fixture = text(input, "fixture", true) as string;
    const characterLimit = evidenceLimit(input);
    const [detail, summary] = await Promise.all([
      dependencies.loadFixture(benchmark, fixture, signal),
      dependencies.loadSummary(signal),
    ]);
    const lookup = buildGenerationLookup(summary.runs_meta);
    const includePrompt = bool(input, "include_prompt");
    const includeExpected = bool(input, "include_expected");
    const includeOutput = bool(input, "include_model_output");
    const includeStructured = bool(input, "include_structured_output");
    const outputs = detail.outputs
      .map((result) => ({
        model: result.model,
        ...projectResult(
          result,
          result.model,
          lookup,
          includeOutput,
          characterLimit,
        ),
        ...(includeStructured
          ? {
              parsed_payload: truncateEvidence(
                result.parsed_payload,
                characterLimit,
              ),
              raw_structured_output: truncateEvidence(
                result.raw_structured_output,
                characterLimit,
              ),
              structured_error: truncateEvidence(
                result.structured_error,
                characterLimit,
              ),
            }
          : {}),
      }))
      .sort(
        (a, b) =>
          a.model.localeCompare(b.model) ||
          String(a.output_mode).localeCompare(String(b.output_mode)) ||
          String(a.reasoning_level).localeCompare(String(b.reasoning_level)),
      );
    const includesEvidence =
      includePrompt || includeExpected || includeOutput || includeStructured;
    return {
      campaign_id: detail.campaign_id ?? summary.campaign_id ?? null,
      fixture: {
        id: detail.fixture.id,
        benchmark: detail.fixture.benchmark,
        description: detail.fixture.description,
        purpose: detail.fixture.purpose,
        difficulty: detail.fixture.difficulty,
        tags: detail.fixture.tags,
        ...(includePrompt
          ? { prompt: truncateEvidence(detail.fixture.prompt, characterLimit) }
          : {}),
        ...(includeExpected
          ? {
              expected: truncateEvidence(
                detail.fixture.expected,
                characterLimit,
              ),
            }
          : {}),
      },
      outputs: page(outputs, offset, limit),
      ...(includesEvidence ? { untrusted_content: true } : {}),
    };
  }

  const benchmark = text(input, "benchmark", true) as string;
  const metric = (text(input, "resource_metric") ?? "cost") as ResourceMetric;
  const strategy = (text(input, "strategy") ??
    "efficiency_ratio") as RankingStrategy;
  const outputMode = text(input, "output_mode") ?? "both";
  if (!["cost", "api_time", "tokens"].includes(metric))
    throw new InvalidAgentInput(
      "resource_metric must be cost, api_time, or tokens",
    );
  if (!["efficiency_ratio", "balanced"].includes(strategy))
    throw new InvalidAgentInput(
      "strategy must be efficiency_ratio or balanced",
    );
  if (!["text", "json_schema", "both"].includes(outputMode))
    throw new InvalidAgentInput(
      "output_mode must be text, json_schema, or both",
    );
  const minimumQuality =
    input.minimum_quality == null ? 0 : Number(input.minimum_quality);
  if (
    !Number.isFinite(minimumQuality) ||
    minimumQuality < 0 ||
    minimumQuality > 1
  )
    throw new InvalidAgentInput("minimum_quality must be between 0 and 1");
  const [data, summary] = await Promise.all([
    dependencies.loadQuadrantChart({ benchmark }, signal),
    dependencies.loadSummary(signal),
  ]);
  const ranked = rankModels(
    data,
    benchmark,
    metric,
    strategy,
    outputMode,
    minimumQuality,
  );
  const lookup = buildGenerationLookup(summary.runs_meta);
  const entries = ranked.entries.map((entry) => ({
    ...entry,
    generated_at: generatedAt(
      lookup,
      entry.model,
      entry.reasoning_level,
      entry.output_mode,
    ),
  }));
  return {
    campaign_id: summary.campaign_id ?? null,
    benchmark,
    resource_metric: metric,
    strategy,
    output_mode: outputMode,
    minimum_quality: minimumQuality,
    candidate_count: ranked.candidate_count,
    selected_candidate_count: entries.length,
    excluded_below_quality: ranked.excluded_below_quality,
    excluded_unusable_resource: ranked.excluded_unusable_resource,
    ranking: page(entries, offset, limit),
  };
}
