export type TokenCount = number | null | undefined;

export interface OutputTokenDecomposition {
  totalOutputTokens: number | null;
  visibleOutputTokens: number | null;
  reasoningTokens: number | null;
  hasReasoningData: boolean;
}

export const TOTAL_OUTPUT_LABEL = "Total output";
export const REASONING_WITHIN_OUTPUT_LABEL = "Reasoning within output";

function normalizedTokenCount(value: TokenCount): number | null {
  return value == null ? null : value;
}

function formatTokenCount(value: number): string {
  return value.toLocaleString("en-US");
}

export function decomposeOutputTokens(
  outputTokens: TokenCount,
  reasoningTokens: TokenCount
): OutputTokenDecomposition {
  const totalOutput = normalizedTokenCount(outputTokens);
  const reasoning = normalizedTokenCount(reasoningTokens);
  return {
    totalOutputTokens: totalOutput,
    visibleOutputTokens:
      totalOutput == null ? null : Math.max(totalOutput - (reasoning ?? 0), 0),
    reasoningTokens: reasoning,
    hasReasoningData: reasoning != null,
  };
}

export function formatCompactTokenUsage(
  inputTokens: TokenCount,
  outputTokens: TokenCount,
  reasoningLevel: string | null | undefined,
  reasoningTokens: TokenCount
): string | null {
  if (inputTokens == null || outputTokens == null) return null;
  const base = `${formatTokenCount(inputTokens)} in → ${formatTokenCount(
    outputTokens
  )} out`;
  if (!reasoningLevel) return base;
  return reasoningTokens == null
    ? `${base} (reasoning unavailable)`
    : `${base} (${formatTokenCount(reasoningTokens)} reasoning)`;
}

export function formatAggregateTokenUsage(
  inputTokens: TokenCount,
  outputTokens: TokenCount,
  reasoningLevel: string | null | undefined,
  reasoningTokens: TokenCount
): string | null {
  if (inputTokens == null || outputTokens == null) return null;
  const input = formatTokenCount(inputTokens);
  const output = formatTokenCount(outputTokens);
  if (!reasoningLevel) return `${input} input / ${output} output tokens`;
  const reasoning =
    reasoningTokens == null ? "N/A" : formatTokenCount(reasoningTokens);
  return `${input} input / ${output} total output / ${reasoning} reasoning within output tokens`;
}
