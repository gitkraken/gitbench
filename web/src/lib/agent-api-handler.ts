import {
  createAgentQueryService,
  isAgentOperation,
  type AgentOperation,
} from "./agent-query-service.ts";
import { createServerAgentQueryDependencies } from "./agent-query-server.ts";
import { json, queryString } from "./report-api.ts";
import {
  benchmarkSourceUrl,
  fixtureSourceUrl,
  modelSourceUrl,
  modelsSourceUrl,
  overviewSourceUrl,
  type GitBenchToolDependencies,
  type ToolErrorCategory,
  type ToolFailure,
} from "./webmcp-report-tools.ts";

export const AGENT_SUCCESS_CACHE =
  "public, max-age=0, s-maxage=300, stale-while-revalidate=3600";
export const AGENT_FAILURE_CACHE = "no-store";

const parameters: Record<AgentOperation, ReadonlySet<string>> = {
  overview: new Set(["offset", "limit"]),
  models: new Set(["offset", "limit"]),
  "model-results": new Set([
    "model",
    "benchmark",
    "difficulty",
    "tag",
    "output_mode",
    "include_model_output",
    "evidence_characters",
    "offset",
    "limit",
  ]),
  benchmark: new Set(["benchmark", "offset", "limit"]),
  fixture: new Set([
    "benchmark",
    "fixture",
    "include_prompt",
    "include_expected",
    "include_model_output",
    "include_structured_output",
    "evidence_characters",
    "offset",
    "limit",
  ]),
  rank: new Set([
    "benchmark",
    "resource_metric",
    "strategy",
    "output_mode",
    "minimum_quality",
    "offset",
    "limit",
  ]),
};

const integerParameters = new Set(["offset", "limit", "evidence_characters"]);
const booleanParameters = new Set([
  "include_prompt",
  "include_expected",
  "include_model_output",
  "include_structured_output",
]);

function operationSourceUrl(
  operation: AgentOperation | null,
  query: Record<string, unknown>,
): string {
  if (operation === "models") return modelsSourceUrl();
  if (operation === "model-results")
    return modelSourceUrl(queryString(query.model) ?? "unknown");
  if (operation === "benchmark" || operation === "rank")
    return benchmarkSourceUrl(queryString(query.benchmark) ?? "unknown");
  if (operation === "fixture")
    return fixtureSourceUrl(
      queryString(query.benchmark) ?? "unknown",
      queryString(query.fixture) ?? "unknown",
    );
  return overviewSourceUrl();
}

function failure(
  operation: AgentOperation | null,
  query: Record<string, unknown>,
  category: ToolErrorCategory,
  message: string,
  input?: Record<string, unknown>,
): ToolFailure {
  return {
    ok: false,
    source_url: operationSourceUrl(operation, query),
    error: { category, message, ...(input ? { input } : {}) },
  };
}

function decodeQuery(
  operation: AgentOperation,
  query: Record<string, unknown>,
): Record<string, unknown> | ToolFailure {
  const input: Record<string, unknown> = {};
  for (const [key, raw] of Object.entries(query)) {
    if (key === "chart" || key === "operation") continue;
    if (!parameters[operation].has(key)) {
      return failure(
        operation,
        query,
        "invalid_input",
        `Unsupported query parameter: ${key}`,
        { [key]: raw },
      );
    }
    if (Array.isArray(raw)) {
      return failure(
        operation,
        query,
        "invalid_input",
        `${key} must be supplied once`,
        { [key]: raw },
      );
    }
    const value = queryString(raw);
    if (value === undefined) continue;
    if (integerParameters.has(key)) {
      if (!/^\d+$/.test(value)) {
        return failure(
          operation,
          query,
          "invalid_input",
          `${key} must be an integer`,
          { [key]: value },
        );
      }
      input[key] = Number(value);
    } else if (booleanParameters.has(key)) {
      if (value !== "true" && value !== "false") {
        return failure(
          operation,
          query,
          "invalid_input",
          `${key} must be true or false`,
          { [key]: value },
        );
      }
      input[key] = value === "true";
    } else if (key === "minimum_quality") {
      if (value.trim() === "" || !Number.isFinite(Number(value))) {
        return failure(
          operation,
          query,
          "invalid_input",
          "minimum_quality must be a number",
          { minimum_quality: value },
        );
      }
      input[key] = Number(value);
    } else {
      input[key] = value;
    }
  }
  return input;
}

function statusFor(category: ToolErrorCategory): number {
  if (category === "invalid_input") return 400;
  if (category === "not_found") return 404;
  if (category === "cancelled") return 499;
  if (category === "unavailable") return 503;
  return 500;
}

export function createAgentApiHandler(
  dependenciesFactory: () => GitBenchToolDependencies = createServerAgentQueryDependencies,
) {
  return async function agentApiHandler(req: any, res: any): Promise<void> {
    const rawOperation = String(
      req.query?.operation ?? req.query?.chart ?? "",
    ).replace(/^agent-/, "");
    const operation = isAgentOperation(rawOperation) ? rawOperation : null;

    if (req.method !== "GET") {
      res.setHeader("allow", "GET");
      res.setHeader("cache-control", AGENT_FAILURE_CACHE);
      json(
        res,
        405,
        failure(
          operation,
          req.query ?? {},
          "invalid_input",
          "Agent API operations only support GET.",
        ),
      );
      return;
    }
    if (!operation) {
      res.setHeader("cache-control", AGENT_FAILURE_CACHE);
      json(
        res,
        404,
        failure(
          null,
          req.query ?? {},
          "not_found",
          `Unsupported agent operation: ${rawOperation || "unknown"}`,
        ),
      );
      return;
    }

    const input = decodeQuery(operation, req.query ?? {});
    if ("ok" in input) {
      res.setHeader("cache-control", AGENT_FAILURE_CACHE);
      json(res, 400, input);
      return;
    }

    const service = createAgentQueryService(
      dependenciesFactory(),
      "https://gitbench.dev",
    );
    const result = await service.execute(operation, input, req.signal);
    res.setHeader(
      "cache-control",
      result.ok ? AGENT_SUCCESS_CACHE : AGENT_FAILURE_CACHE,
    );
    json(res, result.ok ? 200 : statusFor(result.error.category), result);
  };
}

export const agentApiHandler = createAgentApiHandler();
