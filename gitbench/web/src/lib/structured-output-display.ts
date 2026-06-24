export interface StructuredOutputFailureDisplay {
  message: string;
  copyText: string;
}

export function formatStructuredOutputFailure(
  structuredError: string | null | undefined,
  rawStructuredOutput: string | null | undefined
): StructuredOutputFailureDisplay | null {
  if (!structuredError || rawStructuredOutput == null) return null;

  const label = structuredError.startsWith("Failed to parse ")
    ? "Invalid JSON"
    : "Invalid structured output";
  return {
    message: `${label}. Output: ${rawStructuredOutput}`,
    copyText: rawStructuredOutput,
  };
}
