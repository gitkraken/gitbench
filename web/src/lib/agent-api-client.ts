import { ReportClientError } from "./report-client-error.ts";

export async function requestAgentOperation(
  operation: string,
  input: Record<string, unknown>,
  signal?: AbortSignal,
  baseUrl?: string,
): Promise<unknown> {
  const path = `/api/agent/v1/${encodeURIComponent(operation)}`;
  const url = baseUrl
    ? new URL(path, `${baseUrl.replace(/\/$/, "")}/`).toString()
    : path;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(input)) {
    if (value !== undefined && value !== null) params.set(key, String(value));
  }
  const requestUrl = params.size ? `${url}?${params}` : url;
  const response = await fetch(requestUrl, { method: "GET", signal });
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ReportClientError(
      `Agent API returned invalid JSON: ${requestUrl}`,
      response.status,
      requestUrl,
    );
  }
  if (
    typeof body !== "object" ||
    body === null ||
    typeof (body as { ok?: unknown }).ok !== "boolean"
  ) {
    throw new ReportClientError(
      `Agent API returned an invalid envelope: ${requestUrl}`,
      response.status,
      requestUrl,
    );
  }
  return body;
}
