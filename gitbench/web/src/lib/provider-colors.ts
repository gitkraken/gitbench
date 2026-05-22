export const PROVIDER_COLORS: Record<string, string> = {
  anthropic: "#EC7FFF",
  cohere: "#01B7A1",
  deepseek: "#B657FF",
  google: "#196FFF",
  meta: "#6AB8FF",
  minimax: "#C170FF",
  mistral: "#FEDC00",
  moonshot: "#7900C9",
  openai: "#01FEE0",
  perplexity: "#48FEE9",
  qwen: "#359AFE",
  xai: "#EDEDED",
  zai: "#FFF96D",
};

/** Derive a deterministic hue for a provider string (golden-angle spacing). */
export function providerHue(provider: string): number {
  let h = 0;
  for (let i = 0; i < provider.length; i++) {
    h = (h * 31 + provider.charCodeAt(i)) & 0xffffffff;
  }
  return (h >>> 0) % 360;
}

/** Get the provider-specific color, falling back to a deterministic HSL hue. */
export function getProviderColor(provider: string): string {
  return (
    PROVIDER_COLORS[provider.toLowerCase()] ??
    `hsl(${providerHue(provider)}, 70%, 64%)`
  );
}
