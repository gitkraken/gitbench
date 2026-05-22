/**
 * Provider brand icons for GitBench.
 *
 * All icons sourced from @thesvg/react (https://thesvg.org) — 5,885+
 * verified brand SVG icons, tree-shakeable, with proper 24×24 viewBox.
 *
 * To add a new provider:
 * 1. Check https://thesvg.org for the icon (search by provider name)
 * 2. Import the component from @thesvg/react below
 * 3. Register it in the PROVIDER_ICONS map
 * 4. Add its palette color to provider-colors.ts
 * See docs/agents/provider-logos.md for full instructions.
 */

import Claude from "@thesvg/react/claude";
import Openai from "@thesvg/react/openai";
import Google from "@thesvg/react/google";
import Meta from "@thesvg/react/meta";
import Mistral from "@thesvg/react/mistral";
import Deepseek from "@thesvg/react/deepseek";
import Minimax from "@thesvg/react/minimax";
import Xai from "@thesvg/react/xai";
import Moonshot from "@thesvg/react/moonshot";
import Yi from "@thesvg/react/yi";
import Qwen from "@thesvg/react/qwen";
import Cohere from "@thesvg/react/cohere";
import Perplexity from "@thesvg/react/perplexity";

import type { ComponentType, SVGProps } from "react";

export type ProviderSvgComponent = ComponentType<SVGProps<SVGSVGElement>>;

export const PROVIDER_ICONS: Record<string, ProviderSvgComponent> = {
  anthropic: Claude, // Anthropic's Claude brand mark
  openai: Openai,
  google: Google,
  meta: Meta,
  mistral: Mistral,
  deepseek: Deepseek,
  minimax: Minimax,
  xai: Xai,
  moonshot: Moonshot,
  zai: Yi, // 01.AI / 零一万物 — makers of Yi models
  qwen: Qwen,
  cohere: Cohere,
  perplexity: Perplexity,
};
