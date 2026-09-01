import {
  createGitBenchToolDefinitions,
  type GitBenchToolDependencies,
  type ToolResult,
} from "./webmcp-report-tools.ts";

export const AGENT_OPERATIONS = [
  "overview",
  "models",
  "model-results",
  "benchmark",
  "fixture",
  "rank",
] as const;

export type AgentOperation = (typeof AGENT_OPERATIONS)[number];

const toolNames: Record<AgentOperation, string> = {
  overview: "gitbench_get_overview",
  models: "gitbench_list_models",
  "model-results": "gitbench_get_model_results",
  benchmark: "gitbench_get_benchmark",
  fixture: "gitbench_get_fixture",
  rank: "gitbench_rank_models",
};

export function isAgentOperation(value: string): value is AgentOperation {
  return (AGENT_OPERATIONS as readonly string[]).includes(value);
}

/**
 * Server-compatible facade over the report query contract. HTTP and browser
 * adapters call this facade rather than reproducing validation or projection.
 */
export function createAgentQueryService(
  dependencies: GitBenchToolDependencies,
  sourceBaseUrl?: string,
) {
  const definitions = new Map(
    createGitBenchToolDefinitions(dependencies, sourceBaseUrl).map(
      (definition) => [definition.name, definition],
    ),
  );

  return {
    execute(
      operation: AgentOperation,
      input: Record<string, unknown> = {},
      signal?: AbortSignal,
    ): Promise<ToolResult<unknown>> {
      const definition = definitions.get(toolNames[operation]);
      if (!definition) {
        throw new Error(`Missing agent operation definition: ${operation}`);
      }
      return definition.execute(input, { signal }) as Promise<
        ToolResult<unknown>
      >;
    },
  };
}
