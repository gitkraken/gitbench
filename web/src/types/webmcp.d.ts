interface WebMcpJsonSchema {
  type: "object";
  properties?: Record<string, Record<string, unknown>>;
  required?: string[];
  additionalProperties?: boolean;
}

interface WebMcpToolAnnotations {
  readOnlyHint?: boolean;
  untrustedContentHint?: boolean;
}

interface WebMcpExecutionContext {
  signal?: AbortSignal;
}

interface WebMcpToolDefinition {
  name: string;
  description: string;
  inputSchema: WebMcpJsonSchema;
  annotations?: WebMcpToolAnnotations;
  execute(
    input: Record<string, unknown>,
    context?: WebMcpExecutionContext,
  ): unknown | Promise<unknown>;
}

interface WebMcpRegistrationOptions {
  signal?: AbortSignal;
  exposedTo?: string[];
}

interface ModelContext {
  registerTool(
    tool: WebMcpToolDefinition,
    options?: WebMcpRegistrationOptions,
  ): void | Promise<void>;
}

interface Document {
  readonly modelContext?: ModelContext;
}
